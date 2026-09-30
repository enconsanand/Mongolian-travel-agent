"""The contract every payment rail meets, so the payment module never knows which rail it is talking to.

A rail only moves money and reports what the provider says. Deciding whether a payment is allowed (AP2 mandate
checks, amounts, idempotency) happens before a rail is called, in ``app.modules.payment``.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal, Protocol

RailId = Literal["qpay", "bonum", "sim"]
InstrumentType = Literal["qpay_qr", "card"]
ChargeState = Literal["pending", "paid", "failed", "cancelled"]


class RailError(Exception):
    """The provider refused the request or could not be reached. ``retryable`` says whether trying again may help."""

    def __init__(self, message: str, *, retryable: bool = False, status_code: int | None = None) -> None:
        super().__init__(message)
        self.retryable = retryable
        self.status_code = status_code


@dataclass(frozen=True)
class ChargeHandle:
    """What the user needs to pay: a QR, a short link, bank-app deeplinks. ``provider_ref`` is the invoice id."""

    provider: RailId
    provider_ref: str
    amount_mnt: int
    qr_text: str | None = None
    qr_image: str | None = None  # base64 PNG
    short_url: str | None = None
    deeplinks: list[dict[str, str]] = field(default_factory=list)


@dataclass(frozen=True)
class ChargeStatus:
    """The provider's answer when we ask (never a callback: those are only hints)."""

    state: ChargeState
    paid_amount_mnt: int
    provider_payment_id: str | None = None


@dataclass(frozen=True)
class WebhookHint:
    """What a callback claims. Used only to decide which charge to ``verify``; never trusted on its own."""

    provider_ref: str | None
    provider_payment_id: str | None


class PaymentRail(Protocol):
    id: RailId

    def supports(self, instrument: InstrumentType) -> bool: ...

    def create_charge(
        self, *, charge_id: str, amount_mnt: int, description: str, callback_url: str
    ) -> ChargeHandle: ...

    def verify(self, provider_ref: str) -> ChargeStatus: ...

    def cancel(self, provider_ref: str) -> None: ...

    def refund(self, provider_payment_id: str) -> None: ...

    def parse_webhook(self, query: Mapping[str, str], body: bytes) -> WebhookHint: ...

    def issue_receipt(self, provider_payment_id: str) -> str | None: ...
