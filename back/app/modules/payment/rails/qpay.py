"""QPay Merchant V2 adapter. The same class drives the real QPay and our simulator (``app.services.qpay_sim``).

Paths and field names follow the Merchant V2 API as used by public client libraries. The refund and e-receipt
paths differ between sources, so they are constructor arguments: confirm them once QPay grants sandbox access
and change only the defaults below.

``verify`` runs when a callback arrives and, because QPay callbacks can be lost, from a slow reconciliation sweep
(once a minute per unpaid invoice, like Toktok's payment cron), never in a tight loop.
"""

import json
import threading
import time
from collections.abc import Callable, Mapping
from typing import Any

import httpx

from app.modules.payment.rails.base import (
    ChargeHandle,
    ChargeStatus,
    InstrumentType,
    RailError,
    RailId,
    WebhookHint,
)

TOKEN_PATH = "/v2/auth/token"
REFRESH_PATH = "/v2/auth/refresh"
INVOICE_PATH = "/v2/invoice"
CHECK_PATH = "/v2/payment/check"
DEFAULT_REFUND = ("DELETE", "/v2/payment/refund/{payment_id}")
DEFAULT_RECEIPT = ("POST", "/v2/ebarimt_v3/create")
TOKEN_MARGIN_SECONDS = 60
EPOCH_THRESHOLD = 1_000_000_000  # a larger expires_in is a timestamp (2001+), not a lifetime


