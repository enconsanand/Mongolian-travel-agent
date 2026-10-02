"""QPay Merchant V2 simulator: the same endpoints and field names as ``app.modules.payment.rails.qpay`` uses.

Run: ``uvicorn app.services.qpay_sim:app --port 8010`` (the ``qpay-sim`` compose service). State is in memory.

Besides the QPay API it has ``/_sim/...`` endpoints for demos and tests: pay an invoice (optionally sending the
callback several times, like QPay retries do), fail it, slow down or fail the next calls, drop callbacks. It never
talks to a bank.

What it copies from QPay as our production integrations (Enlighten, Toktok) see it:
- ``expires_in`` and ``refresh_expires_in`` are Unix timestamps, not lifetimes.
- The callback is a GET to the merchant's ``callback_url`` (its own query kept) with ``qpay_payment_id`` added.
- A callback can be lost; merchants re-check unpaid invoices with ``payment/check`` on a timer.
- ``GET /v2/payment/{payment_id}`` describes one payment; amounts are decimal strings ("180000.00").
- The invoice lists one deeplink per bank app.

Where it differs on purpose, for demos: ``qr_text``, ``qPay_shortUrl`` and every deeplink open the "Sim Bank" page
(``/_sim/bank/{invoice_id}``), so scanning the QR with a phone camera pays the invoice like a bank app would. Set
``QPAY_SIM_PUBLIC_URL`` to an address the phone can reach. ``qr_image`` is not a real PNG.

A guess about real QPay (so our code must not depend on it): a repeated ``sender_invoice_no`` returns the existing
invoice.
"""

import base64
import contextlib
import html
import os
import secrets
import threading
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Annotated, Any

import httpx
from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

USERNAME = os.environ.get("QPAY_SIM_USERNAME", "sim_merchant")
PASSWORD = os.environ.get("QPAY_SIM_PASSWORD", "sim_password")
# Where a browser or phone reaches this simulator (QR codes and deeplinks point here)
PUBLIC_URL = os.environ.get("QPAY_SIM_PUBLIC_URL", "http://localhost:8010").rstrip("/")
TOKEN_TTL = 3600
REFRESH_TTL = 86400

# The bank apps QPay lists on an invoice; in the simulator each opens the Sim Bank page
BANK_APPS = [
    ("qpay", "qPay wallet", "qPay хэтэвч"),
    ("khanbank", "Khan bank", "Хаан банк"),
    ("statebank", "State bank", "Төрийн банк"),
    ("tdbbank", "Trade and Development bank", "Худалдаа хөгжлийн банк"),
    ("golomtbank", "Golomt bank", "Голомт банк"),
    ("xacbank", "Xac bank", "Хас банк"),
]


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
    wallet: str = "Sim Bank"
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
    callback_delay_ms: int = 0  # QPay calls back a moment after the bank confirms
    callbacks_sent: list[str] = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)


