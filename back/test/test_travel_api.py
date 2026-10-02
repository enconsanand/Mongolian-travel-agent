"""Travel read API on the seeded mock data (mongomock: geo queries are covered against real MongoDB)."""

import pytest

from app.seeds.mock_seed import load_mock_collections, upsert_mock_users

PASSWORD = "seed-password-1"
API = "/api/v1"


@pytest.fixture
def seeded(db):
    load_mock_collections(db, real_server=False)
    upsert_mock_users(db, password=PASSWORD)
    return db


def _auth(client, email):
    token = client.post(f"{API}/auth/login", data={"username": email, "password": PASSWORD}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_regions_are_localized(client, seeded):
    mn = client.get(f"{API}/regions").json()
    en = client.get(f"{API}/regions", headers={"Accept-Language": "en"}).json()
    assert [r["id"] for r in mn] == ["east", "north", "south", "west"]
    assert mn[0]["name"] == "Зүүн бүс"
    assert en[0]["name"] == "East"
    assert "_id" not in mn[0]


def test_get_unknown_region_is_404(client, seeded):
    assert client.get(f"{API}/regions/central").status_code == 404


def test_stays_filter_by_region_type_and_free_date(client, seeded):
    stays = client.get(f"{API}/stays", params={"region": "west", "type": "ger_camp"}).json()
    assert stays and all(s["region"] == "west" and s["type"] == "ger_camp" for s in stays)

    seeded["stay_availability"].update_many(
        {"stay_id": "stay_olgii_hotel_eagle", "date": "2026-10-03"},
        {"$set": {"status": "sold_out", "available": 0}},
    )
    free = {s["id"] for s in client.get(f"{API}/stays", params={"region": "west", "date": "2026-10-03"}).json()}
    assert "stay_olgii_hotel_eagle" not in free
    assert "stay_olgii_guesthouse_kazakh" in free


def test_a_range_requires_every_night_free(client, seeded):
    one = {s["id"] for s in client.get(f"{API}/stays", params={"region": "west", "date": "2026-10-03"}).json()}
    assert "stay_olgii_guesthouse_kazakh" in one
    seeded["stay_availability"].update_many(
        {"stay_id": "stay_olgii_guesthouse_kazakh", "date": "2026-10-04"},
        {"$set": {"status": "sold_out", "available": 0}},
    )
    span = {
        s["id"]
        for s in client.get(
            f"{API}/stays", params={"region": "west", "date_from": "2026-10-03", "date_to": "2026-10-04"}
        ).json()
    }
    assert "stay_olgii_guesthouse_kazakh" not in span


def test_stay_detail_has_policy_and_availability(client, seeded):
    stay = client.get(
        f"{API}/stays/stay_khatgal_camp_blue_pearl",
        params={"date_from": "2026-10-03", "date_to": "2026-10-04"},
        headers={"Accept-Language": "en"},
    ).json()
    assert stay["name"] == "Blue Pearl Ger Camp"
    assert stay["cancellation_policy"]["name"] == "Moderate"
    assert {a["date"] for a in stay["availability"]} == {"2026-10-03", "2026-10-04"}


def test_events_overlapping_dates(client, seeded):
    events = client.get(f"{API}/events", params={"date_from": "2026-10-03", "date_to": "2026-10-04"}).json()
    ids = {e["id"] for e in events}
    assert "event_golden_eagle_festival_2026" in ids
    assert "event_national_naadam_2027" not in ids


def test_train_matches_intermediate_stop(client, seeded):
    trains = client.get(f"{API}/transport/schedules", params={"mode": "train", "to_place_id": "place_darkhan"}).json()
    assert {t["id"] for t in trains} == {"sched_train_ub_sukhbaatar", "sched_train_ub_erdenet"}


def test_transport_availability_only_open(client, seeded):
    rows = client.get(
        f"{API}/transport/availability", params={"schedule_id": "sched_train_ub_sukhbaatar", "date": "2026-10-03"}
    ).json()
    assert rows and all(r["seats_left"] > 0 for r in rows)


def test_shared_rides_hide_cancelled(client, seeded):
    rides = {r["id"] for r in client.get(f"{API}/shared-rides").json()}
    assert "ride_012" not in rides
    assert "ride_001" in rides


def test_self_drive_vehicles_free_on_date(client, seeded):
    vehicles = client.get(f"{API}/vehicles", params={"rental_mode": "self_drive", "date": "2026-10-10"}).json()
    ids = {v["id"] for v in vehicles}
    assert all(v["rental"]["mode"] == "self_drive" for v in vehicles)
    assert "veh_rent_03" not in ids  # booked by Jambaa's trip


def test_vehicles_with_driver_embed_driver(client, seeded):
    vehicles = client.get(f"{API}/vehicles", params={"rental_mode": "with_driver", "region": "west"}).json()
    assert vehicles and all(v["driver"]["id"] == v["driver_id"] for v in vehicles)


def test_fuel_prices(client, seeded):
    assert client.get(f"{API}/config/fuel").json()["price_per_liter_mnt"]["diesel"] > 0


def test_my_trips_require_login(client, seeded):
    assert client.get(f"{API}/me/trips").status_code == 401


def test_my_trips_only_show_own_trips(client, seeded):
    headers = _auth(client, "jambaa@nashatech.com")
    trips = client.get(f"{API}/me/trips", headers=headers).json()
    assert [t["id"] for t in trips] == ["trip_jamba_east"]
    assert client.get(f"{API}/me/trips/trip_anand_eagle", headers=headers).status_code == 404


def test_my_trip_detail(client, seeded):
    headers = {**_auth(client, "tsendayush@nashatech.com"), "Accept-Language": "en"}
    trip = client.get(f"{API}/me/trips/trip_tsende_darkhan", headers=headers).json()
    assert trip["title"] == "Weekend in Darkhan by train"
    assert trip["itinerary"]["version"] == 1
    assert {p["status"] for p in trip["payments"]} == {"paid", "refunded"}
    assert trip["refunds"][0]["reason_text"] == "Driver cancelled (car broke down)"


def test_my_payments_filter_by_status(client, seeded):
    headers = _auth(client, "jambaa@nashatech.com")
    pending = client.get(f"{API}/me/payments", params={"status": "approved_by_user"}, headers=headers).json()
    assert [p["id"] for p in pending] == ["pay_jamba_001"]


def test_images_have_attribution(client, seeded):
    event = next(e for e in client.get(f"{API}/events").json() if e["id"] == "event_golden_eagle_festival_2026")
    assert event["cover_image_url"] == event["images"][0]["url"]
    for image in event["images"]:
        assert image["match"] == "event_topic"
        assert image["license"] and image["author"] and image["source"].startswith("https://commons.wikimedia.org/")
    stay = client.get(f"{API}/stays/stay_terkhiin_camp_white_lake").json()
    assert stay["images"][0]["match"] == "near_stay"


def test_public_endpoints_hide_phone_numbers(client, seeded):
    rides = client.get(f"{API}/shared-rides", params={"only_bookable": "false"}).json()
    assert all("phone" not in (r.get("posted_by") or {}) for r in rides)
    assert "phone" not in client.get(f"{API}/stays/stay_ub_hotel_blue_sky").json()["owner"]
    assert all("phone" not in d for d in client.get(f"{API}/drivers").json())
    vehicles = client.get(f"{API}/vehicles", params={"rental_mode": "with_driver"}).json()
    assert all("phone" not in v["driver"] for v in vehicles if v["driver"])


def test_bad_coordinates_are_rejected(client, seeded):
    assert client.get(f"{API}/places", params={"lng": 100, "lat": 200}).status_code == 422
    assert client.get(f"{API}/stays", params={"lng": 100, "lat": 47, "radius_km": -5}).status_code == 422
    assert client.get(f"{API}/regions/locate", params={"lng": 500, "lat": 0}).status_code == 422


def test_invoices_are_owned_localized_and_do_not_expose_payment_internals(client, seeded):
    headers = _auth(client, "jambaa@nashatech.com")
    rows = client.get(f"{API}/me/invoices", headers={**headers, "Accept-Language": "en"})
    assert rows.status_code == 200, rows.text
    invoices = rows.json()
    assert invoices
    own_ids = {p["_id"] for p in seeded["payments"].find({"user_id": "user_jamba"})}
    assert {i["id"] for i in invoices} == own_ids
    for invoice in invoices:
        payment = seeded["payments"].find_one({"_id": invoice["id"]})
        assert invoice["amount_mnt"] == payment["amount_mnt"]
        assert invoice["status"] == payment["status"]
        assert not {"consent", "charge", "idempotency_key", "payment_mandate_id"}.intersection(invoice)
        assert isinstance(invoice["trip_title"], str)
        expected_paid = [s["at"] for s in payment["status_history"] if s["status"] == "paid"]
        assert invoice["paid_at"] == (expected_paid[-1] if expected_paid else None)
        assert invoice["checkout_id"] is None  # legacy seeded payments have no AP2 checkout
