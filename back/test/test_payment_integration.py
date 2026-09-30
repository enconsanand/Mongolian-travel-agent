"""The payment flow on a real MongoDB replica set: transactions, unique indexes, replay protection.

Skipped unless MONGO_TEST_URI is set, e.g. with the compose stack running:
    MONGO_TEST_URI="mongodb://localhost:27018/?directConnection=true" uv run pytest test/test_payment_integration.py
It uses a throwaway database and drops it afterwards.
"""

import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

from app import ap2
from app.db.mongo import ensure_indexes
from app.modules import payment
from app.modules.payment.rails import QPayRail
from app.services import qpay_sim
from test.payment_helpers import NOW, USER, insert_checkout, payment_mandate

URI = os.environ.get("MONGO_TEST_URI")
pytestmark = pytest.mark.skipif(not URI, reason="set MONGO_TEST_URI to run against a real replica set")


@pytest.fixture
def real_db():
    client = MongoClient(URI, tz_aware=True, serverSelectionTimeoutMS=5000)
    name = f"test_payments_{uuid4().hex[:8]}"
    db = client[name]
    assert not ensure_indexes(db)
    yield db
    client.drop_database(name)


@pytest.fixture
def rail(monkeypatch):
    sent: list[str] = []
    monkeypatch.setattr(qpay_sim.httpx, "post", lambda url, **_: sent.append(str(url)))
    sim = TestClient(qpay_sim.app)
    sim.post("/_sim/reset")
    r = QPayRail(
        rail_id="sim",
        base_url="x",
        username=qpay_sim.USERNAME,
        password=qpay_sim.PASSWORD,
        invoice_code="S",
        client=sim,
    )
    r.sim, r.sent = sim, sent  # type: ignore[attr-defined]
    return r


def test_full_flow_uses_transactions_and_settles_once(real_db, rail):
    user_key = ap2.generate_key()
    kid = payment.register_user_key(real_db, user_id=USER, jwk=ap2.public_jwk(user_key), now=NOW)
    checkout_jwt = insert_checkout(real_db)
    p = payment.start_payment(
        real_db,
        rail,
        user_id=USER,
        checkout_id="chk_1",
        payment_mandate=payment_mandate(user_key, checkout_jwt),
        kid=kid,
        instrument="qpay_qr",
        now=NOW,
    ).payment
    rail.sim.post(f"/_sim/invoices/{p['provider_ref']}/pay", params={"callbacks": 3})
    token = payment.webhook_token(p["_id"])
    outcomes = [
        payment.handle_callback(real_db, rail, payment_id=p["_id"], token=token, query={}, body=b"", now=NOW)
        for _ in rail.sent
    ]
    assert outcomes.count("paid") == 1
    assert real_db["outbox"].count_documents({"type": "payment.paid"}) == 1
    assert real_db["checkouts"].find_one({"_id": "chk_1"})["status"] == "paid"


def test_replay_index_blocks_a_second_used_mandate_for_the_same_checkout(real_db):
    base = {"kind": "payment", "form": "closed", "transaction_id": "hash-1", "status": "used"}
    real_db["mandates"].insert_one({"_id": "m1", "hash": "a", **base})
    with pytest.raises(DuplicateKeyError):
        real_db["mandates"].insert_one({"_id": "m2", "hash": "b", **base})
    real_db["mandates"].insert_one({"_id": "m3", "hash": "c", **base, "status": "rejected"})  # evidence is allowed


def test_one_payment_per_transaction_id(real_db):
    real_db["payments"].insert_one({"_id": "p1", "idempotency_key": "k1", "transaction_id": "t"})
    with pytest.raises(DuplicateKeyError):
        real_db["payments"].insert_one({"_id": "p2", "idempotency_key": "k2", "transaction_id": "t"})
    real_db["payments"].insert_many([{"_id": "p3", "idempotency_key": "k3"}, {"_id": "p4", "idempotency_key": "k4"}])
