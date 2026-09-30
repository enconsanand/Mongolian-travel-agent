"""Document schemas for the commerce collections: checkouts, AP2 mandates, holds, payment events, outbox.

Unlike ``app.schemas.travel`` these collections have no mock files: only the running app writes them. They
follow the same conventions (readable string ``_id``, ISO timestamps, integer MNT) and get the same strict
``$jsonSchema`` validators, created by the seeder.

AP2 terms follow the Agent Payments Protocol v0.2 (https://ap2-protocol.org/ap2/specification/):
a Checkout Mandate proves the user approved this exact checkout; a Payment Mandate proves they approved paying
for it. Each is ``open`` (constraints, for autonomous mode) or ``closed`` (bound to one checkout by its hash).
"""

from typing import Any, ClassVar, Literal

from pydantic import Field, model_validator

from app.schemas.travel import Doc, QuoteLine, UnitType

PaymentProvider = Literal["qpay", "bonum", "sim"]


# ----------------------------------------------------------------------------- checkout (AP2 Merchant)


class CheckoutLine(QuoteLine):
    """A priced line of the checkout; stay lines also say which night and unit they hold."""

    date: str | None = None
    unit_type: UnitType | None = None


class CheckoutDoc(Doc):
    """The exact basket the user is asked to approve, signed by the platform as merchant (``checkout_jwt``).

    ``checkout_hash`` (base64url SHA-256 of ``checkout_jwt``) is what both mandates bind to, and is the AP2
    ``transaction_id``. Lifecycle: open -> paid, or open -> expired / cancelled.
    """

    collection: ClassVar[str] = "checkouts"

    trip_id: str
    user_id: str
    quote_id: str | None = None
    lines: list[CheckoutLine] = Field(min_length=1)
    total_mnt: int = Field(ge=0)
    currency: Literal["MNT"] = "MNT"
    hold_ids: list[str]
    checkout_jwt: str
    checkout_hash: str
    status: Literal["open", "paid", "expired", "cancelled"]
    expires_at: str
    created_at: str


# ----------------------------------------------------------------------------- AP2 mandates

MandateVct = Literal["mandate.checkout.1", "mandate.checkout.open.1", "mandate.payment.1", "mandate.payment.open.1"]
_VCT_SHAPE: dict[str, tuple[str, str]] = {
    "mandate.checkout.1": ("checkout", "closed"),
    "mandate.checkout.open.1": ("checkout", "open"),
    "mandate.payment.1": ("payment", "closed"),
    "mandate.payment.open.1": ("payment", "open"),
}


class MandateDoc(Doc):
    """A mandate as received (``sd_jwt``, stored verbatim for dispute evidence) and what we decided about it.

    ``hash`` is unique, and a closed mandate's ``transaction_id`` can be ``used`` once, so a replayed mandate
    is rejected. Direct mode: the user signs closed mandates. Autonomous mode: the user signs an open mandate
    and the agent signs closed ones with the key bound in the open mandate's ``cnf``.
    """

    collection: ClassVar[str] = "mandates"

    vct: MandateVct
    kind: Literal["checkout", "payment"]
    form: Literal["open", "closed"]
    trip_id: str
    user_id: str
    checkout_id: str | None = None
    transaction_id: str | None = None  # closed mandates: the checkout_hash they bind to
    open_mandate_id: str | None = None  # autonomous mode: the user-signed open mandate this one relies on
    sd_jwt: str
    hash: str
    signer: Literal["user", "agent"]
    key_id: str
    status: Literal["received", "verified", "rejected", "used"]
    reject_reason: str | None = None
    received_at: str
    verified_at: str | None = None
    used_at: str | None = None

    @model_validator(mode="after")
    def _vct_matches_kind_and_form(self) -> "MandateDoc":
        if _VCT_SHAPE[self.vct] != (self.kind, self.form):
            raise ValueError(f"vct `{self.vct}` does not match kind `{self.kind}` / form `{self.form}`")
        if self.form == "closed" and not self.transaction_id:
            raise ValueError("a closed mandate must carry the transaction_id (checkout hash) it binds to")
        return self


# ----------------------------------------------------------------------------- inventory holds


class HoldDoc(Doc):
    """Units taken out of ``stay_availability.available`` for a checkout until it is paid or the hold expires.

    Expiry is done by a sweeper that gives the units back in the same transaction that marks the hold
    ``expired``; a TTL index would delete the hold without returning the units.
    """

    collection: ClassVar[str] = "holds"

    trip_id: str
    checkout_id: str | None = None
    stay_id: str
    unit_type: UnitType
    date: str
    qty: int = Field(ge=1)
    status: Literal["held", "confirmed", "released", "expired"]
    expires_at: str
    created_at: str


# ----------------------------------------------------------------------------- payment rail events


class PaymentEventDoc(Doc):
    """What a payment rail told us: a callback (a hint only) or the result of asking it (``verified``).

    Unique on (provider, provider_ref, kind), so a callback QPay sends three times is stored once.
    """

    collection: ClassVar[str] = "payment_events"

    provider: PaymentProvider
    provider_ref: str
    kind: Literal["callback", "check", "refund"]
    payment_id: str | None = None
    verified: bool
    raw: dict[str, Any]
    received_at: str


# ----------------------------------------------------------------------------- user signing keys


class UserKeyDoc(Doc):
    """A public key a user's browser created (WebCrypto P-256, private part never leaves the device).

    Direct-mode mandates are verified against it. ``_id`` is the RFC 7638 thumbprint, so the same key registers
    once.
    """

    collection: ClassVar[str] = "user_keys"

    user_id: str
    jwk: dict[str, str]
    created_at: str
    revoked_at: str | None = None


# ----------------------------------------------------------------------------- transactional outbox


class OutboxEventDoc(Doc):
    """An event written in the same transaction as the change it announces. ``app.db.outbox.dispatch`` claims
    it (sets ``dispatched_at``) and runs the handler; a failing handler puts it back with ``last_error``."""

    collection: ClassVar[str] = "outbox"

    type: Literal[
        "payment.paid",
        "payment.failed",
        "booking.confirmed",
        "booking.cancelled",
        "hold.expired",
        "checkout.expired",
    ]
    aggregate_id: str
    payload: dict[str, Any]
    created_at: str
    dispatched_at: str | None = None
    attempts: int = Field(default=0, ge=0)
    last_error: str | None = None


# Commerce collections, keyed by collection name. No mock files; the seeder creates them with validators.
COMMERCE_MODELS: dict[str, type[Doc]] = {
    m.collection: m for m in (CheckoutDoc, MandateDoc, HoldDoc, PaymentEventDoc, OutboxEventDoc, UserKeyDoc)
}
