"""Payment flow: verify the AP2 Payment Mandate, open a charge on the rail, and settle it when the rail says paid.

Nothing here trusts the caller or the rail's callback:
- ``start_payment`` verifies the user-signed Payment Mandate against the merchant-signed checkout before any rail
  call, and is idempotent per checkout (one payment per checkout, retries reuse it).
- ``handle_callback`` authenticates the callback URL with an HMAC token, then asks the rail itself (``verify``);
  it moves ``awaiting_payment -> paid`` with a compare-and-set, so three copies of a callback settle once.
Settling writes the payment, the checkout and a ``payment.paid`` outbox event in one transaction.
"""

import contextlib
import hashlib
import hmac
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from pymongo.client_session import ClientSession
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from app import ap2
from app.core.config import settings
from app.core.keys import merchant_public_jwk
from app.db.outbox import emit, iso
from app.db.transactions import run_in_transaction
from app.modules.payment.rails import InstrumentType, PaymentRail, RailError
from app.schemas.commerce import CheckoutDoc, MandateDoc, PaymentEventDoc, UserKeyDoc
from app.schemas.travel import AuditLogDoc, PaymentDoc

logger = logging.getLogger(__name__)

PaymentErrorCode = Literal[
    "checkout_not_found",
    "checkout_not_open",
    "checkout_expired",
    "key_not_found",
    "mandate_rejected",
    "mandate_already_used",
    "rail_unavailable",
    "rail_refused",
]
CallbackOutcome = Literal["paid", "already_settled", "pending", "underpaid", "failed"]


