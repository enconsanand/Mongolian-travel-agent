"""The merchant-signed checkout (``checkout_jwt``) that both AP2 mandates bind to.

The platform is merchant of record, so ``booking`` signs one checkout per trip with the merchant key. Its claims
are ours (AP2 leaves the checkout payload to the commerce protocol); what AP2 fixes is that mandates carry
``checkout_hash = base64url(SHA-256(checkout_jwt))``.
"""

from typing import Any

from cryptography.hazmat.primitives.asymmetric import ec

from app.ap2.errors import MandateError
from app.ap2.jws import Json, sha256_b64url, sign, verify

CHECKOUT_TYP = "JWT"
CURRENCY = "MNT"
SKEW_SECONDS = 60


def mnt_to_minor(mnt: int) -> int:
    """AP2 amounts are in minor units; MNT has 2 decimals (ISO 4217), so 180 000₮ is 18 000 000."""
    return mnt * 100


def amount(mnt: int) -> Json:
    return {"amount": mnt_to_minor(mnt), "currency": CURRENCY}


def checkout_claims(
    *,
    merchant_id: str,
    checkout_id: str,
    trip_id: str,
    lines: list[dict[str, Any]],
    total_mnt: int,
    iat: int,
    exp: int,
) -> Json:
    if not lines:
        raise ValueError("a checkout needs at least one line")
    if sum(line["total_mnt"] for line in lines) != total_mnt:
        raise ValueError("checkout total does not equal the sum of its lines")
    return {
        "iss": merchant_id,
        "checkout_id": checkout_id,
        "trip_id": trip_id,
        "lines": lines,
        "total": amount(total_mnt),
        "iat": iat,
        "exp": exp,
    }


def sign_checkout(claims: Json, merchant_key: ec.EllipticCurvePrivateKey, *, kid: str) -> tuple[str, str]:
    """Return (checkout_jwt, checkout_hash)."""
    token = sign(claims, merchant_key, kid=kid, typ=CHECKOUT_TYP)
    return token, sha256_b64url(token)


def check_time(claims: Json, now: int) -> None:
    exp, iat = claims.get("exp"), claims.get("iat")
    if not isinstance(exp, int) or not isinstance(iat, int):
        raise MandateError("malformed", "iat and exp must be integer epoch seconds")
    if now > exp + SKEW_SECONDS:
        raise MandateError("expired", f"expired at {exp}")
    if iat > now + SKEW_SECONDS:
        raise MandateError("not_yet_valid", f"issued in the future ({iat})")


def verify_checkout(checkout_jwt: str, merchant_jwk: Json, *, now: int) -> Json:
    """Merchant signature and validity window of a checkout JWT; returns its claims."""
    _, claims = verify(checkout_jwt, merchant_jwk)
    check_time(claims, now)
    total = claims.get("total")
    if not isinstance(total, dict) or total.get("currency") != CURRENCY or not isinstance(total.get("amount"), int):
        raise MandateError("malformed", "checkout total must be {amount: int, currency: MNT}")
    return claims
