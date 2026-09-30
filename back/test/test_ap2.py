"""AP2 mandates: happy paths for direct and autonomous mode, and every way a mandate must be rejected."""

import base64
import json

import pytest

from app import ap2
from app.ap2 import MandateError
from app.ap2.checkout import checkout_claims
from app.ap2.jws import b64url, verify

NOW = 1_790_000_000  # epoch seconds
MERCHANT = "merchant_mta"
PAYEE = {"id": MERCHANT, "name": "Mongolian Travel Agent"}
QPAY = {"type": "qpay_qr"}
LINE = {
    "kind": "stay",
    "ref_id": "stay_khatgal_camp_blue_pearl",
    "qty": 1,
    "unit_price_mnt": 180000,
    "total_mnt": 180000,
    "date": "2026-10-03",
    "unit_type": "ger",
}


@pytest.fixture(scope="module")
def keys():
    merchant, user, agent, stranger = (ap2.generate_key() for _ in range(4))
    return {
        "merchant": merchant,
        "user": user,
        "agent": agent,
        "stranger": stranger,
        "merchant_jwk": ap2.public_jwk(merchant, "merchant-1"),
        "user_jwk": ap2.public_jwk(user, "user-1"),
        "agent_jwk": ap2.public_jwk(agent, "agent-1"),
        "stranger_jwk": ap2.public_jwk(stranger, "x"),
    }


def _checkout(keys, total_mnt=180000, exp=NOW + 900):
    lines = [{**LINE, "unit_price_mnt": total_mnt, "total_mnt": total_mnt}]
    claims = checkout_claims(
        merchant_id=MERCHANT,
        checkout_id="chk_1",
        trip_id="trip_jamba_east",
        lines=lines,
        total_mnt=total_mnt,
        iat=NOW,
        exp=exp,
    )
    return ap2.sign_checkout(claims, keys["merchant"], kid="merchant-1")


def _payment_mandate(keys, checkout_jwt, *, signer="user", amount_mnt=180000, payee=PAYEE, exp=NOW + 600):
    claims = ap2.payment_mandate_claims(
        checkout_jwt=checkout_jwt, payee=payee, amount_mnt=amount_mnt, instrument=QPAY, iat=NOW, exp=exp
    )
    return ap2.sign_mandate(claims, keys[signer], kid=f"{signer}-1")


def _verify_payment(keys, sd_jwt, checkout_jwt, *, signer_jwk="user_jwk", now=NOW):
    return ap2.verify_payment_mandate(
        sd_jwt,
        signer_jwk=keys[signer_jwk],
        checkout_jwt=checkout_jwt,
        merchant_jwk=keys["merchant_jwk"],
        payee_id=MERCHANT,
        now=now,
    )


def _code(fn):
    with pytest.raises(MandateError) as info:
        fn()
    return info.value.code


# ----------------------------------------------------------------------------- direct mode


def test_direct_mode_checkout_and_payment_mandates_verify(keys):
    checkout_jwt, checkout_hash = _checkout(keys)
    checkout_mandate = ap2.sign_mandate(
        ap2.checkout_mandate_claims(checkout_jwt, iat=NOW, exp=NOW + 600), keys["user"], kid="user-1"
    )
    verified = ap2.verify_checkout_mandate(
        checkout_mandate, signer_jwk=keys["user_jwk"], merchant_jwk=keys["merchant_jwk"], now=NOW
    )
    assert verified.claims["checkout_hash"] == checkout_hash
    assert verified.kid == "user-1"

    payment = _verify_payment(keys, _payment_mandate(keys, checkout_jwt), checkout_jwt)
    assert payment.claims["transaction_id"] == checkout_hash
    assert payment.claims["payment_amount"] == {"amount": 18_000_000, "currency": "MNT"}  # minor units


def test_mandate_hash_is_stable_and_unique_per_signature(keys):
    checkout_jwt, _ = _checkout(keys)
    first, second = _payment_mandate(keys, checkout_jwt), _payment_mandate(keys, checkout_jwt)
    assert first != second  # ECDSA is randomized
    assert ap2.mandate_hash(first) == _verify_payment(keys, first, checkout_jwt).hash
    assert ap2.mandate_hash(first) != ap2.mandate_hash(second)


# ----------------------------------------------------------------------------- rejections


