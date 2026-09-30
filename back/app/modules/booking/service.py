"""Booking saga for stays: hold every night, sign the checkout, then confirm, release or expire.

    create_checkout      hold units night by night (all or none) -> bookings "held" -> merchant-signed checkout
    on_payment_paid      holds and bookings -> confirmed, trip -> booked            (outbox: payment.paid)
    on_payment_failed    holds released, bookings and checkout cancelled             (outbox: payment.failed)
    expire_checkouts     unpaid past expiry: cancel the rail invoice, then release   (sweeper)

A hold takes units out of ``stay_availability.available`` with a conditional ``$inc`` (never below zero), so two
travellers cannot both get the last ger. If a payment lands after its holds expired, the units are taken again;
if that is no longer possible every booking of the checkout is cancelled and a refund is flagged (all or none).
Every handler is idempotent: an outbox event can be delivered twice.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Literal
from uuid import uuid4

from pymongo import ReturnDocument
from pymongo.client_session import ClientSession
from pymongo.database import Database

from app import ap2
from app.ap2.checkout import checkout_claims
from app.core.config import settings
from app.core.keys import merchant_key, merchant_kid
from app.db.outbox import emit, iso
from app.db.transactions import run_in_transaction
from app.modules import payment
from app.modules.payment.rails import PaymentRail
from app.schemas.commerce import CheckoutDoc, CheckoutLine, HoldDoc
from app.schemas.travel import AuditLogDoc, BookingDoc, StayAvailabilityDoc, StayDoc, TripDoc

HOLD_MINUTES = 15

BookingErrorCode = Literal["trip_not_found", "stay_not_found", "unit_not_offered", "too_many_guests", "unavailable"]


class BookingError(Exception):
    def __init__(self, code: BookingErrorCode, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code: BookingErrorCode = code
        self.detail = detail


@dataclass(frozen=True)
class StayRequest:
    stay_id: str
    unit_type: str
    check_in: str  # YYYY-MM-DD
    nights: int
    units: int
    guests: int

    def dates(self) -> list[str]:
        start = date.fromisoformat(self.check_in)
        return [(start + timedelta(days=i)).isoformat() for i in range(self.nights)]


def _dump(model: Any) -> dict[str, Any]:
    return model.model_dump(by_alias=True, exclude={"is_mock"})


def _audit(db: Database, session: ClientSession | None, now: datetime, **fields: Any) -> None:
    doc = AuditLogDoc.model_validate({"_id": f"audit_{uuid4().hex}", "ts": iso(now), "details": {}, **fields})
    db[AuditLogDoc.collection].insert_one(_dump(doc), session=session)


def _return_units(db: Database, hold: dict, session: ClientSession | None) -> None:
    db[StayAvailabilityDoc.collection].update_one(
        {"stay_id": hold["stay_id"], "date": hold["date"], "unit_type": hold["unit_type"]},
        {"$inc": {"available": hold["qty"]}},
        session=session,
    )


def _take_units(db: Database, stay_id: str, unit_type: str, day: str, qty: int, session: ClientSession | None):
    """Atomically take ``qty`` units for one night; None when not enough are free (or the stay is closed)."""
    return db[StayAvailabilityDoc.collection].find_one_and_update(
        {"stay_id": stay_id, "unit_type": unit_type, "date": day, "status": "open", "available": {"$gte": qty}},
        {"$inc": {"available": -qty}},
        session=session,
        return_document=ReturnDocument.AFTER,
    )


# ----------------------------------------------------------------------------- create


def _plan(db: Database, stays: list[StayRequest]) -> list[tuple[StayRequest, dict, dict]]:
    if not stays:
        raise BookingError("unavailable", "no stays requested")
    plan = []
    for req in stays:
        if req.nights < 1 or req.units < 1 or req.guests < 1:
            raise BookingError("unavailable", "nights, units and guests must be at least 1")
        stay = db[StayDoc.collection].find_one({"_id": req.stay_id})
        if stay is None:
            raise BookingError("stay_not_found", req.stay_id)
        unit = next((u for u in stay["units"] if u["unit_type"] == req.unit_type), None)
        if unit is None:
            raise BookingError("unit_not_offered", f"{req.stay_id} has no {req.unit_type}")
        if req.guests > req.units * unit["beds_per_unit"]:
            raise BookingError(
                "too_many_guests", f"{req.units} x {req.unit_type} sleeps {req.units * unit['beds_per_unit']}"
            )
        plan.append((req, stay, unit))
    return plan


def create_checkout(
    db: Database, *, user_id: str, trip_id: str, stays: list[StayRequest], now: datetime
) -> dict[str, Any]:
    """Hold every requested night and return the merchant-signed checkout the user will approve."""
    trip = db[TripDoc.collection].find_one({"_id": trip_id, "user_id": user_id})
    if trip is None:
        raise BookingError("trip_not_found")
    plan = _plan(db, stays)
    checkout_id = f"chk_{uuid4().hex[:16]}"
    expires = now + timedelta(minutes=HOLD_MINUTES)

    def work(session: ClientSession | None) -> dict[str, Any]:
        taken: list[dict] = []
        lines: list[dict] = []
        bookings: list[dict] = []
        try:
            for req, stay, unit in plan:
                per_person = unit["price_basis"] == "per_person"
                stay_total = 0
                for day in req.dates():
                    row = _take_units(db, req.stay_id, req.unit_type, day, req.units, session)
                    if row is None:
                        raise BookingError("unavailable", f"{req.stay_id} {req.unit_type} on {day}")
                    taken.append({"stay_id": req.stay_id, "unit_type": req.unit_type, "date": day, "qty": req.units})
                    qty = req.guests if per_person else req.units
                    line = CheckoutLine.model_validate(
                        {
                            "kind": "stay",
                            "ref_id": req.stay_id,
                            "qty": qty,
                            "unit_price_mnt": row["price_mnt"],
                            "total_mnt": qty * row["price_mnt"],
                            "label": stay["name"],
                            "date": day,
                            "unit_type": req.unit_type,
                        }
                    )
                    lines.append(line.model_dump())
                    stay_total += line.total_mnt
                check_out = (date.fromisoformat(req.check_in) + timedelta(days=req.nights)).isoformat()
                bookings.append(
                    _dump(
                        BookingDoc.model_validate(
                            {
                                "_id": f"bk_{checkout_id}_{len(bookings) + 1}",
                                "trip_id": trip_id,
                                "user_id": user_id,
                                "kind": "stay",
                                "status": "held",
                                "total_price_mnt": stay_total,
                                "checkout_id": checkout_id,
                                "stay_id": req.stay_id,
                                "unit_type": req.unit_type,
                                "check_in": req.check_in,
                                "check_out": check_out,
                                "nights": req.nights,
                                "guests": req.guests,
                                "cancellation_policy_id": stay["cancellation_policy_id"],
                            }
                        )
                    )
                )
        except BookingError:
            if session is None:  # no transaction to abort: give the units back by hand
                for hold in taken:
                    _return_units(db, hold, None)
            raise

        holds = [
            _dump(
                HoldDoc.model_validate(
                    {
                        "_id": f"hold_{checkout_id}_{i}",
                        "trip_id": trip_id,
                        "checkout_id": checkout_id,
                        **t,
                        "status": "held",
                        "expires_at": iso(expires),
                        "created_at": iso(now),
                    }
                )
            )
            for i, t in enumerate(taken, start=1)
        ]
        total = sum(line["total_mnt"] for line in lines)
        claims = checkout_claims(
            merchant_id=settings.MERCHANT_ID,
            checkout_id=checkout_id,
            trip_id=trip_id,
            lines=lines,
            total_mnt=total,
            iat=int(now.timestamp()),
            exp=int(expires.timestamp()),
        )
        token, digest = ap2.sign_checkout(claims, merchant_key(), kid=merchant_kid())
        checkout = _dump(
            CheckoutDoc.model_validate(
                {
                    "_id": checkout_id,
                    "trip_id": trip_id,
                    "user_id": user_id,
                    "lines": lines,
                    "total_mnt": total,
                    "hold_ids": [h["_id"] for h in holds],
                    "checkout_jwt": token,
                    "checkout_hash": digest,
                    "status": "open",
                    "expires_at": iso(expires),
                    "created_at": iso(now),
                }
            )
        )
        db[HoldDoc.collection].insert_many(holds, session=session)
        db[BookingDoc.collection].insert_many(bookings, session=session)
        db[CheckoutDoc.collection].insert_one(checkout, session=session)
        db[TripDoc.collection].update_one(
            {"_id": trip_id, "status": {"$in": ["planned", "awaiting_payment"]}},
            {"$set": {"status": "awaiting_payment"}},
            session=session,
        )
        _audit(
            db,
            session,
            now,
            actor="system",
            user_id=user_id,
            trip_id=trip_id,
            action="checkout_created",
            entity="checkout",
            entity_id=checkout_id,
            amount_mnt=total,
            details={"holds": len(holds), "expires_at": iso(expires)},
        )
        return checkout

    return run_in_transaction(db, work)


# ----------------------------------------------------------------------------- settle


def _release(db: Database, checkout: dict, *, hold_from: str, checkout_to: str, now: datetime, session) -> int:
    """Give back the units of every ``hold_from`` hold, cancel held bookings, move the checkout. Returns holds freed."""
    freed = 0
    for hold in db[HoldDoc.collection].find({"checkout_id": checkout["_id"], "status": hold_from}, session=session):
        target = "expired" if checkout_to == "expired" else "released"
        moved = db[HoldDoc.collection].update_one(
            {"_id": hold["_id"], "status": hold_from}, {"$set": {"status": target}}, session=session
        )
        if moved.modified_count:
            _return_units(db, hold, session)
            freed += 1
    db[BookingDoc.collection].update_many(
        {"checkout_id": checkout["_id"], "status": "held"}, {"$set": {"status": "cancelled"}}, session=session
    )
    db[CheckoutDoc.collection].update_one({"_id": checkout["_id"]}, {"$set": {"status": checkout_to}}, session=session)
    db[TripDoc.collection].update_one(
        {"_id": checkout["trip_id"], "status": "awaiting_payment"}, {"$set": {"status": "planned"}}, session=session
    )
    return freed


def on_payment_paid(db: Database, event: dict, now: datetime) -> None:
    checkout = db[CheckoutDoc.collection].find_one({"_id": event["payload"]["checkout_id"]})
    if checkout is None:
        raise LookupError(f"checkout {event['payload']['checkout_id']} not found")
    payment_id = event["payload"]["payment_id"]

    def work(session: ClientSession | None) -> None:
        holds = list(db[HoldDoc.collection].find({"checkout_id": checkout["_id"]}, session=session))
        if holds and all(h["status"] == "confirmed" for h in holds):
            return  # already confirmed by an earlier delivery
        lost = []
        for hold in holds:
            if hold["status"] == "held":
                db[HoldDoc.collection].update_one(
                    {"_id": hold["_id"], "status": "held"}, {"$set": {"status": "confirmed"}}, session=session
                )
            elif hold["status"] in ("expired", "released"):
                # Paid after the hold lapsed: take the units again if they are still free
                if _take_units(db, hold["stay_id"], hold["unit_type"], hold["date"], hold["qty"], session):
                    db[HoldDoc.collection].update_one(
                        {"_id": hold["_id"]}, {"$set": {"status": "confirmed"}}, session=session
                    )
                else:
                    lost.append(hold)

        if lost:
            # All or none: give back what was confirmed, cancel every booking, flag the refund
            for hold in db[HoldDoc.collection].find(
                {"checkout_id": checkout["_id"], "status": "confirmed"}, session=session
            ):
                db[HoldDoc.collection].update_one(
                    {"_id": hold["_id"]}, {"$set": {"status": "released"}}, session=session
                )
                _return_units(db, hold, session)
            db[BookingDoc.collection].update_many(
                {"checkout_id": checkout["_id"], "status": {"$in": ["held", "cancelled"]}},
                {"$set": {"status": "cancelled", "payment_id": payment_id}},
                session=session,
            )
            emit(
                db,
                type="booking.cancelled",
                aggregate_id=checkout["_id"],
                payload={
                    "checkout_id": checkout["_id"],
                    "payment_id": payment_id,
                    "refund_required": True,
                    "lost_nights": [f"{h['stay_id']} {h['date']}" for h in lost],
                },
                now=now,
                session=session,
            )
            _audit(
                db,
                session,
                now,
                actor="system",
                user_id=checkout["user_id"],
                trip_id=checkout["trip_id"],
                action="paid_but_unavailable",
                entity="checkout",
                entity_id=checkout["_id"],
                amount_mnt=checkout["total_mnt"],
                details={"lost": len(lost)},
            )
            return

        db[BookingDoc.collection].update_many(
            {"checkout_id": checkout["_id"], "status": {"$in": ["held", "cancelled"]}},
            {"$set": {"status": "confirmed", "payment_id": payment_id}},
            session=session,
        )
        db[TripDoc.collection].update_one({"_id": checkout["trip_id"]}, {"$set": {"status": "booked"}}, session=session)
        emit(
            db,
            type="booking.confirmed",
            aggregate_id=checkout["_id"],
            payload={"checkout_id": checkout["_id"], "payment_id": payment_id, "trip_id": checkout["trip_id"]},
            now=now,
            session=session,
        )
        _audit(
            db,
            session,
            now,
            actor="system",
            user_id=checkout["user_id"],
            trip_id=checkout["trip_id"],
            action="booking_confirmed",
            entity="checkout",
            entity_id=checkout["_id"],
            amount_mnt=checkout["total_mnt"],
        )

    run_in_transaction(db, work)


def on_payment_failed(db: Database, event: dict, now: datetime) -> None:
    checkout = db[CheckoutDoc.collection].find_one({"_id": event["payload"]["checkout_id"]})
    if checkout is None or checkout["status"] not in ("open", "paid"):
        return

    def work(session: ClientSession | None) -> None:
        _release(db, checkout, hold_from="held", checkout_to="cancelled", now=now, session=session)
        _audit(
            db,
            session,
            now,
            actor="system",
            user_id=checkout["user_id"],
            trip_id=checkout["trip_id"],
            action="checkout_cancelled_payment_failed",
            entity="checkout",
            entity_id=checkout["_id"],
        )

    run_in_transaction(db, work)


OUTBOX_HANDLERS = {"payment.paid": on_payment_paid, "payment.failed": on_payment_failed}


# ----------------------------------------------------------------------------- expiry sweeper


def expire_checkouts(db: Database, rail: PaymentRail, *, now: datetime, limit: int = 50) -> int:
    """Release open checkouts past their expiry whose payment can no longer land. Returns how many expired."""
    expired = 0
    due = db[CheckoutDoc.collection].find({"status": "open", "expires_at": {"$lt": iso(now)}}).limit(limit)
    for checkout in list(due):
        if not payment.cancel_unpaid_charge(db, rail, checkout_id=checkout["_id"], now=now):
            continue  # it may be paid right now; the payment callback settles it

        def work(session: ClientSession | None, checkout: dict = checkout) -> bool:
            moved = db[CheckoutDoc.collection].update_one(
                {"_id": checkout["_id"], "status": "open"}, {"$set": {"status": "expired"}}, session=session
            )
            if moved.modified_count == 0:
                return False
            freed = _release(db, checkout, hold_from="held", checkout_to="expired", now=now, session=session)
            emit(
                db,
                type="checkout.expired",
                aggregate_id=checkout["_id"],
                payload={"checkout_id": checkout["_id"], "holds_released": freed},
                now=now,
                session=session,
            )
            return True

        expired += int(run_in_transaction(db, work))
    return expired
