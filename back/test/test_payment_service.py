"""Payment service against the QPay simulator: start, idempotency, rejections, callbacks, settlement."""

from datetime import timedelta
from urllib.parse import urlsplit

import pytest
from fastapi.testclient import TestClient

from app import ap2
from app.modules import payment
from app.modules.payment.rails import QPayRail
from app.services import qpay_sim
from test.payment_helpers import NOW, USER, insert_checkout, payment_mandate


@pytest.fixture
def sim(monkeypatch):
    sent: list[str] = []
    monkeypatch.setattr(qpay_sim.httpx, "get", lambda url, **_: sent.append(str(url)))
    with TestClient(qpay_sim.app) as client:
        client.post("/_sim/reset")
        client.sent = sent  # type: ignore[attr-defined]
        yield client


@pytest.fixture
def rail(sim):
    return QPayRail(
        rail_id="sim",
        base_url="http://unused",
        username=qpay_sim.USERNAME,
        password=qpay_sim.PASSWORD,
        invoice_code="SIM",
        client=sim,
    )


@pytest.fixture
def user_key():
    return ap2.generate_key()


@pytest.fixture
def kid(db, user_key):
    return payment.register_user_key(db, user_id=USER, jwk=ap2.public_jwk(user_key), now=NOW)


def _start(db, rail, mandate, kid, checkout_id="chk_1"):
    return payment.start_payment(
        db, rail, user_id=USER, checkout_id=checkout_id, payment_mandate=mandate, kid=kid, instrument="qpay_qr", now=NOW
    )


def _callback(db, rail, url):
    parts = urlsplit(url)
    _, payment_id, token = parts.path.rsplit("/", 2)
    query = dict(p.split("=", 1) for p in parts.query.split("&")) if parts.query else {}
    return payment.handle_callback(db, rail, payment_id=payment_id, token=token, query=query, body=b"", now=NOW)


def _code(fn):
    with pytest.raises(payment.PaymentError) as info:
        fn()
    return info.value.code, info.value.detail


# ----------------------------------------------------------------------------- start


def test_start_payment_opens_a_charge(db, rail, user_key, kid):
    checkout_jwt = insert_checkout(db)
    started = _start(db, rail, payment_mandate(user_key, checkout_jwt), kid)

    p = started.payment
    assert started.created
    assert p["status"] == "awaiting_payment"
    assert p["provider"] == "sim" and p["provider_ref"].startswith("sim_inv_")
    assert p["charge"]["qr_text"] and p["charge"]["deeplinks"]
    assert p["transaction_id"] == db["checkouts"].find_one({"_id": "chk_1"})["checkout_hash"]
    mandate = db["mandates"].find_one({"_id": p["payment_mandate_id"]})
    assert mandate["status"] == "used" and mandate["signer"] == "user"
    assert db["audit_log"].count_documents({"action": "payment_approved"}) == 1


def test_start_payment_is_idempotent(db, rail, user_key, kid, sim):
    checkout_jwt = insert_checkout(db)
    mandate = payment_mandate(user_key, checkout_jwt)
    first = _start(db, rail, mandate, kid)
    again = _start(db, rail, mandate, kid)
    other_signature = _start(db, rail, payment_mandate(user_key, checkout_jwt), kid)

    assert first.payment["_id"] == again.payment["_id"] == other_signature.payment["_id"]
    assert not again.created and not other_signature.created
    assert len(sim.get("/_sim/invoices").json()) == 1
    assert db["payments"].count_documents({"checkout_id": "chk_1"}) == 1


@pytest.mark.parametrize(
    ("make_mandate", "reason"),
    [
        (lambda key, jwt: payment_mandate(key, jwt, amount_mnt=1), "amount_mismatch"),
        (lambda key, jwt: payment_mandate(key, jwt, payee_id="someone_else"), "payee_mismatch"),
        (lambda key, jwt: payment_mandate(ap2.generate_key(), jwt), "bad_signature"),
        (lambda key, jwt: "not-a-mandate", "malformed"),
    ],
)
def test_bad_mandates_never_reach_the_rail(db, rail, user_key, kid, sim, make_mandate, reason):
    checkout_jwt = insert_checkout(db)
    assert _code(lambda: _start(db, rail, make_mandate(user_key, checkout_jwt), kid)) == ("mandate_rejected", reason)
    assert sim.get("/_sim/invoices").json() == []
    assert db["payments"].count_documents({}) == 0
    assert db["mandates"].find_one({"status": "rejected"})["reject_reason"] == reason