def test_tampered_amount_is_rejected(keys):
    checkout_jwt, _ = _checkout(keys)
    header, payload, signature = _payment_mandate(keys, checkout_jwt)[:-1].split(".")
    claims = json.loads(base64.urlsafe_b64decode(payload + "=="))
    claims["payment_amount"]["amount"] = 1
    forged = f"{header}.{b64url(json.dumps(claims).encode())}.{signature}~"
    assert _code(lambda: _verify_payment(keys, forged, checkout_jwt)) == "bad_signature"


def test_signed_amount_different_from_checkout_is_rejected(keys):
    checkout_jwt, _ = _checkout(keys)
    sd_jwt = _payment_mandate(keys, checkout_jwt, amount_mnt=1000)
    assert _code(lambda: _verify_payment(keys, sd_jwt, checkout_jwt)) == "amount_mismatch"


def test_mandate_for_another_checkout_cannot_be_rebound(keys):
    checkout_a, _ = _checkout(keys)
    checkout_b, _ = _checkout(keys)
    sd_jwt = _payment_mandate(keys, checkout_a)
    assert _code(lambda: _verify_payment(keys, sd_jwt, checkout_b)) == "hash_mismatch"


def test_expired_mandate_is_rejected(keys):
    checkout_jwt, _ = _checkout(keys, exp=NOW + 3600)
    sd_jwt = _payment_mandate(keys, checkout_jwt, exp=NOW + 10)
    assert _code(lambda: _verify_payment(keys, sd_jwt, checkout_jwt, now=NOW + 600)) == "expired"


def test_expired_checkout_is_rejected(keys):
    checkout_jwt, _ = _checkout(keys, exp=NOW + 10)
    sd_jwt = _payment_mandate(keys, checkout_jwt, exp=NOW + 3600)
    assert _code(lambda: _verify_payment(keys, sd_jwt, checkout_jwt, now=NOW + 600)) == "expired"


def test_wrong_payee_is_rejected(keys):
    checkout_jwt, _ = _checkout(keys)
    sd_jwt = _payment_mandate(keys, checkout_jwt, payee={"id": "someone_else"})
    assert _code(lambda: _verify_payment(keys, sd_jwt, checkout_jwt)) == "payee_mismatch"


def test_mandate_signed_by_another_key_is_rejected(keys):
    checkout_jwt, _ = _checkout(keys)
    sd_jwt = _payment_mandate(keys, checkout_jwt, signer="stranger")
    assert _code(lambda: _verify_payment(keys, sd_jwt, checkout_jwt)) == "bad_signature"


def test_checkout_not_signed_by_the_merchant_is_rejected(keys):
    claims = checkout_claims(
        merchant_id=MERCHANT, checkout_id="c", trip_id="t", lines=[LINE], total_mnt=180000, iat=NOW, exp=NOW + 900
    )
    fake_checkout, _ = ap2.sign_checkout(claims, keys["stranger"], kid="merchant-1")
    sd_jwt = _payment_mandate(keys, fake_checkout)
    assert _code(lambda: _verify_payment(keys, sd_jwt, fake_checkout)) == "bad_signature"


def test_a_checkout_mandate_is_not_accepted_as_a_payment_mandate(keys):
    checkout_jwt, _ = _checkout(keys)
    wrong = ap2.sign_mandate(ap2.checkout_mandate_claims(checkout_jwt, iat=NOW, exp=NOW + 60), keys["user"], kid="u")
    assert _code(lambda: _verify_payment(keys, wrong, checkout_jwt)) == "wrong_vct"


@pytest.mark.parametrize("alg", ["none", "HS256", "ES384"])
def test_only_es256_is_accepted(keys, alg):
    checkout_jwt, _ = _checkout(keys)
    _, payload, signature = _payment_mandate(keys, checkout_jwt)[:-1].split(".")
    header = b64url(json.dumps({"alg": alg, "typ": "dc+sd-jwt"}).encode())
    assert _code(lambda: _verify_payment(keys, f"{header}.{payload}.{signature}~", checkout_jwt)) == "wrong_alg"


@pytest.mark.parametrize(
    "token",
    ["", "not-a-token", "a.b.c", "a.b~", "x.y.z~disclosure~"],
)
def test_malformed_mandates_are_rejected(keys, token):
    checkout_jwt, _ = _checkout(keys)
    assert _code(lambda: _verify_payment(keys, token, checkout_jwt)) in {"malformed", "wrong_alg"}


