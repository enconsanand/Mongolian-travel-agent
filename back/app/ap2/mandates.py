"""AP2 v0.2 Checkout and Payment Mandates: build, sign, verify, and check a closed mandate against an open one.

Wire format (our reading of https://ap2-protocol.org/ap2/specification/ ; re-check before interop with third
parties): each mandate is an SD-JWT with no disclosures, i.e. an ES256 JWS followed by ``~``. Claim names used:

- closed Checkout Mandate ``mandate.checkout.1``: ``checkout_jwt``, ``checkout_hash``
- closed Payment Mandate ``mandate.payment.1``: ``transaction_id`` (= checkout hash), ``payee``,
  ``payment_amount`` (minor units), ``payment_instrument``
- open Payment Mandate ``mandate.payment.open.1``: ``constraints`` keyed ``payment.amount_range``,
  ``payment.allowed_payees``, ``payment.execution_date``; ``cnf.jwk`` = the agent key allowed to sign closed ones

Direct mode (human present, the default here): the user signs the closed mandates on the trusted surface.
Autonomous mode: the user signs an open mandate; the agent signs closed ones, and verifiers need both.
Every function is pure: keys and ``now`` come in as arguments, so each role can verify on its own.
"""

from dataclasses import dataclass
from typing import Any

from cryptography.hazmat.primitives.asymmetric import ec

from app.ap2.checkout import amount, check_time, verify_checkout
from app.ap2.errors import MandateError
from app.ap2.jws import Json, jwk_thumbprint, sha256_b64url, sign, verify

CHECKOUT_VCT = "mandate.checkout.1"
CHECKOUT_OPEN_VCT = "mandate.checkout.open.1"
PAYMENT_VCT = "mandate.payment.1"
PAYMENT_OPEN_VCT = "mandate.payment.open.1"
SD_JWT_TYP = "dc+sd-jwt"


@dataclass(frozen=True)
class Verified:
    """A mandate that passed verification: its claims, the hash we store it under, and the signing key id."""

    claims: Json
    hash: str
    kid: str | None


def mandate_hash(sd_jwt: str) -> str:
    """Unique id of a mandate as received (``mandates.hash``): replaying the same mandate hits the unique index."""
    return sha256_b64url(sd_jwt)


# ----------------------------------------------------------------------------- build


def checkout_mandate_claims(checkout_jwt: str, *, iat: int, exp: int) -> Json:
    return {
        "vct": CHECKOUT_VCT,
        "checkout_jwt": checkout_jwt,
        "checkout_hash": sha256_b64url(checkout_jwt),
        "iat": iat,
        "exp": exp,
    }


def payment_mandate_claims(
    *,
    checkout_jwt: str,
    payee: Json,
    amount_mnt: int,
    instrument: Json,
    iat: int,
    exp: int,
    execution_date: str | None = None,
) -> Json:
    claims: Json = {
        "vct": PAYMENT_VCT,
        "transaction_id": sha256_b64url(checkout_jwt),
        "payee": payee,
        "payment_amount": amount(amount_mnt),
        "payment_instrument": instrument,
        "iat": iat,
        "exp": exp,
    }
    if execution_date:
        claims["execution_date"] = execution_date
    return claims


def open_payment_mandate_claims(
    *,
    max_mnt: int,
    agent_jwk: Json,
    iat: int,
    exp: int,
    allowed_payees: list[str] | None = None,
    execution_window: tuple[str, str] | None = None,
) -> Json:
    """What the user pre-approves for autonomous mode: an amount cap, payees and dates, and the agent key."""
    constraints: dict[str, Any] = {"payment.amount_range": {"max": amount(max_mnt)}}
    if allowed_payees is not None:
        constraints["payment.allowed_payees"] = allowed_payees
    if execution_window is not None:
        constraints["payment.execution_date"] = {"not_before": execution_window[0], "not_after": execution_window[1]}
    public = {k: agent_jwk[k] for k in ("kty", "crv", "x", "y")}
    return {"vct": PAYMENT_OPEN_VCT, "constraints": constraints, "cnf": {"jwk": public}, "iat": iat, "exp": exp}


def sign_mandate(claims: Json, key: ec.EllipticCurvePrivateKey, *, kid: str) -> str:
    """Server-side signing (tests, and the agent key in autonomous mode). Users sign in the browser."""
    return sign(claims, key, kid=kid, typ=SD_JWT_TYP) + "~"


# ----------------------------------------------------------------------------- verify


