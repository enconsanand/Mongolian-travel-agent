"""The whole saga over HTTP: hold stays, pay with an AP2 mandate, the simulator calls back, the trip is booked."""

from urllib.parse import urlsplit

import pytest
from fastapi.testclient import TestClient

from app import ap2
from app.api.v1 import payments as payments_api
from app.api.v1.deps import get_current_active_user
from app.main import app
from app.models.user import User
from app.modules.payment.rails import QPayRail
from app.seeds.mock_seed import load_mock_collections
from app.services import qpay_sim
from test.payment_helpers import NOW, payment_mandate
from test.test_booking import TRIP, USER, _free_nights


@pytest.fixture
def api(client, db, monkeypatch):
    load_mock_collections(db, real_server=False)
    db["trips"].update_one({"_id": TRIP}, {"$set": {"user_id": USER, "status": "planned"}})
    sent: list[str] = []
    monkeypatch.setattr(qpay_sim.httpx, "get", lambda url, **_: sent.append(str(url)))
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
    app.dependency_overrides.update(
        {payments_api.get_rail: lambda: rail, get_current_active_user: lambda: user, payments_api.get_now: lambda: NOW}
    )
    client.sim, client.sent = sim, sent  # type: ignore[attr-defined]
    yield client
    for dep in (payments_api.get_rail, get_current_active_user, payments_api.get_now):
        app.dependency_overrides.pop(dep, None)


def test_hold_pay_and_book_over_http(api, db):
    stay, unit, dates = _free_nights(db, basis="per_unit", nights=2)
    key = ap2.generate_key()
    kid = api.post("/api/v1/me/keys", json={"jwk": ap2.public_jwk(key)}).json()["kid"]

    created = api.post(
        f"/api/v1/me/trips/{TRIP}/checkouts",
        json={
            "stays": [
                {"stay_id": stay["_id"], "unit_type": unit["unit_type"], "check_in": dates[0], "nights": 2, "guests": 1}
            ]
        },
    )
    assert created.status_code == 201, created.text
    checkout = created.json()
    assert checkout["status"] == "open" and len(checkout["lines"]) == 2

    mandate = payment_mandate(key, checkout["checkout_jwt"], amount_mnt=checkout["total_mnt"])
    paid = api.post(f"/api/v1/me/checkouts/{checkout['id']}/pay", json={"payment_mandate": mandate, "kid": kid})
    assert paid.status_code == 200 and paid.json()["status"] == "awaiting_payment"

    invoice = db["payments"].find_one({"_id": paid.json()["id"]})["provider_ref"]
    api.sim.post(f"/_sim/invoices/{invoice}/pay")
    parts = urlsplit(api.sent[0])
    assert api.post(f"{parts.path}?{parts.query}").text == "SUCCESS"

    view = api.get(f"/api/v1/me/checkouts/{checkout['id']}").json()
    assert view["status"] == "paid" and view["payment"]["status"] == "paid"
    assert [b["status"] for b in view["bookings"]] == ["confirmed"]  # confirmed by the webhook, no background loop


def test_unavailable_stay_is_409(api, db):
    stay, unit, dates = _free_nights(db, basis="per_unit", nights=1)
    db["stay_availability"].update_one(
        {"stay_id": stay["_id"], "unit_type": unit["unit_type"], "date": dates[0]}, {"$set": {"available": 0}}
    )
    resp = api.post(
        f"/api/v1/me/trips/{TRIP}/checkouts",
        json={
            "stays": [
                {"stay_id": stay["_id"], "unit_type": unit["unit_type"], "check_in": dates[0], "nights": 1, "guests": 1}
            ]
        },
    )
    assert resp.status_code == 409 and resp.json()["detail"]["code"] == "unavailable"


def test_bad_date_is_422(api):
    resp = api.post(
        f"/api/v1/me/trips/{TRIP}/checkouts",
        json={"stays": [{"stay_id": "s", "unit_type": "ger", "check_in": "tomorrow", "nights": 1, "guests": 1}]},
    )
    assert resp.status_code == 422


def test_checkout_of_another_user_is_404(api):
    assert api.get("/api/v1/me/checkouts/chk_not_mine").status_code == 404
