"""Booking saga on the mock data: holds, all-or-none, payment settles or releases, expiry, late payments."""

from datetime import date, timedelta
from urllib.parse import urlsplit

import pytest
from fastapi.testclient import TestClient

from app import ap2
from app.core.keys import merchant_public_jwk
from app.db.outbox import dispatch
from app.modules import booking, payment
from app.modules.booking import StayRequest
from app.modules.payment.rails import QPayRail
from app.seeds.mock_seed import load_mock_collections
from app.services import qpay_sim
from test.payment_helpers import NOW, payment_mandate

USER = "user_jamba"
TRIP = "trip_jamba_east"


@pytest.fixture
def seeded(db):
    load_mock_collections(db, real_server=False)
    db["trips"].update_one({"_id": TRIP}, {"$set": {"user_id": USER, "status": "planned"}})
    return db


@pytest.fixture
def sim(monkeypatch):
    sent: list[str] = []
    monkeypatch.setattr(qpay_sim.httpx, "post", lambda url, **_: sent.append(str(url)))
    with TestClient(qpay_sim.app) as client:
        client.post("/_sim/reset")
        client.sent = sent  # type: ignore[attr-defined]
        yield client


@pytest.fixture
def rail(sim):
    return QPayRail(
        rail_id="sim",
        base_url="x",
        username=qpay_sim.USERNAME,
        password=qpay_sim.PASSWORD,
        invoice_code="S",
        client=sim,
    )


def _free_nights(db, *, basis, nights=2, units=1, exactly=None):
    """A (stay, unit) with `units` free on `nights` consecutive open nights (or exactly `exactly` on the first)."""
    for stay in db["stays"].find():
        for unit in stay["units"]:
            if unit["price_basis"] != basis:
                continue
            rows = {
                r["date"]: r
                for r in db["stay_availability"].find(
                    {"stay_id": stay["_id"], "unit_type": unit["unit_type"], "status": "open"}
                )
            }
            for first in sorted(rows):
                dates = [(date.fromisoformat(first) + timedelta(days=i)).isoformat() for i in range(nights)]
                if all(d in rows and rows[d]["available"] >= units for d in dates) and (
                    exactly is None or rows[dates[0]]["available"] == exactly
                ):
                    return stay, unit, dates
    raise AssertionError("no suitable stay in the mock data")


def _available(db, stay_id, unit_type, day):
    return db["stay_availability"].find_one({"stay_id": stay_id, "unit_type": unit_type, "date": day})["available"]


def _checkout(db, stay, unit, dates, units=1, guests=1, now=NOW):
    req = StayRequest(stay["_id"], unit["unit_type"], dates[0], len(dates), units, guests)
    return booking.create_checkout(db, user_id=USER, trip_id=TRIP, stays=[req], now=now)


def _pay(db, rail, checkout, user_key, kid, now=NOW):
    return payment.start_payment(
        db,
        rail,
        user_id=USER,
        checkout_id=checkout["_id"],
        payment_mandate=payment_mandate(user_key, checkout["checkout_jwt"], amount_mnt=checkout["total_mnt"]),
        kid=kid,
        instrument="qpay_qr",
        now=now,
    ).payment


@pytest.fixture
def signer(seeded):
    key = ap2.generate_key()
    return key, payment.register_user_key(seeded, user_id=USER, jwk=ap2.public_jwk(key), now=NOW)


# ----------------------------------------------------------------------------- create


def test_create_checkout_holds_every_night(seeded):
    stay, unit, dates = _free_nights(seeded, basis="per_unit", nights=2)
    before = [_available(seeded, stay["_id"], unit["unit_type"], d) for d in dates]

    checkout = _checkout(seeded, stay, unit, dates)

    assert [_available(seeded, stay["_id"], unit["unit_type"], d) for d in dates] == [b - 1 for b in before]
    assert len(checkout["lines"]) == 2 and [line["date"] for line in checkout["lines"]] == dates
    assert checkout["total_mnt"] == sum(line["total_mnt"] for line in checkout["lines"]) == 2 * unit["price_mnt"]
    assert seeded["holds"].count_documents({"checkout_id": checkout["_id"], "status": "held"}) == 2
    b = seeded["bookings"].find_one({"checkout_id": checkout["_id"]})
    assert b["status"] == "held" and b["nights"] == 2 and b["check_out"] > b["check_in"]
    assert seeded["trips"].find_one({"_id": TRIP})["status"] == "awaiting_payment"
    claims = ap2.verify_checkout(checkout["checkout_jwt"], merchant_public_jwk(), now=int(NOW.timestamp()))
    assert claims["total"]["amount"] == ap2.mnt_to_minor(checkout["total_mnt"])


