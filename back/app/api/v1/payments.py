"""Payments API: register a browser signing key, pay a checkout with an AP2 Payment Mandate, rail callbacks.

The router holds no payment logic; it maps ``app.modules.payment`` results and errors to HTTP.
"""

from datetime import UTC, datetime
from functools import lru_cache
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from app import ap2
from app.api.v1.deps import ActiveUser, DbSession
from app.core.config import settings
from app.modules import payment
from app.modules.payment.rails import InstrumentType, PaymentRail, RailError, build_rail

router = APIRouter()


@lru_cache
def _configured_rail() -> PaymentRail:
    return build_rail(
        settings.PAYMENT_RAIL,
        base_url=settings.QPAY_BASE_URL,
        username=settings.QPAY_USERNAME,
        password=settings.QPAY_PASSWORD,
        invoice_code=settings.QPAY_INVOICE_CODE,
    )


def get_rail() -> PaymentRail:
    return _configured_rail()


Rail = Annotated[PaymentRail, Depends(get_rail)]

_STATUS = {
    "checkout_not_found": status.HTTP_404_NOT_FOUND,
    "key_not_found": status.HTTP_404_NOT_FOUND,
    "checkout_not_open": status.HTTP_409_CONFLICT,
    "checkout_expired": status.HTTP_409_CONFLICT,
    "mandate_already_used": status.HTTP_409_CONFLICT,
    "mandate_rejected": status.HTTP_422_UNPROCESSABLE_CONTENT,
    "rail_refused": status.HTTP_502_BAD_GATEWAY,
    "rail_unavailable": status.HTTP_503_SERVICE_UNAVAILABLE,
}


def _http(exc: payment.PaymentError) -> HTTPException:
    return HTTPException(_STATUS[exc.code], detail={"code": exc.code, "detail": exc.detail})


def get_now() -> datetime:
    """The request time; a dependency so tests can pin the clock mandates are checked against."""
    return datetime.now(UTC)


Now = Annotated[datetime, Depends(get_now)]


# ----------------------------------------------------------------------------- keys


class KeyIn(BaseModel):
    jwk: dict[str, Any] = Field(description="Public EC P-256 JWK made with WebCrypto (non-extractable private key)")


@router.post("/me/keys", tags=["Payments"], status_code=status.HTTP_201_CREATED)
def register_key(body: KeyIn, db: DbSession, user: ActiveUser, now: Now) -> dict[str, str]:
    try:
        return {"kid": payment.register_user_key(db, user_id=user.id, jwk=body.jwk, now=now)}
    except ap2.MandateError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail={"code": exc.code}) from exc
    except payment.PaymentError as exc:
        raise _http(exc) from exc


# ----------------------------------------------------------------------------- pay


class PayIn(BaseModel):
    payment_mandate: str = Field(description="Closed AP2 Payment Mandate (SD-JWT) signed in the browser")
    kid: str = Field(description="Id of the registered key that signed it")
    instrument: InstrumentType = "qpay_qr"


def _public(p: dict[str, Any]) -> dict[str, Any]:
    charge = p.get("charge") or {}
    return {
        "id": p["_id"],
        "status": p["status"],
        "amount_mnt": p["amount_mnt"],
        "checkout_id": p.get("checkout_id"),
        "qr_text": charge.get("qr_text"),
        "qr_image": charge.get("qr_image"),
        "short_url": charge.get("short_url"),
        "deeplinks": charge.get("deeplinks", []),
    }


@router.post("/me/checkouts/{checkout_id}/pay", tags=["Payments"])
def pay_checkout(
    checkout_id: str, body: PayIn, db: DbSession, user: ActiveUser, rail: Rail, now: Now
) -> dict[str, Any]:
    try:
        started = payment.start_payment(
            db,
            rail,
            user_id=user.id,
            checkout_id=checkout_id,
            payment_mandate=body.payment_mandate,
            kid=body.kid,
            instrument=body.instrument,
            now=now,
        )
    except payment.PaymentError as exc:
        raise _http(exc) from exc
    return _public(started.payment)


# ----------------------------------------------------------------------------- rail callbacks


@router.api_route(
    "/webhooks/{provider}/{payment_id}/{token}",
    methods=["GET", "POST"],
    tags=["Payments"],
    response_class=PlainTextResponse,
    include_in_schema=False,
)
async def rail_callback(
    provider: str, payment_id: str, token: str, request: Request, db: DbSession, rail: Rail, now: Now
) -> PlainTextResponse:
    if provider != rail.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    body = await request.body()
    try:
        # Sync pymongo and httpx: run in the threadpool so the event loop stays free
        await run_in_threadpool(
            payment.handle_callback,
            db,
            rail,
            payment_id=payment_id,
            token=token,
            query=dict(request.query_params),
            body=body,
            now=now,
        )
    except LookupError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND) from exc
    except RailError as exc:
        # Could not ask the rail; a non-200 lets the provider retry the callback
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE) from exc
    return PlainTextResponse("SUCCESS")
