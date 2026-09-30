"""Payments over HTTP: register a key, pay a checkout, the simulator calls the webhook, the payment is paid."""

from urllib.parse import urlsplit

import pytest
from fastapi.testclient import TestClient

from app import ap2
from app.api.v1 import payments as payments_api
from app.api.v1.deps import get_current_active_user
from app.main import app
from app.models.user import User
from app.modules.payment.rails import QPayRail
from app.services import qpay_sim
from test.payment_helpers import NOW, USER, insert_checkout, payment_mandate


@pytest.fixture
def api(client, db, monkeypatch):
    sent: list[str] = []
    monkeypatch.setattr(qpay_sim.httpx, "post", lambda url, **_: sent.append(str(url)))
    sim = TestClient(qpay_sim.app)
    sim.post("/_sim/reset")
    rail = QPayRail(
        rail_id="sim",
        base_url="x",
        username=qpay_sim.USERNAME,
        password=qpay_sim.PASSWORD,
        invoice_code="S",
        client=sim,
    )
    user = User(_id=USER, email="jambaa@nashatech.com", hashed_password="x", first_name="Jambaa", last_name="G")
    app.dependency_overrides[payments_api.get_rail] = lambda: rail
    app.dependency_overrides[get_current_active_user] = lambda: user
    app.dependency_overrides[payments_api.get_now] = lambda: NOW
    client.sim, client.sent = sim, sent  # type: ignore[attr-defined]
    yield client
    app.dependency_overrides.pop(payments_api.get_rail, None)
    app.dependency_overrides.pop(get_current_active_user, None)
    app.dependency_overrides.pop(payments_api.get_now, None)


def test_pay_a_checkout_end_to_end(api, db):
    user_key = ap2.generate_key()
    kid = api.post("/api/v1/me/keys", json={"jwk": ap2.public_jwk(user_key)}).json()["kid"]
    checkout_jwt = insert_checkout(db)

    resp = api.post(
        "/api/v1/me/checkouts/chk_1/pay", json={"payment_mandate": payment_mandate(user_key, checkout_jwt), "kid": kid}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "awaiting_payment" and body["qr_text"] and body["amount_mnt"] == 180000
    assert body["provider"] == "sim" and body["sim_invoice_id"].startswith("sim_inv_")

    invoice = db["payments"].find_one({"_id": body["id"]})["provider_ref"]
    api.sim.post(f"/_sim/invoices/{invoice}/pay", params={"callbacks": 2})
    for url in api.sent:
        parts = urlsplit(url)
        webhook = api.post(f"{parts.path}?{parts.query}")
        assert webhook.status_code == 200 and webhook.text == "SUCCESS"

    assert db["payments"].find_one({"_id": body["id"]})["status"] == "paid"
    assert db["outbox"].count_documents({"type": "payment.paid"}) == 1


def test_rejected_mandate_is_422_with_its_reason(api, db):
    user_key = ap2.generate_key()
    kid = api.post("/api/v1/me/keys", json={"jwk": ap2.public_jwk(user_key)}).json()["kid"]
    checkout_jwt = insert_checkout(db)
    resp = api.post(
        "/api/v1/me/checkouts/chk_1/pay",
        json={"payment_mandate": payment_mandate(user_key, checkout_jwt, amount_mnt=5), "kid": kid},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == {"code": "mandate_rejected", "detail": "amount_mismatch"}


def test_private_key_registration_is_refused(api):
    jwk = {**ap2.public_jwk(ap2.generate_key()), "d": "private"}
    assert api.post("/api/v1/me/keys", json={"jwk": jwk}).status_code == 422


def test_webhook_with_a_bad_token_is_404(api):
    assert api.post("/api/v1/webhooks/sim/pay_chk_1/wrong").status_code == 404
    assert api.post("/api/v1/webhooks/qpay/pay_chk_1/wrong").status_code == 404  # not the active rail


def test_merchant_jwks_verifies_checkouts(api, db):
    jwks = api.get("/api/v1/merchant/jwks").json()
    checkout_jwt = insert_checkout(db)
    claims = ap2.verify_checkout(checkout_jwt, jwks["keys"][0], now=int(NOW.timestamp()))
    assert claims["iss"] == jwks["merchant_id"]
    assert "d" not in jwks["keys"][0]
