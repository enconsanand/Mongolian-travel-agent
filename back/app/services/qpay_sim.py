"""QPay Merchant V2 simulator: the same endpoints and field names as ``app.modules.payment.rails.qpay`` uses.

Run: ``uvicorn app.services.qpay_sim:app --port 8010`` (the ``qpay-sim`` compose service). State is in memory.

Besides the QPay API it has ``/_sim/...`` endpoints for demos and tests: pay an invoice (optionally sending the
callback several times, like QPay retries do), fail it, slow down or fail the next calls. It never talks to a bank.

Behaviour that is a guess about real QPay (so our code must not depend on it): a repeated ``sender_invoice_no``
returns the existing invoice; callbacks are sent as POST with ``payment_id`` and ``invoice_id`` in the query.
"""

import base64
import contextlib
import os
import secrets
import threading
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Annotated, Any

import httpx
from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Query, status
from pydantic import BaseModel, Field

USERNAME = os.environ.get("QPAY_SIM_USERNAME", "sim_merchant")
PASSWORD = os.environ.get("QPAY_SIM_PASSWORD", "sim_password")
TOKEN_TTL = 3600
REFRESH_TTL = 86400


def _now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class Invoice:
    invoice_id: str
    invoice_code: str
    sender_invoice_no: str
    amount: int
    description: str
    callback_url: str
    status: str = "OPEN"  # OPEN, PAID, CANCELLED
    payment_ids: list[str] = field(default_factory=list)


@dataclass
class Payment:
    payment_id: str
    invoice_id: str
    amount: int
    status: str  # PAID, FAILED, REFUNDED
    payment_type: str  # P2P (bank QR) or CARD
    date: str = field(default_factory=_now_iso)


@dataclass
class State:
    tokens: dict[str, float] = field(default_factory=dict)  # access token -> expires at
    refresh: dict[str, float] = field(default_factory=dict)
    invoices: dict[str, Invoice] = field(default_factory=dict)
    by_sender_no: dict[str, str] = field(default_factory=dict)
    payments: dict[str, Payment] = field(default_factory=dict)
    receipts: dict[str, str] = field(default_factory=dict)  # payment_id -> receipt id
    latency_ms: int = 0
    fail_next: int = 0  # the next N API calls answer 503
    send_callbacks: bool = True
    callbacks_sent: list[str] = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)


state = State()
app = FastAPI(title="QPay Merchant V2 simulator", docs_url="/_sim/docs", openapi_url="/_sim/openapi.json")


def _chaos() -> None:
    if state.latency_ms:
        time.sleep(state.latency_ms / 1000)
    with state.lock:
        if state.fail_next > 0:
            state.fail_next -= 1
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "simulated outage")


def _issue_tokens() -> dict[str, Any]:
    access, refresh = secrets.token_urlsafe(24), secrets.token_urlsafe(24)
    now = time.time()
    with state.lock:
        state.tokens[access] = now + TOKEN_TTL
        state.refresh[refresh] = now + REFRESH_TTL
    return {
        "token_type": "bearer",
        "access_token": access,
        "expires_in": TOKEN_TTL,
        "refresh_token": refresh,
        "refresh_expires_in": REFRESH_TTL,
        "scope": "sim",
    }


