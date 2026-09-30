"""Payment: AP2 Credential Provider checks, then the payment rail (QPay, Bonum or the simulator).

Deterministic, no LLM. No rail is called before the Payment Mandate verifies.
"""

from app.modules.payment.service import (
    CallbackOutcome,
    PaymentError,
    StartedPayment,
    callback_url,
    handle_callback,
    register_user_key,
    start_payment,
    user_jwk,
    webhook_token,
)

__all__ = [
    "CallbackOutcome",
    "PaymentError",
    "StartedPayment",
    "callback_url",
    "handle_callback",
    "register_user_key",
    "start_payment",
    "user_jwk",
    "webhook_token",
]
