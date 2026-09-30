"""Shared builders for payment tests: a user key, a merchant-signed checkout, a user-signed Payment Mandate."""

from datetime import UTC, datetime, timedelta

from app import ap2
from app.ap2.checkout import checkout_claims
from app.core.config import settings
from app.core.keys import merchant_key, merchant_kid
from app.db.outbox import iso

NOW = datetime(2026, 10, 1, 8, 0, tzinfo=UTC)
USER = "user_jamba"
TRIP = "trip_jamba_east"
LINE = {
    "kind": "stay",
    "ref_id": "stay_khatgal_camp_blue_pearl",
    "qty": 1,
    "unit_price_mnt": 180000,
    "total_mnt": 180000,
    "label": {"mn": "Хөх сувд бааз", "en": "Blue Pearl Ger Camp"},
    "date": "2026-10-03",
    "unit_type": "ger",
}


def insert_checkout(db, checkout_id="chk_1", total_mnt=180000, user_id=USER, expires=NOW + timedelta(minutes=15)):
    line = {**LINE, "unit_price_mnt": total_mnt, "total_mnt": total_mnt}
    claims = checkout_claims(
        merchant_id=settings.MERCHANT_ID,
        checkout_id=checkout_id,
        trip_id=TRIP,
        lines=[{k: v for k, v in line.items() if k != "label"}],
        total_mnt=total_mnt,
        iat=int(NOW.timestamp()),
        exp=int(expires.timestamp()),
    )
    token, digest = ap2.sign_checkout(claims, merchant_key(), kid=merchant_kid())
    db["checkouts"].insert_one(
        {
            "_id": checkout_id,
            "trip_id": TRIP,
            "user_id": user_id,
            "lines": [line],
            "total_mnt": total_mnt,
            "currency": "MNT",
            "hold_ids": [],
            "checkout_jwt": token,
            "checkout_hash": digest,
            "status": "open",
            "expires_at": iso(expires),
            "created_at": iso(NOW),
        }
    )
    return token


def payment_mandate(user_key, checkout_jwt, amount_mnt=180000, payee_id=None):
    claims = ap2.payment_mandate_claims(
        checkout_jwt=checkout_jwt,
        payee={"id": payee_id or settings.MERCHANT_ID, "name": "Mongolian Travel Agent"},
        amount_mnt=amount_mnt,
        instrument={"type": "qpay_qr"},
        iat=int(NOW.timestamp()),
        exp=int(NOW.timestamp()) + 600,
    )
    return ap2.sign_mandate(claims, user_key, kid="browser")
