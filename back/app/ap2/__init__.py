"""AP2 v0.2 mandates: build and verify Checkout / Payment Mandates (ES256), checkout hash, constraint checks.

Pure functions with no I/O, so every role (merchant, credential provider, payment agent) verifies independently.
Callers catch ``MandateError`` and store its ``code`` as the reject reason.
"""

from app.ap2.checkout import amount, mnt_to_minor, sign_checkout, verify_checkout
from app.ap2.errors import MandateError, RejectCode
from app.ap2.jws import generate_key, jwk_thumbprint, load_public_jwk, public_jwk, sha256_b64url
from app.ap2.mandates import (
    CHECKOUT_VCT,
    PAYMENT_OPEN_VCT,
    PAYMENT_VCT,
    Verified,
    check_within_open,
    checkout_mandate_claims,
    mandate_hash,
    open_payment_mandate_claims,
    payment_mandate_claims,
    sign_mandate,
    verify_checkout_mandate,
    verify_open_payment_mandate,
    verify_payment_mandate,
)

__all__ = [
    "CHECKOUT_VCT",
    "PAYMENT_OPEN_VCT",
    "PAYMENT_VCT",
    "MandateError",
    "RejectCode",
    "Verified",
    "amount",
    "check_within_open",
    "checkout_mandate_claims",
    "generate_key",
    "jwk_thumbprint",
    "load_public_jwk",
    "mandate_hash",
    "mnt_to_minor",
    "open_payment_mandate_claims",
    "payment_mandate_claims",
    "public_jwk",
    "sha256_b64url",
    "sign_checkout",
    "sign_mandate",
    "verify_checkout",
    "verify_checkout_mandate",
    "verify_open_payment_mandate",
    "verify_payment_mandate",
]
