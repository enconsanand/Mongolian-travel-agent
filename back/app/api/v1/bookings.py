"""Bookings API: hold stays for a trip and get the checkout to approve; read a checkout with its payment."""

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.api.v1.deps import ActiveUser, DbSession
from app.api.v1.payments import Now
from app.modules import booking
from app.schemas.travel import UnitType

router = APIRouter()

_STATUS = {
    "trip_not_found": status.HTTP_404_NOT_FOUND,
    "stay_not_found": status.HTTP_404_NOT_FOUND,
    "unit_not_offered": status.HTTP_422_UNPROCESSABLE_CONTENT,
    "too_many_guests": status.HTTP_422_UNPROCESSABLE_CONTENT,
    "unavailable": status.HTTP_409_CONFLICT,
}


class StayIn(BaseModel):
    stay_id: str
    unit_type: UnitType
    check_in: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    nights: int = Field(ge=1, le=30)
    units: int = Field(default=1, ge=1, le=20)
    guests: int = Field(ge=1, le=60)


class CheckoutIn(BaseModel):
    stays: list[StayIn] = Field(min_length=1, max_length=14)


def _checkout_out(c: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": c["_id"],
        "trip_id": c["trip_id"],
        "status": c["status"],
        "lines": c["lines"],
        "total_mnt": c["total_mnt"],
        "expires_at": c["expires_at"],
        # The browser builds both AP2 mandates from these two and signs them on the trusted surface
        "checkout_jwt": c["checkout_jwt"],
        "checkout_hash": c["checkout_hash"],
    }


@router.post("/me/trips/{trip_id}/checkouts", tags=["Bookings"], status_code=status.HTTP_201_CREATED)
def create_checkout(trip_id: str, body: CheckoutIn, db: DbSession, user: ActiveUser, now: Now) -> dict[str, Any]:
    try:
        checkout = booking.create_checkout(
            db,
            user_id=user.id,
            trip_id=trip_id,
            stays=[booking.StayRequest(**s.model_dump()) for s in body.stays],
            now=now,
        )
    except booking.BookingError as exc:
        raise HTTPException(_STATUS[exc.code], detail={"code": exc.code, "detail": exc.detail}) from exc
    return _checkout_out(checkout)


@router.get("/me/checkouts/{checkout_id}", tags=["Bookings"])
def get_checkout(checkout_id: str, db: DbSession, user: ActiveUser) -> dict[str, Any]:
    checkout = db["checkouts"].find_one({"_id": checkout_id, "user_id": user.id})
    if checkout is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "checkout_not_found"})
    pay = db["payments"].find_one({"checkout_id": checkout_id}, {"_id": 1, "status": 1})
    bookings = list(db["bookings"].find({"checkout_id": checkout_id}, {"_id": 1, "status": 1, "stay_id": 1}))
    return {
        **_checkout_out(checkout),
        "payment": {"id": pay["_id"], "status": pay["status"]} if pay else None,
        "bookings": [{"id": b["_id"], "status": b["status"], "stay_id": b.get("stay_id")} for b in bookings],
    }