def _issuer_jws(sd_jwt: str) -> str:
    if not isinstance(sd_jwt, str) or not sd_jwt.endswith("~"):
        raise MandateError("malformed", "an SD-JWT ends with '~'")
    jws, *disclosures = sd_jwt[:-1].split("~")
    if disclosures:
        raise MandateError("malformed", "selective disclosures are not supported yet")
    return jws


def _verify_mandate(sd_jwt: str, signer_jwk: Json, vct: str, now: int) -> Verified:
    header, claims = verify(_issuer_jws(sd_jwt), signer_jwk)
    if claims.get("vct") != vct:
        raise MandateError("wrong_vct", f"expected {vct}, got {claims.get('vct')!r}")
    check_time(claims, now)
    return Verified(claims=claims, hash=mandate_hash(sd_jwt), kid=header.get("kid"))


def verify_checkout_mandate(sd_jwt: str, *, signer_jwk: Json, merchant_jwk: Json, now: int) -> Verified:
    """Merchant's check: the signer approved exactly the checkout the merchant signed."""
    mandate = _verify_mandate(sd_jwt, signer_jwk, CHECKOUT_VCT, now)
    checkout_jwt = mandate.claims.get("checkout_jwt")
    if not isinstance(checkout_jwt, str):
        raise MandateError("malformed", "checkout_jwt missing")
    if mandate.claims.get("checkout_hash") != sha256_b64url(checkout_jwt):
        raise MandateError("hash_mismatch", "checkout_hash is not the hash of checkout_jwt")
    verify_checkout(checkout_jwt, merchant_jwk, now=now)
    return mandate


def verify_payment_mandate(
    sd_jwt: str, *, signer_jwk: Json, checkout_jwt: str, merchant_jwk: Json, payee_id: str, now: int
) -> Verified:
    """Credential provider's check: pay exactly this checkout's total, to us, as the signer approved."""
    mandate = _verify_mandate(sd_jwt, signer_jwk, PAYMENT_VCT, now)
    checkout = verify_checkout(checkout_jwt, merchant_jwk, now=now)
    if mandate.claims.get("transaction_id") != sha256_b64url(checkout_jwt):
        raise MandateError("hash_mismatch", "transaction_id does not match this checkout")
    if mandate.claims.get("payment_amount") != checkout["total"]:
        raise MandateError("amount_mismatch", "payment_amount differs from the checkout total")
    payee = mandate.claims.get("payee")
    if not isinstance(payee, dict) or payee.get("id") != payee_id:
        raise MandateError("payee_mismatch", "payee is not this merchant")
    return mandate


def verify_open_payment_mandate(sd_jwt: str, *, user_jwk: Json, now: int) -> Verified:
    mandate = _verify_mandate(sd_jwt, user_jwk, PAYMENT_OPEN_VCT, now)
    constraints, cnf = mandate.claims.get("constraints"), mandate.claims.get("cnf")
    if not isinstance(constraints, dict) or not isinstance(cnf, dict) or not isinstance(cnf.get("jwk"), dict):
        raise MandateError("malformed", "open mandate needs constraints and cnf.jwk")
    return mandate


def check_within_open(open_mandate: Verified, closed: Verified, *, closed_signer_jwk: Json, today: str) -> None:
    """Autonomous mode: the agent-signed closed Payment Mandate must stay inside the user-signed open one."""
    if jwk_thumbprint(open_mandate.claims["cnf"]["jwk"]) != jwk_thumbprint(closed_signer_jwk):
        raise MandateError("key_not_bound", "closed mandate was not signed by the agent key the user approved")
    constraints: Json = open_mandate.claims["constraints"]
    paid: Json = closed.claims["payment_amount"]

    limits = constraints.get("payment.amount_range", {})
    for bound, too_far in (("max", lambda a, b: a > b), ("min", lambda a, b: a < b)):
        limit = limits.get(bound)
        if limit is None:
            continue
        if limit.get("currency") != paid.get("currency"):
            raise MandateError("constraint_violated", "currency differs from the open mandate")
        if too_far(paid["amount"], limit["amount"]):
            raise MandateError("constraint_violated", f"amount is outside the approved {bound}")

    payees = constraints.get("payment.allowed_payees")
    if payees is not None and closed.claims["payee"].get("id") not in payees:
        raise MandateError("constraint_violated", "payee is not in the approved list")

    window = constraints.get("payment.execution_date")
    if window is not None and not (window["not_before"] <= today <= window["not_after"]):
        raise MandateError("constraint_violated", "outside the approved dates")
