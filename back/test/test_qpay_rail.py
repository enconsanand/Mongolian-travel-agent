"""The QPay adapter against the QPay simulator, over HTTP in-process (FastAPI TestClient)."""

import pytest
from fastapi.testclient import TestClient

from app.modules.payment.rails import QPayRail, RailError, build_rail
from app.services import qpay_sim

CALLBACK = "http://back.test/api/v1/webhooks/qpay/secret-token"


class Clock:
    def __init__(self) -> None:
        self.now = 1_790_000_000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def sim(monkeypatch):
    sent: list[str] = []
    monkeypatch.setattr(qpay_sim.httpx, "post", lambda url, **_: sent.append(str(url)))
    with TestClient(qpay_sim.app) as client:
        client.post("/_sim/reset")
        client.sent = sent  # type: ignore[attr-defined]
        yield client


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def rail(sim, clock):
    return QPayRail(
        rail_id="sim",
        base_url="http://unused",
        username=qpay_sim.USERNAME,
        password=qpay_sim.PASSWORD,
        invoice_code="SIM_INVOICE",
        client=sim,
        clock=clock,
    )


def _charge(rail, amount=180000, charge_id="pay_trip_1"):
    return rail.create_charge(charge_id=charge_id, amount_mnt=amount, description="Trip", callback_url=CALLBACK)


def test_create_charge_returns_what_the_user_pays_with(rail):
    handle = _charge(rail)
    assert handle.provider == "sim"
    assert handle.provider_ref.startswith("sim_inv_")
    assert handle.amount_mnt == 180000
    assert handle.qr_text and handle.short_url
    assert handle.deeplinks and handle.deeplinks[0]["link"].startswith("simbank://")


def test_verify_is_pending_until_paid_then_paid(rail, sim):
    handle = _charge(rail)
    assert rail.verify(handle.provider_ref).state == "pending"

    paid = sim.post(f"/_sim/invoices/{handle.provider_ref}/pay").json()

    status = rail.verify(handle.provider_ref)
    assert status.state == "paid"
    assert status.paid_amount_mnt == 180000
    assert status.provider_payment_id == paid["payment_id"]


def test_partial_payment_reports_the_amount_actually_paid(rail, sim):
    # The rail reports; the payment module must compare paid_amount_mnt with what it expected
    handle = _charge(rail)
    sim.post(f"/_sim/invoices/{handle.provider_ref}/pay", params={"amount": 1000})
    status = rail.verify(handle.provider_ref)
    assert status.paid_amount_mnt == 1000 < handle.amount_mnt


def test_failed_payment(rail, sim):
    handle = _charge(rail)
    sim.post(f"/_sim/invoices/{handle.provider_ref}/fail")
    assert rail.verify(handle.provider_ref).state == "failed"


def test_cancel_open_invoice_but_not_a_paid_one(rail, sim):
    open_one = _charge(rail, charge_id="a")
    rail.cancel(open_one.provider_ref)
    paid_one = _charge(rail, charge_id="b")
    sim.post(f"/_sim/invoices/{paid_one.provider_ref}/pay")
    with pytest.raises(RailError) as info:
        rail.cancel(paid_one.provider_ref)
    assert info.value.status_code == 422 and not info.value.retryable


def test_card_payments_refund_and_bank_qr_payments_do_not(rail, sim):
    card = _charge(rail, charge_id="card")
    card_payment = sim.post(f"/_sim/invoices/{card.provider_ref}/pay", params={"method": "CARD"}).json()["payment_id"]
    rail.refund(card_payment)

    qr = _charge(rail, charge_id="qr")
    qr_payment = sim.post(f"/_sim/invoices/{qr.provider_ref}/pay").json()["payment_id"]
    with pytest.raises(RailError):
        rail.refund(qr_payment)  # the payment module queues a manual refund


def test_issue_receipt_is_idempotent(rail, sim):
    handle = _charge(rail)
    payment_id = sim.post(f"/_sim/invoices/{handle.provider_ref}/pay").json()["payment_id"]
    assert rail.issue_receipt(payment_id) == rail.issue_receipt(payment_id)


def test_expired_token_is_replaced_transparently(rail, sim):
    _charge(rail, charge_id="first")
    qpay_sim.state.tokens.clear()  # the server forgets our token (restart, revocation)
    assert _charge(rail, charge_id="second").provider_ref


def test_refresh_token_is_used_when_the_access_token_expires(rail, clock):
    _charge(rail, charge_id="first")
    refresh_before = set(qpay_sim.state.refresh)
    clock.now += qpay_sim.TOKEN_TTL  # access token expired locally, refresh token still valid
    _charge(rail, charge_id="second")
    assert refresh_before and not refresh_before & set(qpay_sim.state.refresh)  # the old refresh token was spent


def test_outage_is_retryable(rail, sim):
    _charge(rail, charge_id="warm")
    sim.post("/_sim/config", json={"fail_next": 1})
    with pytest.raises(RailError) as info:
        _charge(rail, charge_id="during-outage")
    assert info.value.retryable


def test_bad_credentials(sim):
    rail = QPayRail(base_url="x", username="nope", password="nope", invoice_code="X", client=sim)
    with pytest.raises(RailError, match="auth"):
        _charge(rail)


def test_non_positive_amount_is_refused_before_calling_qpay(rail):
    with pytest.raises(RailError):
        _charge(rail, amount=0)


def test_repeated_callbacks_are_sent_and_parse_to_the_same_hint(rail, sim):
    handle = _charge(rail)
    payment_id = sim.post(f"/_sim/invoices/{handle.provider_ref}/pay", params={"callbacks": 3}).json()["payment_id"]
    assert len(sim.sent) == 3
    assert all(url.startswith(CALLBACK) and payment_id in url for url in sim.sent)

    from_query = rail.parse_webhook({"payment_id": payment_id, "invoice_id": handle.provider_ref}, b"")
    from_body = rail.parse_webhook(
        {}, f'{{"payment_id": "{payment_id}", "object_id": "{handle.provider_ref}"}}'.encode()
    )
    assert from_query == from_body
    assert rail.parse_webhook({}, b"not json").provider_payment_id is None


def test_build_rail():
    sim_rail = build_rail("sim", base_url="http://qpay-sim:8010", username="u", password="p", invoice_code="c")
    assert isinstance(sim_rail, QPayRail) and sim_rail.id == "sim"
    with pytest.raises(NotImplementedError):
        build_rail("bonum", base_url="x", username="u", password="p", invoice_code="c")