def _bearer(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing bearer token")
    return authorization.removeprefix("Bearer ")


def require_token(authorization: Annotated[str | None, Header()] = None) -> None:
    _chaos()
    token = _bearer(authorization)
    if state.tokens.get(token, 0) < time.time():
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid or expired token")


Auth = Annotated[None, Depends(require_token)]


# ----------------------------------------------------------------------------- auth


@app.post("/v2/auth/token")
def token(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    _chaos()
    expected = "Basic " + base64.b64encode(f"{USERNAME}:{PASSWORD}".encode()).decode()
    if not authorization or not secrets.compare_digest(authorization, expected):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "bad credentials")
    return _issue_tokens()


@app.post("/v2/auth/refresh")
def refresh(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    _chaos()
    token_ = _bearer(authorization)
    with state.lock:
        valid = state.refresh.pop(token_, 0) >= time.time()
    if not valid:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid refresh token")
    return _issue_tokens()


# ----------------------------------------------------------------------------- invoices


class InvoiceIn(BaseModel):
    invoice_code: str
    sender_invoice_no: str = Field(min_length=1, max_length=45)
    invoice_receiver_code: str
    invoice_description: str
    amount: int = Field(gt=0)
    callback_url: str


def _invoice_out(inv: Invoice) -> dict[str, Any]:
    qr_text = f"SIM|{inv.invoice_id}|{inv.amount}"
    return {
        "invoice_id": inv.invoice_id,
        "qr_text": qr_text,
        "qr_image": base64.b64encode(qr_text.encode()).decode(),  # not a real PNG; the UI can render qr_text
        "qPay_shortUrl": f"https://qpay.sim/{inv.invoice_id}",
        "urls": [
            {"name": "Sim Bank", "description": "Simulated bank app", "logo": "", "link": f"simbank://q?{qr_text}"}
        ],
    }


@app.post("/v2/invoice")
def create_invoice(body: InvoiceIn, _: Auth) -> dict[str, Any]:
    with state.lock:
        existing = state.by_sender_no.get(body.sender_invoice_no)
        if existing:
            return _invoice_out(state.invoices[existing])
        inv = Invoice(
            invoice_id=f"sim_inv_{secrets.token_hex(8)}",
            invoice_code=body.invoice_code,
            sender_invoice_no=body.sender_invoice_no,
            amount=body.amount,
            description=body.invoice_description,
            callback_url=body.callback_url,
        )
        state.invoices[inv.invoice_id] = inv
        state.by_sender_no[inv.sender_invoice_no] = inv.invoice_id
    return _invoice_out(inv)


def _get_invoice(invoice_id: str) -> Invoice:
    inv = state.invoices.get(invoice_id)
    if inv is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "INVOICE_NOTFOUND")
    return inv


@app.get("/v2/invoice/{invoice_id}")
def get_invoice(invoice_id: str, _: Auth) -> dict[str, Any]:
    inv = _get_invoice(invoice_id)
    return {"invoice_id": inv.invoice_id, "invoice_status": inv.status, "amount": inv.amount}


@app.delete("/v2/invoice/{invoice_id}")
def cancel_invoice(invoice_id: str, _: Auth) -> dict[str, Any]:
    with state.lock:
        inv = _get_invoice(invoice_id)
        if inv.status == "PAID":
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "INVOICE_PAID")
        inv.status = "CANCELLED"
    return {"invoice_id": invoice_id, "invoice_status": "CANCELLED"}


# ----------------------------------------------------------------------------- payments


class Offset(BaseModel):
    page_number: int = 1
    page_limit: int = 100


class CheckIn(BaseModel):
    object_type: str
    object_id: str
    offset: Offset = Offset()


@app.post("/v2/payment/check")
def check_payment(body: CheckIn, _: Auth) -> dict[str, Any]:
    if body.object_type != "INVOICE":
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "only INVOICE is simulated")
    inv = _get_invoice(body.object_id)
    rows = [state.payments[p] for p in inv.payment_ids]
    return {
        "count": len(rows),
        "paid_amount": sum(p.amount for p in rows if p.status == "PAID"),
        "rows": [
            {
                "payment_id": p.payment_id,
                "payment_status": p.status,
                "payment_amount": str(p.amount),
                "payment_currency": "MNT",
                "payment_type": p.payment_type,
                "payment_date": p.date,
            }
            for p in rows
        ],
    }


@app.delete("/v2/payment/refund/{payment_id}")
def refund_payment(payment_id: str, _: Auth) -> dict[str, Any]:
    with state.lock:
        pay = state.payments.get(payment_id)
        if pay is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "PAYMENT_NOTFOUND")
        if pay.payment_type != "CARD":
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "only card payments can be refunded")
        if pay.status != "PAID":
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"payment is {pay.status}")
        pay.status = "REFUNDED"
    return {"payment_id": payment_id, "payment_status": "REFUNDED"}