class PaymentError(Exception):
    def __init__(self, code: PaymentErrorCode, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code: PaymentErrorCode = code
        self.detail = detail


@dataclass(frozen=True)
class StartedPayment:
    payment: dict[str, Any]
    created: bool  # False when an earlier call already started it


# ----------------------------------------------------------------------------- helpers


def _audit(
    db: Database,
    *,
    now: datetime,
    actor: str,
    action: str,
    entity: str,
    entity_id: str,
    user_id: str | None,
    trip_id: str | None,
    amount_mnt: int | None = None,
    details: dict[str, Any] | None = None,
    session: ClientSession | None = None,
) -> None:
    doc = AuditLogDoc.model_validate(
        {
            "_id": f"audit_{uuid4().hex}",
            "ts": iso(now),
            "actor": actor,
            "user_id": user_id,
            "trip_id": trip_id,
            "action": action,
            "entity": entity,
            "entity_id": entity_id,
            "amount_mnt": amount_mnt,
            "details": details or {},
        }
    )
    db[AuditLogDoc.collection].insert_one(doc.model_dump(by_alias=True, exclude={"is_mock"}), session=session)


def webhook_token(payment_id: str) -> str:
    """Per-payment secret in the callback URL; QPay callbacks are unsigned, so this is what authenticates them."""
    key = hashlib.sha256(b"webhook:" + settings.JWT_SECRET.encode()).digest()
    return hmac.new(key, payment_id.encode(), hashlib.sha256).hexdigest()[:32]


def callback_url(provider: str, payment_id: str) -> str:
    base = settings.PUBLIC_BASE_URL.rstrip("/")
    return f"{base}{settings.API_V1_STR}/webhooks/{provider}/{payment_id}/{webhook_token(payment_id)}"


# ----------------------------------------------------------------------------- user keys


def register_user_key(db: Database, *, user_id: str, jwk: dict[str, Any], now: datetime) -> str:
    """Store a browser-made public key; returns its id (thumbprint). Registering the same key again is a no-op."""
    public = ap2.public_jwk(ap2.load_public_jwk(jwk))  # refuses private or non-P-256 keys, drops extra members
    kid = ap2.jwk_thumbprint(public)
    existing = db[UserKeyDoc.collection].find_one({"_id": kid})
    if existing and existing["user_id"] != user_id:
        raise PaymentError("key_not_found", "this key belongs to another user")
    if not existing:
        doc = UserKeyDoc.model_validate({"_id": kid, "user_id": user_id, "jwk": public, "created_at": iso(now)})
        db[UserKeyDoc.collection].insert_one(doc.model_dump(by_alias=True, exclude={"is_mock"}))
    return kid


def user_jwk(db: Database, *, user_id: str, kid: str) -> dict[str, Any]:
    doc = db[UserKeyDoc.collection].find_one({"_id": kid, "user_id": user_id, "revoked_at": None})
    if doc is None:
        raise PaymentError("key_not_found", "unknown or revoked key")
    return doc["jwk"]


# ----------------------------------------------------------------------------- start


def _record_rejected_mandate(
    db: Database, *, sd_jwt: str, checkout: dict, user_id: str, kid: str, code: str, now: datetime
) -> None:
    """Keep rejected mandates as evidence (the replay index only covers used mandates, so this blocks nothing)."""
    doc = {
        "_id": f"mdt_{uuid4().hex}",
        "vct": ap2.PAYMENT_VCT,
        "kind": "payment",
        "form": "closed",
        "trip_id": checkout["trip_id"],
        "user_id": user_id,
        "checkout_id": checkout["_id"],
        "transaction_id": checkout["checkout_hash"],
        "sd_jwt": sd_jwt,
        "hash": ap2.mandate_hash(sd_jwt) if isinstance(sd_jwt, str) else f"invalid:{uuid4().hex}",
        "signer": "user",
        "key_id": kid,
        "status": "rejected",
        "reject_reason": code,
        "received_at": iso(now),
    }
    with contextlib.suppress(DuplicateKeyError):  # the same bad mandate sent again
        db[MandateDoc.collection].insert_one(
            MandateDoc.model_validate(doc).model_dump(by_alias=True, exclude={"is_mock"})
        )


def start_payment(
    db: Database,
    rail: PaymentRail,
    *,
    user_id: str,
    checkout_id: str,
    payment_mandate: str,
    kid: str,
    instrument: InstrumentType,
    now: datetime,
) -> StartedPayment:
    checkout = db[CheckoutDoc.collection].find_one({"_id": checkout_id, "user_id": user_id})
    if checkout is None:
        raise PaymentError("checkout_not_found")

    payment_id = f"pay_{checkout_id}"
    existing = db[PaymentDoc.collection].find_one({"_id": payment_id})
    if existing and existing["status"] in ("awaiting_payment", "paid"):
        return StartedPayment(payment=existing, created=False)

    if checkout["status"] != "open":
        raise PaymentError("checkout_not_open", checkout["status"])
    if iso(now) > checkout["expires_at"]:
        raise PaymentError("checkout_expired")

    signer = user_jwk(db, user_id=user_id, kid=kid)
    try:
        verified = ap2.verify_payment_mandate(
            payment_mandate,
            signer_jwk=signer,
            checkout_jwt=checkout["checkout_jwt"],
            merchant_jwk=merchant_public_jwk(),
            payee_id=settings.MERCHANT_ID,
            now=int(now.timestamp()),
        )
    except ap2.MandateError as exc:
        _record_rejected_mandate(
            db, sd_jwt=payment_mandate, checkout=checkout, user_id=user_id, kid=kid, code=exc.code, now=now
        )
        _audit(
            db,
            now=now,
            actor="system",
            action="payment_mandate_rejected",
            entity="checkout",
            entity_id=checkout_id,
            user_id=user_id,
            trip_id=checkout["trip_id"],
            details={"reason": exc.code},
        )
        raise PaymentError("mandate_rejected", exc.code) from exc

    if existing is None:
        existing = _create_payment_record(db, checkout, verified, user_id, kid, payment_mandate, instrument, now)

    return StartedPayment(payment=_open_charge(db, rail, existing, checkout, now), created=True)


def _create_payment_record(
    db: Database,
    checkout: dict,
    verified: ap2.Verified,
    user_id: str,
    kid: str,
    sd_jwt: str,
    instrument: InstrumentType,
    now: datetime,
) -> dict[str, Any]:
    payment_id = f"pay_{checkout['_id']}"
    mandate_id = f"mdt_{verified.hash[:32]}"
    mandate = MandateDoc.model_validate(
        {
            "_id": mandate_id,
            "vct": ap2.PAYMENT_VCT,
            "kind": "payment",
            "form": "closed",
            "trip_id": checkout["trip_id"],
            "user_id": user_id,
            "checkout_id": checkout["_id"],
            "transaction_id": checkout["checkout_hash"],
            "sd_jwt": sd_jwt,
            "hash": verified.hash,
            "signer": "user",
            "key_id": kid,
            "status": "verified",
            "received_at": iso(now),
            "verified_at": iso(now),
        }
    ).model_dump(by_alias=True, exclude={"is_mock"})
    payment = PaymentDoc.model_validate(
        {
            "_id": payment_id,
            "user_id": user_id,
            "trip_id": checkout["trip_id"],
            "quote_id": checkout.get("quote_id"),
            "booking_ids": [],
            "amount_mnt": checkout["total_mnt"],
            "method": {"type": "qpay" if instrument == "qpay_qr" else "card"},
            "provider": settings.PAYMENT_RAIL,
            "provider_ref": "",
            "status": "approved_by_user",
            "status_history": [{"status": "approved_by_user", "at": iso(now), "actor": "user"}],
            "consent": {"approved_by_user": True, "max_amount_mnt": checkout["total_mnt"], "approved_at": iso(now)},
            "idempotency_key": f"{checkout['_id']}:payment",
            "is_sandbox": settings.PAYMENT_RAIL == "sim",
            "checkout_id": checkout["_id"],
            "payment_mandate_id": mandate_id,
            "transaction_id": checkout["checkout_hash"],
        }
    ).model_dump(by_alias=True, exclude={"is_mock"})

    def work(session: ClientSession | None) -> None:
        db[MandateDoc.collection].insert_one(mandate, session=session)
        db[PaymentDoc.collection].insert_one(payment, session=session)
        _audit(
            db,
            now=now,
            actor="user",
            action="payment_approved",
            entity="payment",
            entity_id=payment_id,
            user_id=user_id,
            trip_id=checkout["trip_id"],
            amount_mnt=checkout["total_mnt"],
            details={"mandate_id": mandate_id},
            session=session,
        )

    try:
        run_in_transaction(db, work)
    except DuplicateKeyError as exc:
        # A concurrent call won (same payment id), or another mandate for this checkout is already recorded
        winner = db[PaymentDoc.collection].find_one({"_id": payment_id})
        if winner is None:
            raise PaymentError("mandate_already_used") from exc
        return winner
    return payment


def _open_charge(db: Database, rail: PaymentRail, payment: dict, checkout: dict, now: datetime) -> dict[str, Any]:
    """approved_by_user -> awaiting_payment. Safe to call again after a rail failure."""
    try:
        handle = rail.create_charge(
            charge_id=payment["_id"],
            amount_mnt=payment["amount_mnt"],
            description=f"Mongolian Travel Agent {checkout['trip_id']}",
            callback_url=callback_url(rail.id, payment["_id"]),
        )
    except RailError as exc:
        logger.warning("Rail %s refused charge %s: %s", rail.id, payment["_id"], exc)
        raise PaymentError("rail_unavailable" if exc.retryable else "rail_refused", str(exc)) from exc

    charge = {
        "qr_text": handle.qr_text,
        "qr_image": handle.qr_image,
        "short_url": handle.short_url,
        "deeplinks": handle.deeplinks,
    }
    db[PaymentDoc.collection].update_one(
        {"_id": payment["_id"], "status": "approved_by_user"},
        {
            "$set": {"provider_ref": handle.provider_ref, "status": "awaiting_payment", "charge": charge},
            "$push": {"status_history": {"status": "awaiting_payment", "at": iso(now), "actor": "system"}},
        },
    )
    db[MandateDoc.collection].update_one(
        {"_id": payment["payment_mandate_id"]}, {"$set": {"status": "used", "used_at": iso(now)}}
    )
    return db[PaymentDoc.collection].find_one({"_id": payment["_id"]}) or payment


# ----------------------------------------------------------------------------- cancel


def cancel_unpaid_charge(db: Database, rail: PaymentRail, *, checkout_id: str, now: datetime) -> bool:
    """Close the rail invoice of an unpaid payment so it can no longer be paid; ``awaiting_payment -> expired``.

    Returns False when the checkout may still be paid (the rail refused the cancel, e.g. it is already paid, or the
    rail is down): the caller must not release inventory yet. True when nothing can be paid any more.
    """
    payment = db[PaymentDoc.collection].find_one({"checkout_id": checkout_id})
    if payment is None or payment["status"] in ("approved_by_user", "expired", "failed", "cancelled"):
        if payment is not None and payment["status"] == "approved_by_user":
            db[PaymentDoc.collection].update_one(
                {"_id": payment["_id"], "status": "approved_by_user"},
                {
                    "$set": {"status": "expired"},
                    "$push": {"status_history": {"status": "expired", "at": iso(now), "actor": "system"}},
                },
            )
        return True
    if payment["status"] != "awaiting_payment":
        return False  # paid (or refunded): the booking side settles it
    try:
        rail.cancel(payment["provider_ref"])
    except RailError:
        return False
    result = db[PaymentDoc.collection].update_one(
        {"_id": payment["_id"], "status": "awaiting_payment"},
        {
            "$set": {"status": "expired"},
            "$push": {"status_history": {"status": "expired", "at": iso(now), "actor": "system"}},
        },
    )
    return result.modified_count == 1


# ----------------------------------------------------------------------------- callback


def _record_event(
    db: Database,
    *,
    provider: str,
    provider_ref: str,
    kind: str,
    payment_id: str,
    verified: bool,
    raw: dict,
    now: datetime,
) -> None:
    event = PaymentEventDoc.model_validate(
        {
            "_id": f"pe_{provider}_{kind}_{provider_ref}",
            "provider": provider,
            "provider_ref": provider_ref,
            "kind": kind,
            "payment_id": payment_id,
            "verified": verified,
            "raw": raw,
            "received_at": iso(now),
        }
    ).model_dump(by_alias=True, exclude={"is_mock"})
    # One row per (provider, ref, kind): repeated callbacks keep the first, checks keep the latest answer
    if kind == "callback":
        with contextlib.suppress(DuplicateKeyError):
            db[PaymentEventDoc.collection].insert_one(event)
    else:
        db[PaymentEventDoc.collection].replace_one({"_id": event["_id"]}, event, upsert=True)


def handle_callback(
    db: Database,
    rail: PaymentRail,
    *,
    payment_id: str,
    token: str,
    query: Mapping[str, str],
    body: bytes,
    now: datetime,
) -> CallbackOutcome:
    """Raises ``LookupError`` for a bad token or unknown payment (the API answers 404 either way)."""
    if not hmac.compare_digest(token, webhook_token(payment_id)):
        raise LookupError("bad token")
    payment = db[PaymentDoc.collection].find_one({"_id": payment_id})
    if payment is None or not payment.get("provider_ref"):
        raise LookupError("unknown payment")

    hint = rail.parse_webhook(query, body)
    _record_event(
        db,
        provider=rail.id,
        provider_ref=payment["provider_ref"],
        kind="callback",
        payment_id=payment_id,
        verified=False,
        raw={"query": dict(query), "hint_payment_id": hint.provider_payment_id},
        now=now,
    )
    if payment["status"] != "awaiting_payment":
        return "already_settled"

    status = rail.verify(payment["provider_ref"])  # RailError propagates: the API answers 503 so QPay may retry
    _record_event(
        db,
        provider=rail.id,
        provider_ref=payment["provider_ref"],
        kind="check",
        payment_id=payment_id,
        verified=True,
        raw={"state": status.state, "paid_amount_mnt": status.paid_amount_mnt},
        now=now,
    )

    if status.state == "paid" and status.paid_amount_mnt >= payment["amount_mnt"]:
        return _settle(db, payment, status.provider_payment_id, "paid", now)
    if status.state == "paid":
        _audit(
            db,
            now=now,
            actor="system",
            action="payment_underpaid",
            entity="payment",
            entity_id=payment_id,
            user_id=payment["user_id"],
            trip_id=payment["trip_id"],
            amount_mnt=status.paid_amount_mnt,
            details={"expected_mnt": payment["amount_mnt"]},
        )
        return "underpaid"
    if status.state == "failed":
        return _settle(db, payment, None, "failed", now)
    return "pending"


def _settle(
    db: Database, payment: dict, provider_payment_id: str | None, outcome: Literal["paid", "failed"], now: datetime
) -> CallbackOutcome:
    def work(session: ClientSession | None) -> bool:
        result = db[PaymentDoc.collection].update_one(
            {"_id": payment["_id"], "status": "awaiting_payment"},
            {
                "$set": {"status": outcome, "charge.provider_payment_id": provider_payment_id},
                "$push": {"status_history": {"status": outcome, "at": iso(now), "actor": "system"}},
            },
            session=session,
        )
        if result.modified_count == 0:
            return False  # another callback settled it first
        if outcome == "paid":
            db[CheckoutDoc.collection].update_one(
                {"_id": payment["checkout_id"]}, {"$set": {"status": "paid"}}, session=session
            )
        emit(
            db,
            type=f"payment.{outcome}",
            aggregate_id=payment["_id"],
            payload={
                "payment_id": payment["_id"],
                "checkout_id": payment["checkout_id"],
                "trip_id": payment["trip_id"],
                "amount_mnt": payment["amount_mnt"],
            },
            now=now,
            session=session,
        )
        _audit(
            db,
            now=now,
            actor="system",
            action=f"payment_{outcome}",
            entity="payment",
            entity_id=payment["_id"],
            user_id=payment["user_id"],
            trip_id=payment["trip_id"],
            amount_mnt=payment["amount_mnt"],
            details={"provider_payment_id": provider_payment_id},
            session=session,
        )
        return True

    return outcome if run_in_transaction(db, work) else "already_settled"