def test_rejected_mandate_does_not_block_a_valid_one(db, rail, user_key, kid):
    checkout_jwt = insert_checkout(db)
    with pytest.raises(payment.PaymentError):
        _start(db, rail, payment_mandate(user_key, checkout_jwt, amount_mnt=1), kid)
    assert _start(db, rail, payment_mandate(user_key, checkout_jwt), kid).payment["status"] == "awaiting_payment"


def test_checkout_of_another_user_is_not_found(db, rail, user_key, kid):
    checkout_jwt = insert_checkout(db, user_id="user_anand")
    assert _code(lambda: _start(db, rail, payment_mandate(user_key, checkout_jwt), kid))[0] == "checkout_not_found"


def test_expired_checkout_is_refused(db, rail, user_key, kid):
    checkout_jwt = insert_checkout(db, expires=NOW.replace(hour=7))
    assert _code(lambda: _start(db, rail, payment_mandate(user_key, checkout_jwt), kid))[0] == "checkout_expired"


def test_unknown_key_is_refused(db, rail, user_key):
    checkout_jwt = insert_checkout(db)
    assert _code(lambda: _start(db, rail, payment_mandate(user_key, checkout_jwt), "nope"))[0] == "key_not_found"


def test_key_registration(db, user_key):
    jwk = ap2.public_jwk(user_key)
    first = payment.register_user_key(db, user_id=USER, jwk=jwk, now=NOW)
    assert payment.register_user_key(db, user_id=USER, jwk={**jwk, "kid": "x"}, now=NOW) == first
    assert db["user_keys"].count_documents({}) == 1
    assert _code(lambda: payment.register_user_key(db, user_id="user_anand", jwk=jwk, now=NOW))[0] == "key_not_found"
    with pytest.raises(ap2.MandateError):
        payment.register_user_key(db, user_id=USER, jwk={**jwk, "d": "private"}, now=NOW)


def test_rail_outage_then_retry(db, rail, user_key, kid, sim):
    checkout_jwt = insert_checkout(db)
    mandate = payment_mandate(user_key, checkout_jwt)
    rail.create_charge(charge_id="warm", amount_mnt=1, description="warm", callback_url="http://x")  # get a token
    sim.post("/_sim/config", json={"fail_next": 1})

    assert _code(lambda: _start(db, rail, mandate, kid))[0] == "rail_unavailable"
    assert db["payments"].find_one({"_id": "pay_chk_1"})["status"] == "approved_by_user"

    assert _start(db, rail, mandate, kid).payment["status"] == "awaiting_payment"


# ----------------------------------------------------------------------------- callbacks


def test_paid_callback_settles_once(db, rail, user_key, kid, sim):
    checkout_jwt = insert_checkout(db)
    p = _start(db, rail, payment_mandate(user_key, checkout_jwt), kid).payment
    assert p["charge"] and not db["outbox"].count_documents({})

    sim.post(f"/_sim/invoices/{p['provider_ref']}/pay", params={"callbacks": 3})
    outcomes = [_callback(db, rail, url) for url in sim.sent]

    assert outcomes == ["paid", "already_settled", "already_settled"]
    settled = db["payments"].find_one({"_id": p["_id"]})
    assert settled["status"] == "paid" and settled["charge"]["provider_payment_id"].startswith("sim_pay_")
    assert db["checkouts"].find_one({"_id": "chk_1"})["status"] == "paid"
    assert db["outbox"].count_documents({"type": "payment.paid", "aggregate_id": p["_id"]}) == 1
    assert db["payment_events"].count_documents({"kind": "callback"}) == 1  # repeated callbacks stored once


def test_callback_before_payment_is_pending(db, rail, user_key, kid):
    checkout_jwt = insert_checkout(db)
    p = _start(db, rail, payment_mandate(user_key, checkout_jwt), kid).payment
    token = payment.webhook_token(p["_id"])
    assert payment.handle_callback(db, rail, payment_id=p["_id"], token=token, query={}, body=b"", now=NOW) == "pending"


def test_underpaid_is_not_settled(db, rail, user_key, kid, sim):
    checkout_jwt = insert_checkout(db)
    p = _start(db, rail, payment_mandate(user_key, checkout_jwt), kid).payment
    sim.post(f"/_sim/invoices/{p['provider_ref']}/pay", params={"amount": 1000})
    assert _callback(db, rail, sim.sent[0]) == "underpaid"
    assert db["payments"].find_one({"_id": p["_id"]})["status"] == "awaiting_payment"
    assert db["audit_log"].count_documents({"action": "payment_underpaid"}) == 1