def test_private_jwk_is_refused_as_a_verification_key(keys):
    private_jwk = {**keys["user_jwk"], "d": "secret"}
    assert _code(lambda: ap2.load_public_jwk(private_jwk)) == "bad_key"


def test_checkout_total_must_equal_its_lines():
    with pytest.raises(ValueError):
        checkout_claims(merchant_id="m", checkout_id="c", trip_id="t", lines=[LINE], total_mnt=1, iat=NOW, exp=NOW)


# ----------------------------------------------------------------------------- autonomous mode


def _open_mandate(keys, max_mnt=500000, payees=(MERCHANT,), window=("2026-10-01", "2026-10-14")):
    claims = ap2.open_payment_mandate_claims(
        max_mnt=max_mnt,
        agent_jwk=keys["agent_jwk"],
        allowed_payees=list(payees),
        execution_window=window,
        iat=NOW,
        exp=NOW + 86400,
    )
    sd_jwt = ap2.sign_mandate(claims, keys["user"], kid="user-1")
    return ap2.verify_open_payment_mandate(sd_jwt, user_jwk=keys["user_jwk"], now=NOW)


def test_autonomous_closed_mandate_within_open_mandate(keys):
    checkout_jwt, _ = _checkout(keys, total_mnt=300000)
    closed = _verify_payment(
        keys,
        _payment_mandate(keys, checkout_jwt, signer="agent", amount_mnt=300000),
        checkout_jwt,
        signer_jwk="agent_jwk",
    )
    ap2.check_within_open(_open_mandate(keys), closed, closed_signer_jwk=keys["agent_jwk"], today="2026-10-03")


@pytest.mark.parametrize(
    ("open_kwargs", "today"),
    [
        ({"max_mnt": 200000}, "2026-10-03"),  # over the approved cap
        ({"payees": ("other_merchant",)}, "2026-10-03"),
        ({}, "2026-10-20"),  # outside the approved dates
    ],
)
def test_autonomous_closed_mandate_outside_open_mandate_is_rejected(keys, open_kwargs, today):
    checkout_jwt, _ = _checkout(keys, total_mnt=300000)
    closed = _verify_payment(
        keys,
        _payment_mandate(keys, checkout_jwt, signer="agent", amount_mnt=300000),
        checkout_jwt,
        signer_jwk="agent_jwk",
    )
    code = _code(
        lambda: ap2.check_within_open(
            _open_mandate(keys, **open_kwargs), closed, closed_signer_jwk=keys["agent_jwk"], today=today
        )
    )
    assert code == "constraint_violated"


def test_autonomous_closed_mandate_from_an_unbound_key_is_rejected(keys):
    checkout_jwt, _ = _checkout(keys)
    closed = _verify_payment(
        keys, _payment_mandate(keys, checkout_jwt, signer="stranger"), checkout_jwt, signer_jwk="stranger_jwk"
    )
    code = _code(
        lambda: ap2.check_within_open(
            _open_mandate(keys), closed, closed_signer_jwk=keys["stranger_jwk"], today="2026-10-03"
        )
    )
    assert code == "key_not_bound"


# ----------------------------------------------------------------------------- browser interop


def test_externally_made_raw_signature_verifies(keys):
    """Build the JWS without our ``sign``: sign the bytes, convert DER to raw r||s the way WebCrypto returns it."""
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature

    header = b64url(json.dumps({"alg": "ES256", "typ": "JWT"}).encode())
    payload = b64url(json.dumps({"hello": "world"}).encode())
    der = keys["user"].sign(f"{header}.{payload}".encode(), ec.ECDSA(hashes.SHA256()))
    r, s = decode_dss_signature(der)
    raw = r.to_bytes(32, "big") + s.to_bytes(32, "big")
    _, claims = verify(f"{header}.{payload}.{b64url(raw)}", keys["user_jwk"])
    assert claims == {"hello": "world"}


def test_thumbprint_ignores_kid(keys):
    assert ap2.jwk_thumbprint(keys["user_jwk"]) == ap2.jwk_thumbprint({**keys["user_jwk"], "kid": "other"})