state = State()
app = FastAPI(title="QPay Merchant V2 simulator", docs_url="/_sim/docs", openapi_url="/_sim/openapi.json")
# Demo only: the web app's "Pay with Sim Bank" button calls /_sim from the browser. Real QPay has no such endpoint.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST"], allow_headers=["*"])


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
    # Like QPay: the expiries are Unix timestamps
    return {
        "token_type": "bearer",
        "access_token": access,
        "expires_in": int(now + TOKEN_TTL),
        "refresh_token": refresh,
        "refresh_expires_in": int(now + REFRESH_TTL),
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


def _bank_url(invoice_id: str, app_id: str | None = None) -> str:
    return f"{PUBLIC_URL}/_sim/bank/{invoice_id}" + (f"?app={app_id}" if app_id else "")


def _invoice_out(inv: Invoice) -> dict[str, Any]:
    qr_text = _bank_url(inv.invoice_id)  # a phone camera opens the Sim Bank page
    return {
        "invoice_id": inv.invoice_id,
        "qr_text": qr_text,
        "qr_image": base64.b64encode(qr_text.encode()).decode(),  # not a real PNG; the UI can render qr_text
        "qPay_shortUrl": qr_text,
        "urls": [
            {"name": name, "description": description, "logo": "", "link": _bank_url(inv.invoice_id, app_id)}
            for app_id, name, description in BANK_APPS
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


def _money(amount: int) -> str:
    return f"{amount}.00"


def _payment_out(p: Payment) -> dict[str, Any]:
    return {
        "payment_id": p.payment_id,
        "payment_status": p.status,
        "payment_fee": "0.00",
        "payment_amount": _money(p.amount),
        "payment_currency": "MNT",
        "payment_date": p.date,
        "payment_wallet": p.wallet,
        "payment_type": p.payment_type,
        "transaction_type": p.payment_type,
        "object_type": "INVOICE",
        "object_id": p.invoice_id,
    }


@app.post("/v2/payment/check")
def check_payment(body: CheckIn, _: Auth) -> dict[str, Any]:
    if body.object_type != "INVOICE":
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "only INVOICE is simulated")
    inv = _get_invoice(body.object_id)
    rows = [state.payments[p] for p in inv.payment_ids]
    return {
        "count": len(rows),
        "paid_amount": sum(p.amount for p in rows if p.status == "PAID"),
        "rows": [_payment_out(p) for p in rows],
    }


@app.get("/v2/payment/{payment_id}")
def get_payment(payment_id: str, _: Auth) -> dict[str, Any]:
    pay = state.payments.get(payment_id)
    if pay is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "PAYMENT_NOTFOUND")
    return _payment_out(pay)


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


def _send_callbacks(url: str, payment_id: str, times: int) -> None:
    if state.callback_delay_ms:
        time.sleep(state.callback_delay_ms / 1000)
    for _ in range(times):
        # Like QPay: a GET to the merchant's own URL, its query kept, with qpay_payment_id added
        target = httpx.URL(url).copy_merge_params({"qpay_payment_id": payment_id})
        state.callbacks_sent.append(str(target))
        # A callback that fails is simply lost; the merchant must re-check unpaid invoices itself
        with contextlib.suppress(httpx.HTTPError):
            httpx.get(target, timeout=5)


@app.post("/_sim/invoices/{invoice_id}/pay")
def sim_pay(
    invoice_id: str,
    background: BackgroundTasks,
    amount: Annotated[int | None, Query(description="default: the invoice amount")] = None,
    method: Annotated[str, Query(pattern="^(P2P|CARD)$")] = "P2P",
    callbacks: Annotated[int, Query(ge=0, le=5, description="times to send the callback")] = 1,
    app_id: Annotated[str | None, Query(alias="app", description="the bank app that paid")] = None,
) -> dict[str, Any]:
    wallet = next((desc for a, _, desc in BANK_APPS if a == app_id), "Sim Bank")
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
            wallet=wallet,
        )
        state.payments[pay.payment_id] = pay
        inv.payment_ids.append(pay.payment_id)
        if pay.amount >= inv.amount:
            inv.status = "PAID"
    if state.send_callbacks and callbacks:
        background.add_task(_send_callbacks, inv.callback_url, pay.payment_id, callbacks)
    return {"payment_id": pay.payment_id, "invoice_status": inv.status}


@app.post("/_sim/invoices/{invoice_id}/fail")
def sim_fail(invoice_id: str) -> dict[str, Any]:
    with state.lock:
        inv = _get_invoice(invoice_id)
        pay = Payment(f"sim_pay_{secrets.token_hex(8)}", invoice_id, inv.amount, "FAILED", "CARD")
        state.payments[pay.payment_id] = pay
        inv.payment_ids.append(pay.payment_id)
    return {"payment_id": pay.payment_id, "payment_status": "FAILED"}


