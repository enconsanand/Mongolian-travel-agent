import logging
from functools import lru_cache

from pymongo import ASCENDING, DESCENDING, GEOSPHERE, IndexModel, MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import PyMongoError

from app.core.config import settings

logger = logging.getLogger(__name__)


@lru_cache
def get_client() -> MongoClient:
    """Shared MongoClient; it pools connections and is safe to reuse across threads."""
    return MongoClient(settings.MONGO_URI, tz_aware=True, serverSelectionTimeoutMS=5000)


def get_database() -> Database:
    return get_client()[settings.MONGO_DB_NAME]


_region_key: list[tuple[str, int | str]] = [("region", ASCENDING)]


def _only_strings(field: str) -> dict:
    """Partial index filter: index only documents where ``field`` is a string (skips null / missing)."""
    return {"partialFilterExpression": {field: {"$type": "string"}}}


# (collection, keys, options). The only list of indexes: the app creates them at startup and the seeder
# creates them on every collection it loads.
INDEXES: list[tuple[str, list[tuple[str, int | str]], dict]] = [
    ("users", [("email", ASCENDING)], {"unique": True, "name": "email_contact_unique", **_only_strings("email")}),
    ("users", [("phone", ASCENDING)], {"unique": True, **_only_strings("phone")}),
    ("auth_challenges", [("expires_at", ASCENDING)], {"expireAfterSeconds": 0}),
    ("saved_plans", [("proposal_id", ASCENDING)], {"unique": True}),
    ("saved_plans", [("user_id", ASCENDING)], {}),
    ("regions", [("boundary", GEOSPHERE)], {}),
    ("places", [("location", GEOSPHERE)], {}),
    ("stays", [("location", GEOSPHERE)], {}),
    ("events", [("location", GEOSPHERE)], {}),
    # Overlap is start_date <= day <= end_date; each bound has its own index
    ("events", [("start_date", ASCENDING)], {}),
    ("events", [("end_date", ASCENDING)], {}),
    ("vehicles", [("current_location", GEOSPHERE)], {}),
    ("routes", [("geometry", GEOSPHERE)], {}),
    *[(c, _region_key, {}) for c in ("places", "events", "routes", "transport_schedules", "shared_rides", "drivers")],
    ("stays", [("region", ASCENDING), ("type", ASCENDING)], {}),
    ("vehicles", [("region", ASCENDING), ("rental.mode", ASCENDING)], {}),
    ("stay_availability", [("stay_id", ASCENDING), ("date", ASCENDING), ("unit_type", ASCENDING)], {"unique": True}),
    # "Which stays are free on these dates" does not name a stay_id, so the unique index cannot serve it.
    # The partial filter matches the query (status open), which is what lets Mongo use the index.
    (
        "stay_availability",
        [("date", ASCENDING), ("status", ASCENDING), ("available", ASCENDING), ("stay_id", ASCENDING)],
        {"partialFilterExpression": {"status": "open"}},
    ),
    (
        "transport_availability",
        [("schedule_id", ASCENDING), ("date", ASCENDING), ("departure_time", ASCENDING), ("seat_class", ASCENDING)],
        {"unique": True},
    ),
    ("vehicle_availability", [("vehicle_id", ASCENDING), ("date", ASCENDING)], {"unique": True}),
    ("shared_rides", [("from_place_id", ASCENDING), ("to_place_id", ASCENDING), ("date", ASCENDING)], {}),
    ("bookings", [("trip_id", ASCENDING)], {}),
    ("bookings", [("user_id", ASCENDING)], {}),
    ("quotes", [("trip_id", ASCENDING)], {}),
    ("payments", [("idempotency_key", ASCENDING)], {"unique": True}),
    ("payments", [("user_id", ASCENDING), ("status", ASCENDING)], {}),
    # One payment per AP2 transaction (checkout hash); older mock payments have none
    ("payments", [("transaction_id", ASCENDING)], {"unique": True, **_only_strings("transaction_id")}),
    # --- commerce (app.schemas.commerce)
    ("checkouts", [("checkout_hash", ASCENDING)], {"unique": True}),
    ("checkouts", [("trip_id", ASCENDING)], {}),
    ("mandates", [("hash", ASCENDING)], {"unique": True}),
    # Replay protection: a checkout's closed mandate of each kind is used once. Rejected mandates are kept as
    # evidence with their real transaction_id, so the index only covers used ones.
    (
        "mandates",
        [("kind", ASCENDING), ("transaction_id", ASCENDING)],
        {"unique": True, "partialFilterExpression": {"form": "closed", "status": "used"}},
    ),
    ("mandates", [("trip_id", ASCENDING)], {}),
    ("holds", [("stay_id", ASCENDING), ("date", ASCENDING), ("unit_type", ASCENDING)], {}),
    # The expiry sweeper's query; not a TTL index, which would drop holds without returning their units
    ("holds", [("status", ASCENDING), ("expires_at", ASCENDING)], {}),
    ("holds", [("trip_id", ASCENDING)], {}),
    (
        "payment_events",
        [("provider", ASCENDING), ("provider_ref", ASCENDING), ("kind", ASCENDING)],
        {"unique": True},
    ),
    ("outbox", [("dispatched_at", ASCENDING), ("created_at", ASCENDING)], {}),
    ("user_keys", [("user_id", ASCENDING)], {}),
    ("refunds", [("payment_id", ASCENDING)], {}),
    ("itinerary_versions", [("trip_id", ASCENDING), ("version", ASCENDING)], {"unique": True}),
    ("trips", [("user_id", ASCENDING)], {}),
    ("audit_log", [("trip_id", ASCENDING), ("ts", ASCENDING)], {}),
    ("audit_log", [("user_id", ASCENDING), ("ts", ASCENDING)], {}),
    ("conversations", [("user_id", ASCENDING), ("updated_at", DESCENDING)], {}),
    ("agent_state", [("trip_id", ASCENDING)], {"unique": True}),
    ("user_memory", [("user_id", ASCENDING)], {}),
    # Trip planner proposals live a day (app.modules.orchestrator.service)
    ("plan_proposals", [("expires_at", ASCENDING)], {"expireAfterSeconds": 0}),
]


def create_indexes_for(collection: Collection, name: str) -> None:
    """Create the indexes of collection ``name`` on ``collection`` (can be a temporary collection)."""
    models = [IndexModel(keys, **options) for col, keys, options in INDEXES if col == name]
    if models:
        collection.create_indexes(models)
        if name == "users":
            # Build the replacement first: preserve email uniqueness throughout the upgrade.
            old = collection.index_information().get("email_1")
            if old and old.get("unique") and not old.get("partialFilterExpression"):
                collection.drop_index("email_1")


def ensure_indexes(db: Database) -> list[str]:
    """Create all indexes (no-op for existing ones). Keeps going past failures; returns them."""
    failures = []
    for name in dict.fromkeys(col for col, _, _ in INDEXES):
        try:
            create_indexes_for(db[name], name)
        except PyMongoError as exc:
            logger.error("Could not create indexes on `%s`: %s", name, exc)
            failures.append(name)
    return failures