def test_per_person_price_counts_guests(seeded):
    stay, unit, dates = _free_nights(seeded, basis="per_person", nights=1)
    guests = min(2, unit["beds_per_unit"])
    checkout = _checkout(seeded, stay, unit, dates, guests=guests)
    assert checkout["lines"][0]["qty"] == guests
    assert checkout["total_mnt"] == guests * unit["price_mnt"]


def test_one_missing_night_holds_nothing(seeded):
    stay, unit, dates = _free_nights(seeded, basis="per_unit", nights=2)
    seeded["stay_availability"].update_one(
        {"stay_id": stay["_id"], "unit_type": unit["unit_type"], "date": dates[1]}, {"$set": {"available": 0}}
    )
    first_before = _available(seeded, stay["_id"], unit["unit_type"], dates[0])

    with pytest.raises(booking.BookingError) as info:
        _checkout(seeded, stay, unit, dates)

    assert info.value.code == "unavailable" and dates[1] in info.value.detail
    assert _available(seeded, stay["_id"], unit["unit_type"], dates[0]) == first_before  # given back
    assert seeded["holds"].count_documents({}) == seeded["checkouts"].count_documents({}) == 0


def test_the_last_unit_goes_to_one_traveller(seeded):
    stay, unit, dates = _free_nights(seeded, basis="per_unit", nights=1)
    seeded["stay_availability"].update_one(
        {"stay_id": stay["_id"], "unit_type": unit["unit_type"], "date": dates[0]}, {"$set": {"available": 1}}
    )
    _checkout(seeded, stay, unit, dates)
    with pytest.raises(booking.BookingError):
        _checkout(seeded, stay, unit, dates)
    assert _available(seeded, stay["_id"], unit["unit_type"], dates[0]) == 0


@pytest.mark.parametrize(
    ("change", "code"),
    [
        ({"stay_id": "stay_nowhere"}, "stay_not_found"),
        ({"unit_type": "suite_that_does_not_exist"}, "unit_not_offered"),
        ({"guests": 99}, "too_many_guests"),
    ],
)
def test_bad_requests(seeded, change, code):
    stay, unit, dates = _free_nights(seeded, basis="per_unit", nights=1)
    req = {
        "stay_id": stay["_id"],
        "unit_type": unit["unit_type"],
        "check_in": dates[0],
        "nights": 1,
        "units": 1,
        "guests": 1,
    }
    with pytest.raises(booking.BookingError) as info:
        booking.create_checkout(seeded, user_id=USER, trip_id=TRIP, stays=[StayRequest(**{**req, **change})], now=NOW)
    assert info.value.code == code


def test_someone_elses_trip_is_not_found(seeded):
    stay, unit, dates = _free_nights(seeded, basis="per_unit", nights=1)
    req = StayRequest(stay["_id"], unit["unit_type"], dates[0], 1, 1, 1)
    with pytest.raises(booking.BookingError) as info:
        booking.create_checkout(seeded, user_id="user_anand", trip_id=TRIP, stays=[req], now=NOW)
    assert info.value.code == "trip_not_found"


# ----------------------------------------------------------------------------- settle


def _callback_all(db, rail, sim):
    for url in sim.sent:
        parts = urlsplit(url)
        _, pid, token = parts.path.rsplit("/", 2)
        payment.handle_callback(db, rail, payment_id=pid, token=token, query={}, body=b"", now=NOW)
    sim.sent.clear()


