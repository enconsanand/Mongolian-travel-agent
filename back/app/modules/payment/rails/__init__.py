"""Payment rails behind one ``PaymentRail`` protocol: ``qpay``, ``bonum``, ``sim``. Chosen by ``PAYMENT_RAIL``.

``sim`` is the QPay adapter pointed at our simulator, so demos and tests run the same adapter code as production.
"""

from functools import lru_cache

from app.modules.payment.rails.base import (
    ChargeHandle,
    ChargeState,
    ChargeStatus,
    InstrumentType,
    PaymentRail,
    RailError,
    RailId,
    WebhookHint,
)
from app.modules.payment.rails.qpay import QPayRail

__all__ = [
    "ChargeHandle",
    "ChargeState",
    "ChargeStatus",
    "InstrumentType",
    "PaymentRail",
    "QPayRail",
    "RailError",
    "RailId",
    "WebhookHint",
    "build_rail",
    "configured_rail",
]


def build_rail(rail_id: RailId, *, base_url: str, username: str, password: str, invoice_code: str) -> PaymentRail:
    if rail_id in ("qpay", "sim"):
        return QPayRail(
            rail_id=rail_id, base_url=base_url, username=username, password=password, invoice_code=invoice_code
        )
    raise NotImplementedError("Bonum rail is on the roadmap; use PAYMENT_RAIL=sim or qpay")


def configured_rail() -> PaymentRail:
    """The rail chosen by settings (one instance per process: it caches the provider token)."""
    return _configured()


@lru_cache
def _configured() -> PaymentRail:
    from app.core.config import settings

    return build_rail(
        settings.PAYMENT_RAIL,
        base_url=settings.QPAY_BASE_URL,
        username=settings.QPAY_USERNAME,
        password=settings.QPAY_PASSWORD,
        invoice_code=settings.QPAY_INVOICE_CODE,
    )