class QPayRail:
    def __init__(
        self,
        *,
        base_url: str,
        username: str,
        password: str,
        invoice_code: str,
        rail_id: RailId = "qpay",
        client: httpx.Client | None = None,
        timeout: float = 10.0,
        refund_endpoint: tuple[str, str] = DEFAULT_REFUND,
        receipt_endpoint: tuple[str, str] = DEFAULT_RECEIPT,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.id: RailId = rail_id
        self._client = client or httpx.Client(base_url=base_url, timeout=timeout)
        self._auth = (username, password)
        self._invoice_code = invoice_code
        self._refund = refund_endpoint
        self._receipt = receipt_endpoint
        self._clock = clock
        self._lock = threading.Lock()
        self._access: str | None = None
        self._access_until = 0.0
        self._refresh: str | None = None
        self._refresh_until = 0.0

    # ------------------------------------------------------------------------- auth

    @staticmethod
    def _lifetime(value: Any) -> float:
        """QPay sends ``expires_in`` as a Unix timestamp; accept a lifetime in seconds too."""
        seconds = float(value or 0)
        return seconds - time.time() if seconds > EPOCH_THRESHOLD else seconds

    def _store(self, data: dict[str, Any]) -> str:
        now = self._clock()
        self._access = data["access_token"]
        self._access_until = now + self._lifetime(data.get("expires_in")) - TOKEN_MARGIN_SECONDS
        self._refresh = data.get("refresh_token")
        self._refresh_until = now + self._lifetime(data.get("refresh_expires_in")) - TOKEN_MARGIN_SECONDS
        return data["access_token"]

    def _token(self, *, force: bool = False) -> str:
        with self._lock:
            now = self._clock()
            if not force and self._access and now < self._access_until:
                return self._access
            if self._refresh and now < self._refresh_until:
                resp = self._client.post(REFRESH_PATH, headers={"Authorization": f"Bearer {self._refresh}"})
                if resp.status_code == 200:
                    return self._store(resp.json())
            resp = self._client.post(TOKEN_PATH, auth=self._auth)
            if resp.status_code != 200:
                raise RailError("QPay auth failed", status_code=resp.status_code)
            return self._store(resp.json())

    def _call(self, method: str, path: str, body: dict[str, Any] | None = None) -> httpx.Response:
        """Send with a bearer token; on 401 get a fresh token once and retry."""
        for attempt in range(2):
            headers = {"Authorization": f"Bearer {self._token(force=attempt > 0)}"}
            try:
                resp = self._client.request(method, path, json=body, headers=headers)
            except httpx.HTTPError as exc:
                raise RailError(f"QPay unreachable: {exc}", retryable=True) from exc
            if resp.status_code != 401:
                break
        if resp.status_code >= 500:
            raise RailError(f"QPay {method} {path} failed", retryable=True, status_code=resp.status_code)
        if resp.status_code >= 400:
            raise RailError(f"QPay {method} {path} refused: {resp.text[:200]}", status_code=resp.status_code)
        return resp

    # ------------------------------------------------------------------------- rail

    def supports(self, instrument: InstrumentType) -> bool:
        # Card payments also go through the QPay page, but refunds are only automatic for cards
        return instrument in ("qpay_qr", "card")

    def create_charge(self, *, charge_id: str, amount_mnt: int, description: str, callback_url: str) -> ChargeHandle:
        if amount_mnt <= 0:
            raise RailError("amount must be positive")
        data = self._call(
            "POST",
            INVOICE_PATH,
            {
                "invoice_code": self._invoice_code,
                "sender_invoice_no": charge_id,
                "invoice_receiver_code": "terminal",
                "invoice_description": description[:255],
                "amount": amount_mnt,
                "callback_url": callback_url,
            },
        ).json()
        return ChargeHandle(
            provider=self.id,
            provider_ref=data["invoice_id"],
            amount_mnt=amount_mnt,
            qr_text=data.get("qr_text"),
            qr_image=data.get("qr_image"),
            short_url=data.get("qPay_shortUrl"),
            deeplinks=[
                {"name": u.get("name", ""), "logo": u.get("logo", ""), "link": u.get("link", "")}
                for u in data.get("urls") or []
            ],
        )

    def verify(self, provider_ref: str) -> ChargeStatus:
        data = self._call(
            "POST",
            CHECK_PATH,
            {"object_type": "INVOICE", "object_id": provider_ref, "offset": {"page_number": 1, "page_limit": 100}},
        ).json()
        rows = data.get("rows") or []
        paid = [r for r in rows if r.get("payment_status") == "PAID"]
        if paid:
            total = sum(int(float(r.get("payment_amount", 0))) for r in paid)
            return ChargeStatus(state="paid", paid_amount_mnt=total, provider_payment_id=str(paid[0]["payment_id"]))
        if rows and all(r.get("payment_status") == "FAILED" for r in rows):
            return ChargeStatus(state="failed", paid_amount_mnt=0)
        return ChargeStatus(state="pending", paid_amount_mnt=0)

    def cancel(self, provider_ref: str) -> None:
        self._call("DELETE", f"{INVOICE_PATH}/{provider_ref}")

    def refund(self, provider_payment_id: str) -> None:
        """Only card payments can be refunded through QPay; a bank QR payment raises and must be returned by hand."""
        method, path = self._refund
        self._call(method, path.format(payment_id=provider_payment_id), {"callback_url": None, "note": "refund"})

    def parse_webhook(self, query: Mapping[str, str], body: bytes) -> WebhookHint:
        """QPay callbacks are unsigned: read what they claim, then ``verify``. Accepts query or JSON body."""
        claimed: dict[str, Any] = dict(query)
        if body:
            try:
                parsed = json.loads(body)
                if isinstance(parsed, dict):
                    claimed.update(parsed)
            except ValueError:
                pass
        payment_id = claimed.get("payment_id") or claimed.get("qpay_payment_id")
        return WebhookHint(
            provider_ref=claimed.get("invoice_id") or claimed.get("object_id"),
            provider_payment_id=str(payment_id) if payment_id else None,
        )

    def issue_receipt(self, provider_payment_id: str) -> str | None:
        method, path = self._receipt
        data = self._call(method, path, {"payment_id": provider_payment_id, "ebarimt_receiver_type": "CITIZEN"}).json()
        return data.get("id")