def test_paid_checkout_is_booked(seeded, rail, sim, signer):
    stay, unit, dates = _free_nights(seeded, basis="per_unit", nights=2)
    checkout = _checkout(seeded, stay, unit, dates)
    p = _pay(seeded, rail, checkout, *signer)
    sim.post(f"/_sim/invoices/{p['provider_ref']}/pay", params={"callbacks": 2})
    _callback_all(seeded, rail, sim)

    assert dispatch(seeded, booking.OUTBOX_HANDLERS, now=NOW) == 1
    assert dispatch(seeded, booking.OUTBOX_HANDLERS, now=NOW) == 0  # nothing left to deliver

    assert seeded["holds"].count_documents({"checkout_id": checkout["_id"], "status": "confirmed"}) == 2
    b = seeded["bookings"].find_one({"checkout_id": checkout["_id"]})
    assert b["status"] == "confirmed" and b["payment_id"] == p["_id"]
    assert seeded["trips"].find_one({"_id": TRIP})["status"] == "booked"
    assert seeded["outbox"].count_documents({"type": "booking.confirmed"}) == 1

    # Delivering payment.paid again (after a crash) changes nothing
    event = seeded["outbox"].find_one({"type": "payment.paid"})
    booking.on_payment_paid(seeded, event, NOW)
    assert seeded["outbox"].count_documents({"type": "booking.confirmed"}) == 1


def test_failed_payment_releases_the_holds(seeded, rail, sim, signer):
    stay, unit, dates = _free_nights(seeded, basis="per_unit", nights=2)
    before = [_available(seeded, stay["_id"], unit["unit_type"], d) for d in dates]
    checkout = _checkout(seeded, stay, unit, dates)
    p = _pay(seeded, rail, checkout, *signer)
    sim.post(f"/_sim/invoices/{p['provider_ref']}/fail")
    payment.handle_callback(
        seeded, rail, payment_id=p["_id"], token=payment.webhook_token(p["_id"]), query={}, body=b"", now=NOW
    )
    dispatch(seeded, booking.OUTBOX_HANDLERS, now=NOW)

    assert [_available(seeded, stay["_id"], unit["unit_type"], d) for d in dates] == before
    assert seeded["checkouts"].find_one({"_id": checkout["_id"]})["status"] == "cancelled"
    assert seeded["bookings"].find_one({"checkout_id": checkout["_id"]})["status"] == "cancelled"
    assert seeded["trips"].find_one({"_id": TRIP})["status"] == "planned"


# ----------------------------------------------------------------------------- expiry


def test_unpaid_checkout_expires_and_its_invoice_is_closed(seeded, rail, sim, signer):
    stay, unit, dates = _free_nights(seeded, basis="per_unit", nights=2)
    before = [_available(seeded, stay["_id"], unit["unit_type"], d) for d in dates]
    checkout = _checkout(seeded, stay, unit, dates)
    p = _pay(seeded, rail, checkout, *signer)

    assert booking.expire_checkouts(seeded, rail, now=NOW + timedelta(minutes=5)) == 0  # not due yet
    assert booking.expire_checkouts(seeded, rail, now=NOW + timedelta(minutes=16)) == 1

    assert [_available(seeded, stay["_id"], unit["unit_type"], d) for d in dates] == before
    assert seeded["checkouts"].find_one({"_id": checkout["_id"]})["status"] == "expired"
    assert seeded["payments"].find_one({"_id": p["_id"]})["status"] == "expired"
    assert seeded["holds"].count_documents({"checkout_id": checkout["_id"], "status": "expired"}) == 2
    assert [i["status"] for i in sim.get("/_sim/invoices").json()] == ["CANCELLED"]
    assert seeded["outbox"].count_documents({"type": "checkout.expired"}) == 1


def test_expiry_waits_when_the_invoice_is_already_paid(seeded, rail, sim, signer):
    stay, unit, dates = _free_nights(seeded, basis="per_unit", nights=1)
    checkout = _checkout(seeded, stay, unit, dates)
    p = _pay(seeded, rail, checkout, *signer)
    sim.post(f"/_sim/invoices/{p['provider_ref']}/pay", params={"callbacks": 0})  # paid; callback still on its way

    assert booking.expire_checkouts(seeded, rail, now=NOW + timedelta(minutes=16)) == 0
    assert seeded["holds"].count_documents({"checkout_id": checkout["_id"], "status": "held"}) == 1

    payment.handle_callback(
        seeded, rail, payment_id=p["_id"], token=payment.webhook_token(p["_id"]), query={}, body=b"", now=NOW
    )
    dispatch(seeded, booking.OUTBOX_HANDLERS, now=NOW)
    assert seeded["bookings"].find_one({"checkout_id": checkout["_id"]})["status"] == "confirmed"