_BANK_PAGE = """<!doctype html>
<html lang="mn"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sim Bank</title>
<style>
:root{color-scheme:light dark;--bg:#f4f5f7;--card:#fff;--ink:#14171c;--muted:#5b6370;--accent:#0b6b4f;
--line:#dde1e6}
@media (prefers-color-scheme:dark){:root{--bg:#101215;--card:#1a1d22;--ink:#eef0f3;--muted:#9aa3ae;--line:#2b3038}}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.45 system-ui,sans-serif}
main{max-width:420px;margin:0 auto;padding:24px 16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:20px}
.tag{font-size:12px;color:var(--muted);letter-spacing:.04em;text-transform:uppercase}
.amount{font-size:32px;font-weight:700;margin:6px 0 2px}
.muted{color:var(--muted);font-size:14px}
button{width:100%;padding:14px;border-radius:10px;border:0;font-size:16px;font-weight:600;margin-top:12px;cursor:pointer}
.pay{background:var(--accent);color:#fff}
.decline{background:transparent;color:var(--muted);border:1px solid var(--line)}
button:disabled{opacity:.5;cursor:default}
#result{margin-top:16px;font-weight:600}
</style></head><body><main>
<p class="tag">Sim Bank · {wallet} · симулятор, жинхэнэ мөнгө шилжихгүй</p>
<div class="card">
  <div class="muted">{description}</div>
  <div class="amount">{amount} ₮</div>
  <div class="muted">Нэхэмжлэх {invoice_id} · {status}</div>
  <button class="pay" id="pay" {disabled}>Төлөх</button>
  <button class="decline" id="decline" {disabled}>Татгалзах</button>
  <div id="result" role="status"></div>
</div>
</main>
<script>
const base = location.pathname.replace('/_sim/bank/', '/_sim/invoices/');
const app = new URLSearchParams(location.search).get('app') || '';
const result = document.getElementById('result');
async function act(path, done) {
  document.querySelectorAll('button').forEach(b => (b.disabled = true));
  const res = await fetch(base + path, { method: 'POST' });
  const body = await res.json().catch(() => ({}));
  result.textContent = res.ok ? done : 'Алдаа: ' + (body.detail || res.status);
}
document.getElementById('pay').onclick = () =>
  act('/pay' + (app ? '?app=' + encodeURIComponent(app) : ''), 'Гүйлгээ амжилттай. Апп руугаа буцна уу.');
document.getElementById('decline').onclick = () => act('/fail', 'Гүйлгээ цуцлагдлаа.');
</script></body></html>"""


@app.get("/_sim/bank/{invoice_id}", response_class=HTMLResponse)
def sim_bank_page(invoice_id: str, app_id: Annotated[str | None, Query(alias="app")] = None) -> str:
    """What a bank app shows after scanning the QR: the amount, then Pay or Decline."""
    inv = _get_invoice(invoice_id)
    wallet = next((desc for a, _, desc in BANK_APPS if a == app_id), "Sim Bank")
    fields = {
        "wallet": wallet,
        "description": inv.description,
        "amount": f"{inv.amount:,}",
        "invoice_id": inv.invoice_id,
        "status": {"OPEN": "төлөгдөөгүй", "PAID": "төлөгдсөн", "CANCELLED": "цуцлагдсан"}[inv.status],
    }
    page = _BANK_PAGE.replace("{disabled}", "" if inv.status == "OPEN" else "disabled")
    for key, value in fields.items():
        page = page.replace("{" + key + "}", html.escape(value))
    return page


class SimConfig(BaseModel):
    latency_ms: int | None = Field(default=None, ge=0, le=30000)
    fail_next: int | None = Field(default=None, ge=0, le=100)
    send_callbacks: bool | None = None
    callback_delay_ms: int | None = Field(default=None, ge=0, le=30000)


@app.post("/_sim/config")
def sim_config(body: SimConfig) -> dict[str, Any]:
    with state.lock:
        for key, value in body.model_dump(exclude_none=True).items():
            setattr(state, key, value)
        return {
            "latency_ms": state.latency_ms,
            "fail_next": state.fail_next,
            "send_callbacks": state.send_callbacks,
            "callback_delay_ms": state.callback_delay_ms,
        }


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