@app.post("/v2/ebarimt_v3/create")
def create_receipt(body: dict[str, Any], _: Auth) -> dict[str, Any]:
    payment_id = str(body.get("payment_id", ""))
    with state.lock:
        if payment_id not in state.payments:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "PAYMENT_NOTFOUND")
        receipt = state.receipts.setdefault(payment_id, f"sim_ebarimt_{secrets.token_hex(6)}")
    return {"id": receipt, "payment_id": payment_id, "ebarimt_receiver_type": body.get("ebarimt_receiver_type")}


# ----------------------------------------------------------------------------- simulator controls (not QPay)


def _send_callbacks(url: str, invoice_id: str, payment_id: str, times: int) -> None:
    for _ in range(times):
        target = httpx.URL(url).copy_merge_params({"payment_id": payment_id, "invoice_id": invoice_id})
        state.callbacks_sent.append(str(target))
        # like QPay: a callback that fails is simply lost; the merchant must not depend on it
        with contextlib.suppress(httpx.HTTPError):
            httpx.post(target, timeout=5)


@app.post("/_sim/invoices/{invoice_id}/pay")
def sim_pay(
    invoice_id: str,
    background: BackgroundTasks,
    amount: Annotated[int | None, Query(description="default: the invoice amount")] = None,
    method: Annotated[str, Query(pattern="^(P2P|CARD)$")] = "P2P",
    callbacks: Annotated[int, Query(ge=0, le=5, description="times to send the callback")] = 1,
) -> dict[str, Any]:
    with state.lock:
        inv = _get_invoice(invoice_id)
        if inv.status != "OPEN":
            raise HTTPException(status.HTTP_409_CONFLICT, f"invoice is {inv.status}")
        pay = Payment(
            payment_id=f"sim_pay_{secrets.token_hex(8)}",
            invoice_id=invoice_id,
            amount=inv.amount if amount is None else amount,
            status="PAID",
            payment_type=method,
        )
        state.payments[pay.payment_id] = pay
        inv.payment_ids.append(pay.payment_id)
        if pay.amount >= inv.amount:
            inv.status = "PAID"
    if state.send_callbacks and callbacks:
        background.add_task(_send_callbacks, inv.callback_url, invoice_id, pay.payment_id, callbacks)
    return {"payment_id": pay.payment_id, "invoice_status": inv.status}


@app.post("/_sim/invoices/{invoice_id}/fail")
def sim_fail(invoice_id: str) -> dict[str, Any]:
    with state.lock:
        inv = _get_invoice(invoice_id)
        pay = Payment(f"sim_pay_{secrets.token_hex(8)}", invoice_id, inv.amount, "FAILED", "CARD")
        state.payments[pay.payment_id] = pay
        inv.payment_ids.append(pay.payment_id)
    return {"payment_id": pay.payment_id, "payment_status": "FAILED"}


class SimConfig(BaseModel):
    latency_ms: int | None = Field(default=None, ge=0, le=30000)
    fail_next: int | None = Field(default=None, ge=0, le=100)
    send_callbacks: bool | None = None


@app.post("/_sim/config")
def sim_config(body: SimConfig) -> dict[str, Any]:
    with state.lock:
        for key, value in body.model_dump(exclude_none=True).items():
            setattr(state, key, value)
        return {"latency_ms": state.latency_ms, "fail_next": state.fail_next, "send_callbacks": state.send_callbacks}


@app.get("/_sim/invoices")
def sim_invoices() -> list[dict[str, Any]]:
    return [
        {"invoice_id": i.invoice_id, "sender_invoice_no": i.sender_invoice_no, "amount": i.amount, "status": i.status}
        for i in state.invoices.values()
    ]


@app.post("/_sim/reset")
def sim_reset() -> dict[str, str]:
    global state
    state = State()
    return {"status": "reset"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy", "service": "qpay-sim"}
