# How NomadRoute uses MongoDB

NomadRoute is an AI trip planner for Mongolia: a traveller describes a trip in Mongolian or English, and the agent
builds a day-by-day route with real roads, stays, events and transport, then books the stays and takes payment.
MongoDB is the only database behind it. This page shows which MongoDB features we use, where, and why.

For the collections and their fields, see [DATABASE.md](DATABASE.md).

## At a glance

| Feature                                                                           | Where                                   | What it does for the product                                                 |
| --------------------------------------------------------------------------------- | --------------------------------------- | ---------------------------------------------------------------------------- |
| Geospatial: `2dsphere`, `$geoNear`, `$nearSphere`, `$geoWithin`, `$geoIntersects` | planner, catalog API                    | Stays near each stop, events near the route, "which region is this point in" |
| Aggregation pipelines (`$match`, `$group`, `$addToSet`, `$push`, `$all`)          | stay availability                       | "Which rooms are free on every night of the trip" in one query               |
| Multi-document ACID transactions (replica set `rs0`)                              | booking, payment                        | Holding rooms, creating bookings and charging happen all-or-nothing          |
| Atomic conditional updates (`find_one_and_update` + `$inc`)                       | booking, outbox, plans                  | No overbooking, safe concurrent workers, optimistic versioning               |
| TTL indexes                                                                       | plans, login codes                      | Draft plans and one-time codes expire by themselves                          |
| Unique and partial indexes                                                        | payments, mandates, users, availability | Idempotent payments, replay protection, one row per room per night           |
| `$jsonSchema` validators generated from Pydantic                                  | every collection                        | The database rejects documents that break the schema                         |
| Upserts with `$setOnInsert`                                                       | saved trips, seeding                    | Saving the same plan twice is safe                                           |
| Atomic collection swap (`rename` with `dropTarget`)                               | seeder                                  | Reloading reference data never shows a half-loaded collection                |
| Bilingual documents (`{"mn": ..., "en": ...}`)                                    | all reference data                      | One document serves both languages                                           |
| Transactional outbox                                                              | payments → bookings                     | Side effects are delivered at least once, even after a crash                 |

## 1. Geospatial queries

Every place, stay, event, vehicle and route stores a GeoJSON `location` (or `geometry` / `boundary`) with a
`2dsphere` index ([mongo.py](../back/app/db/mongo.py)).

- **Stays near a stop, nearest first.** The planner runs `$geoNear` on `stays` for every place on the route,
  with `maxDistance` in metres and only the fields it needs (`$project`), in
  [filters.py `stays_within`](../back/app/modules/orchestrator/filters.py).
- **Events near the route.** `GET /events` filters by date overlap and, when given a point, by a
  `$geoWithin` / `$centerSphere` circle ([filters.py `within_km`](../back/app/modules/orchestrator/filters.py),
  [travel.py `list_events`](../back/app/api/v1/travel.py)). The trip map uses it to show festivals along the road.
- **Nearby catalog search.** `GET /places` and `GET /stays` take `lng`, `lat`, `radius_km` and use
  `$nearSphere`, so results come back sorted by distance ([travel.py `_near`](../back/app/api/v1/travel.py)).
- **Which region is a point in.** Regions store their boundary as a polygon; `GET /regions/locate` finds the
  region with `$geoIntersects` ([travel.py `locate_region`](../back/app/api/v1/travel.py)).

## 2. Aggregation pipelines for availability

`stay_availability` has one row per stay, room type and night. A room type is bookable only if it is open on
every night of the trip. Instead of loading all rows and checking in Python, one pipeline does it
([filters.py `open_unit_nights`](../back/app/modules/orchestrator/filters.py)):

```python
[
    {"$match": {"stay_id": {"$in": stay_ids}, "date": {"$in": nights}, "status": "open"}},
    {"$group": {
        "_id": {"stay_id": "$stay_id", "unit_type": "$unit_type"},
        "dates": {"$addToSet": "$date"},
        "rows": {"$push": {"date": "$date", "available": "$available", "price_mnt": "$price_mnt"}},
    }},
    {"$match": {"dates": {"$all": nights}}},
]
```

A second pipeline (`stay_ids_free_every_night`) groups twice to count free nights per stay. A partial
compound index on `{date, status, available, stay_id}` with `partialFilterExpression: {status: "open"}` matches
the `$match` stage, so MongoDB can serve it from the index.

## 3. Transactions

The compose file runs MongoDB as a single-node replica set (`--replSet rs0`), the same as Atlas, so
multi-document transactions are available. [transactions.py](../back/app/db/transactions.py) wraps work in
`session.with_transaction`, which commits atomically and retries on transient errors.

Used for:

- **Checkout** ([booking/service.py `create_checkout`](../back/app/modules/booking/service.py)): take room units
  for every night of every stay, insert the holds and bookings, and write the audit log. If one night is full,
  nothing is held.
- **Payment approved / failed, checkout expiry** ([payment/service.py](../back/app/modules/payment/service.py),
  `expire_checkouts`): payment state, booking state and returned room units change together.

## 4. Atomic conditional updates (no overbooking)

Taking rooms is a single conditional update, so two travellers can never get the same last room
([booking/service.py `_take_units`](../back/app/modules/booking/service.py)):

```python
db.stay_availability.find_one_and_update(
    {"stay_id": stay_id, "unit_type": unit_type, "date": day, "status": "open", "available": {"$gte": qty}},
    {"$inc": {"available": -qty}},
    return_document=ReturnDocument.AFTER,
)
```

The same pattern appears elsewhere:

- **Outbox workers** claim one event at a time with `find_one_and_update` + `$inc: {attempts: 1}`, so several
  workers can run without delivering an event twice ([outbox.py](../back/app/db/outbox.py)).
- **Plan revisions** update a plan only if its `version` is still the one that was read (optimistic
  concurrency), so two edits from two tabs cannot overwrite each other
  ([orchestrator/service.py `_replace`](../back/app/modules/orchestrator/service.py)).

## 5. Indexes that enforce rules

All indexes are declared in one list, [mongo.py `INDEXES`](../back/app/db/mongo.py), and created at startup and
by the seeder.

- **TTL:** `plan_proposals.expires_at` (draft plans live 24 hours) and `auth_challenges.expires_at` (one-time
  login codes) with `expireAfterSeconds: 0`. Holds deliberately do not use TTL: an expired hold must give its
  rooms back, so a sweeper handles it in a transaction.
- **Unique:** `payments.idempotency_key` (a retried payment request cannot charge twice),
  `payment_events.{provider, provider_ref, kind}` (a payment webhook delivered twice is processed once),
  `stay_availability.{stay_id, date, unit_type}`, `itinerary_versions.{trip_id, version}`.
- **Partial unique:** `users.email` and `users.phone` only where the field is a string (sign-up with email or
  phone); `mandates.{kind, transaction_id}` only for used, closed mandates (replay protection without blocking
  rejected ones); `payments.transaction_id` only where it exists.
- **Compound** indexes for the queries the app actually runs: date-overlap on events (`start_date`, `end_date`),
  bookings by trip and user, audit log by trip and time, conversations by user and `updated_at` descending.

The app catches `DuplicateKeyError` where a duplicate means "already done", which makes those calls idempotent.

## 6. Schema validation from one source of truth

Every document type is a Pydantic model in [schemas/travel.py](../back/app/schemas/travel.py) and
[schemas/commerce.py](../back/app/schemas/commerce.py). [validators.py](../back/app/db/validators.py) turns each
model into a MongoDB `$jsonSchema` validator (`bsonType`, `required`, `enum`, ranges, patterns, nested objects)
and creates the collection with `validationLevel: "strict"`, `validationAction: "error"`. A schema change is
applied with `collMod`. The API, the seeder and the database all check the same rules.

## 7. Safe seeding and saving

- **Atomic swap:** reference collections are built under a temporary name with their validator and indexes, then
  swapped in with `rename(..., dropTarget=True)`, so readers never see a half-loaded or index-less collection
  ([mock_seed.py](../back/app/seeds/mock_seed.py)).
- **Upserts with `$setOnInsert`:** demo rows are added only if missing, and saving a plan as a trip twice
  creates it once ([orchestrator/service.py `save_trip`](../back/app/modules/orchestrator/service.py)).

## 8. Document model choices

- **Bilingual fields:** names and descriptions are stored as `{"mn": ..., "en": ...}` in the same document, and
  the API returns the caller's language from `Accept-Language`
  ([i18n.py](../back/app/utils/i18n.py)). No join or second collection is needed for translations.
- **Embedded data:** a plan embeds its days, stays and totals; a stay embeds its rooms, images and reviews. The
  plan page loads in one read.
- **Snapshots:** `itinerary_versions` keeps every saved version of a trip, and `saved_plans` keeps a snapshot so
  a trip can be resumed after its draft expired.

## 9. Running it

- Local: `docker compose up` starts `mongo:8` as replica set `rs0`; the backend creates every index at startup.
- Atlas: set `MONGO_URI` to the Atlas connection string; nothing else changes (Atlas is a replica set too).
- Tests: unit tests use `mongomock`; the payment integration tests run the real transactional path against the
  compose MongoDB when `MONGO_TEST_URI` is set ([test_payment_integration.py](../back/test/test_payment_integration.py)).