def test_failed_payment(db, rail, user_key, kid, sim):
    checkout_jwt = insert_checkout(db)
    p = _start(db, rail, payment_mandate(user_key, checkout_jwt), kid).payment
    sim.post(f"/_sim/invoices/{p['provider_ref']}/fail")
    token = payment.webhook_token(p["_id"])
    assert payment.handle_callback(db, rail, payment_id=p["_id"], token=token, query={}, body=b"", now=NOW) == "failed"
    assert db["outbox"].count_documents({"type": "payment.failed"}) == 1


def test_forged_callback_is_rejected(db, rail, user_key, kid):
    checkout_jwt = insert_checkout(db)
    p = _start(db, rail, payment_mandate(user_key, checkout_jwt), kid).payment
    with pytest.raises(LookupError):
        payment.handle_callback(db, rail, payment_id=p["_id"], token="guess", query={}, body=b"", now=NOW)
    with pytest.raises(LookupError):
        payment.handle_callback(
            db, rail, payment_id="pay_other", token=payment.webhook_token("pay_other"), query={}, body=b"", now=NOW
        )


def test_callback_url_carries_the_token():
    url = payment.callback_url("sim", "pay_chk_1")
    assert url.endswith(f"/webhooks/sim/pay_chk_1/{payment.webhook_token('pay_chk_1')}")
    assert payment.webhook_token("pay_chk_1") != payment.webhook_token("pay_chk_2")


# ----------------------------------------------------------------------------- reconcile (lost callbacks)


def _awaiting(db, rail, user_key, kid, sim, *, callbacks=False):
    sim.post("/_sim/config", json={"send_callbacks": callbacks})
    checkout_jwt = insert_checkout(db)
    return _start(db, rail, payment_mandate(user_key, checkout_jwt), kid).payment


def test_reconcile_settles_a_payment_whose_callback_was_lost(db, rail, user_key, kid, sim):
    p = _awaiting(db, rail, user_key, kid, sim)
    sim.post(f"/_sim/invoices/{p['provider_ref']}/pay")
    assert sim.sent == []  # QPay dropped the callback

    assert payment.reconcile_unpaid(db, rail, now=NOW + timedelta(seconds=5)) == 0  # still waiting for it
    assert payment.reconcile_unpaid(db, rail, now=NOW + timedelta(seconds=31)) == 1
    assert db["payments"].find_one({"_id": p["_id"]})["status"] == "paid"
    assert db["outbox"].count_documents({"type": "payment.paid"}) == 1


def test_reconcile_checks_each_unpaid_charge_at_most_once_a_minute(db, rail, user_key, kid, sim):
    p = _awaiting(db, rail, user_key, kid, sim)
    later = NOW + timedelta(minutes=1)
    assert payment.reconcile_unpaid(db, rail, now=later) == 0  # unpaid: checked once
    sim.post(f"/_sim/invoices/{p['provider_ref']}/pay")
    assert payment.reconcile_unpaid(db, rail, now=later + timedelta(seconds=30)) == 0  # too soon to ask again
    assert payment.reconcile_unpaid(db, rail, now=later + timedelta(seconds=61)) == 1


def test_reconcile_audits_an_underpayment_once(db, rail, user_key, kid, sim):
    p = _awaiting(db, rail, user_key, kid, sim)
    sim.post(f"/_sim/invoices/{p['provider_ref']}/pay", params={"amount": 1000})
    for minute in range(1, 4):
        payment.reconcile_unpaid(db, rail, now=NOW + timedelta(minutes=minute))
    assert db["payments"].find_one({"_id": p["_id"]})["status"] == "awaiting_payment"
    assert db["audit_log"].count_documents({"action": "payment_underpaid"}) == 1


def test_reconcile_survives_a_rail_outage(db, rail, user_key, kid, sim):
    p = _awaiting(db, rail, user_key, kid, sim)
    sim.post(f"/_sim/invoices/{p['provider_ref']}/pay")
    sim.post("/_sim/config", json={"fail_next": 1})
    assert payment.reconcile_unpaid(db, rail, now=NOW + timedelta(minutes=1)) == 0
    assert payment.reconcile_unpaid(db, rail, now=NOW + timedelta(minutes=2)) == 1


def test_reconcile_after_the_callback_settled_does_nothing(db, rail, user_key, kid, sim):
    p = _awaiting(db, rail, user_key, kid, sim, callbacks=True)
    sim.post(f"/_sim/invoices/{p['provider_ref']}/pay")
    assert _callback(db, rail, sim.sent[0]) == "paid"
    assert payment.reconcile_unpaid(db, rail, now=NOW + timedelta(minutes=5)) == 0