def test_expiry_without_a_payment(seeded, rail):
    stay, unit, dates = _free_nights(seeded, basis="per_unit", nights=1)
    checkout = _checkout(seeded, stay, unit, dates)
    assert booking.expire_checkouts(seeded, rail, now=NOW + timedelta(minutes=16)) == 1
    assert seeded["checkouts"].find_one({"_id": checkout["_id"]})["status"] == "expired"


# ----------------------------------------------------------------------------- late payment


def _expire_holds_by_hand(db, checkout):
    for hold in db["holds"].find({"checkout_id": checkout["_id"]}):
        db["holds"].update_one({"_id": hold["_id"]}, {"$set": {"status": "expired"}})
        db["stay_availability"].update_one(
            {"stay_id": hold["stay_id"], "date": hold["date"], "unit_type": hold["unit_type"]},
            {"$inc": {"available": hold["qty"]}},
        )


def _paid_event(checkout):
    return {"_id": "evt_x", "type": "payment.paid", "payload": {"checkout_id": checkout["_id"], "payment_id": "pay_x"}}


def test_late_payment_takes_the_units_again_when_free(seeded):
    stay, unit, dates = _free_nights(seeded, basis="per_unit", nights=1)
    checkout = _checkout(seeded, stay, unit, dates)
    _expire_holds_by_hand(seeded, checkout)
    before = _available(seeded, stay["_id"], unit["unit_type"], dates[0])

    booking.on_payment_paid(seeded, _paid_event(checkout), NOW)

    assert _available(seeded, stay["_id"], unit["unit_type"], dates[0]) == before - 1
    assert seeded["bookings"].find_one({"checkout_id": checkout["_id"]})["status"] == "confirmed"


def test_late_payment_for_a_sold_night_cancels_all_and_flags_a_refund(seeded):
    stay, unit, dates = _free_nights(seeded, basis="per_unit", nights=2)
    checkout = _checkout(seeded, stay, unit, dates)
    _expire_holds_by_hand(seeded, checkout)
    seeded["stay_availability"].update_one(  # someone else took the second night meanwhile
        {"stay_id": stay["_id"], "unit_type": unit["unit_type"], "date": dates[1]}, {"$set": {"available": 0}}
    )
    first_before = _available(seeded, stay["_id"], unit["unit_type"], dates[0])

    booking.on_payment_paid(seeded, _paid_event(checkout), NOW)

    assert _available(seeded, stay["_id"], unit["unit_type"], dates[0]) == first_before  # not kept
    assert seeded["bookings"].find_one({"checkout_id": checkout["_id"]})["status"] == "cancelled"
    event = seeded["outbox"].find_one({"type": "booking.cancelled"})
    assert event["payload"]["refund_required"] is True and len(event["payload"]["lost_nights"]) == 1


# ----------------------------------------------------------------------------- outbox delivery


def test_failing_handler_puts_the_event_back(seeded):
    seeded["outbox"].insert_one(
        {
            "_id": "evt_bad",
            "type": "payment.paid",
            "aggregate_id": "x",
            "payload": {"checkout_id": "chk_missing", "payment_id": "p"},
            "created_at": "2026-10-01T08:00:00Z",
            "dispatched_at": None,
            "attempts": 0,
        }
    )
    assert dispatch(seeded, booking.OUTBOX_HANDLERS, now=NOW, limit=1) == 0
    event = seeded["outbox"].find_one({"_id": "evt_bad"})
    assert event["dispatched_at"] is None and event["attempts"] == 1 and "chk_missing" in event["last_error"]


def test_background_tick_delivers_events_and_expires(seeded, rail, monkeypatch):
    from app import workers

    monkeypatch.setattr(workers, "get_database", lambda: seeded)
    monkeypatch.setattr(workers, "configured_rail", lambda: rail)
    stay, unit, dates = _free_nights(seeded, basis="per_unit", nights=1)
    checkout = _checkout(seeded, stay, unit, dates)

    workers.run_once(NOW + timedelta(minutes=16))

    assert seeded["checkouts"].find_one({"_id": checkout["_id"]})["status"] == "expired"


def test_background_worker_starts_and_stops(monkeypatch):
    from app import workers

    ticks = []
    monkeypatch.setattr(workers, "OUTBOX_EVERY_SECONDS", 0.01)
    monkeypatch.setattr(workers, "run_once", lambda **kw: ticks.append(kw))
    stop = workers.start()
    import time

    time.sleep(0.1)
    stop.set()
    assert ticks
