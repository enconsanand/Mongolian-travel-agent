"""Cross-language check: a Payment Mandate signed by the web app (front/utils/ap2.ts, WebCrypto) verifies here.

The fixture was produced by the real TypeScript code against a checkout signed by app.ap2. If either side changes
the mandate format (claim names, amount units, signature encoding), this fails before the demo does.
"""

import json
from pathlib import Path

import pytest

from app import ap2

VECTOR = json.loads((Path(__file__).parent / "fixtures" / "browser_mandate_vector.json").read_text())


def _verify(**overrides):
    args = {
        "signer_jwk": VECTOR["user_jwk"],
        "checkout_jwt": VECTOR["checkout_jwt"],
        "merchant_jwk": VECTOR["merchant_jwk"],
        "payee_id": "merchant_mta",
        "now": VECTOR["now"],
    } | overrides
    return ap2.verify_payment_mandate(VECTOR["payment_mandate"], **args)


def test_browser_signed_mandate_verifies():
    verified = _verify()
    assert verified.claims["transaction_id"] == VECTOR["checkout_hash"]
    assert verified.claims["payment_amount"] == {"amount": 18_000_000, "currency": "MNT"}
    assert verified.kid == "browser-vector"


def test_browser_public_key_registers_as_is():
    assert ap2.load_public_jwk(VECTOR["user_jwk"])  # the JWK exported by WebCrypto is accepted unchanged


def test_browser_mandate_is_bound_to_its_signer_and_checkout():
    with pytest.raises(ap2.MandateError):
        _verify(signer_jwk=ap2.public_jwk(ap2.generate_key()))
    with pytest.raises(ap2.MandateError):
        _verify(payee_id="someone_else")
