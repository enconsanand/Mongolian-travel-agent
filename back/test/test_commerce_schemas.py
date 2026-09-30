"""Commerce schemas (checkouts, AP2 mandates, holds, payment events, outbox), their validators and indexes."""

import pytest
from pydantic import ValidationError
from pymongo import IndexModel

from app.db.mongo import INDEXES
from app.db.validators import MODELS, json_schema_for
from app.schemas.commerce import COMMERCE_MODELS, CheckoutDoc, HoldDoc, MandateDoc
from app.schemas.travel import DOC_MODELS, PaymentDoc
from app.seeds.mock_seed import load_mock_collections
from test.test_travel_schemas import _walk

NOW = "2026-10-01T08:00:00Z"
LABEL = {"mn": "Хөх сувд бааз", "en": "Blue Pearl Ger Camp"}


def _closed_payment_mandate(**overrides):
    return {
        "_id": "mdt_1",
        "vct": "mandate.payment.1",
        "kind": "payment",
        "form": "closed",
        "trip_id": "trip_jamba_east",
        "user_id": "user_jamba",
        "checkout_id": "chk_1",
        "transaction_id": "hash-of-checkout-jwt",
        "sd_jwt": "header.payload.signature",
        "hash": "hash-of-sd-jwt",
        "signer": "user",
        "key_id": "key_browser_1",
        "status": "received",
        "received_at": NOW,
        **overrides,
    }


def test_commerce_models_are_separate_from_mock_collections():
    # Mock files map 1:1 to DOC_MODELS; commerce collections have no mock file
    assert not set(COMMERCE_MODELS) & set(DOC_MODELS)
    assert set(COMMERCE_MODELS) == {"checkouts", "mandates", "holds", "payment_events", "outbox"}
    assert set(COMMERCE_MODELS) <= set(MODELS)


@pytest.mark.parametrize("collection", sorted(COMMERCE_MODELS))
def test_commerce_validators_are_strict_objects(collection):
    schema = json_schema_for(COMMERCE_MODELS[collection])
    for node in _walk(schema):
        assert "$ref" not in node and "type" not in node and "title" not in node and "const" not in node
    assert schema["bsonType"] == "object"
    assert schema["additionalProperties"] is False
    assert "_id" in schema["required"]


@pytest.mark.parametrize("collection", sorted(COMMERCE_MODELS))
def test_every_commerce_collection_has_an_index(collection):
    assert any(name == collection for name, _, _ in INDEXES)


def test_index_definitions_are_valid_pymongo():
    for _, keys, options in INDEXES:
        IndexModel(keys, **options)


def test_closed_mandate_is_valid():
    MandateDoc.model_validate(_closed_payment_mandate())


@pytest.mark.parametrize(
    "overrides",
    [
        {"vct": "mandate.checkout.1"},  # vct says checkout, kind says payment
        {"form": "open"},  # vct says closed
        {"transaction_id": None},  # a closed mandate must bind to a checkout
        {"signer": "llm"},
        {"status": "approved"},
        {"extra": 1},
    ],
)
def test_bad_mandates_are_rejected(overrides):
    with pytest.raises(ValidationError):
        MandateDoc.model_validate(_closed_payment_mandate(**overrides))


def test_open_mandate_needs_no_transaction_id():
    MandateDoc.model_validate(
        _closed_payment_mandate(vct="mandate.payment.open.1", form="open", transaction_id=None, checkout_id=None)
    )


def test_checkout_needs_a_line_and_a_non_negative_total():
    base = {
        "_id": "chk_1",
        "trip_id": "trip_jamba_east",
        "user_id": "user_jamba",
        "lines": [
            {
                "kind": "stay",
                "ref_id": "stay_khatgal_camp_blue_pearl",
                "qty": 1,
                "unit_price_mnt": 180000,
                "total_mnt": 180000,
                "label": LABEL,
                "date": "2026-10-03",
                "unit_type": "ger",
            }
        ],
        "total_mnt": 180000,
        "hold_ids": ["hold_1"],
        "checkout_jwt": "header.payload.signature",
        "checkout_hash": "hash-of-checkout-jwt",
        "status": "open",
        "expires_at": NOW,
        "created_at": NOW,
    }
    CheckoutDoc.model_validate(base)
    with pytest.raises(ValidationError):
        CheckoutDoc.model_validate({**base, "lines": []})
    with pytest.raises(ValidationError):
        CheckoutDoc.model_validate({**base, "total_mnt": -1})


def test_hold_quantity_is_positive():
    hold = {
        "_id": "hold_1",
        "trip_id": "trip_jamba_east",
        "stay_id": "stay_khatgal_camp_blue_pearl",
        "unit_type": "ger",
        "date": "2026-10-03",
        "qty": 1,
        "status": "held",
        "expires_at": NOW,
        "created_at": NOW,
    }
    HoldDoc.model_validate(hold)
    with pytest.raises(ValidationError):
        HoldDoc.model_validate({**hold, "qty": 0})


def test_payment_accepts_live_rails_and_ap2_links():
    payment = {
        "_id": "pay_1",
        "user_id": "user_jamba",
        "trip_id": "trip_jamba_east",
        "booking_ids": ["booking_1"],
        "amount_mnt": 180000,
        "method": {"type": "qpay", "invoice_id": "inv_1"},
        "provider": "qpay",
        "provider_ref": "inv_1",
        "status": "awaiting_payment",
        "status_history": [{"status": "awaiting_payment", "at": NOW, "actor": "system"}],
        "consent": {"approved_by_user": True, "max_amount_mnt": 200000, "approved_at": NOW},
        "idempotency_key": "trip_jamba_east:invoice",
        "is_sandbox": True,
        "checkout_id": "chk_1",
        "payment_mandate_id": "mdt_1",
        "transaction_id": "hash-of-checkout-jwt",
    }
    PaymentDoc.model_validate(payment)
    with pytest.raises(ValidationError):
        PaymentDoc.model_validate({**payment, "provider": "stripe_live"})


def test_reseed_keeps_commerce_data_and_reset_empties_it(db):
    load_mock_collections(db, real_server=False)
    db["checkouts"].insert_one({"_id": "chk_real"})
    load_mock_collections(db, real_server=False)
    assert db["checkouts"].find_one({"_id": "chk_real"}) is not None

    load_mock_collections(db, real_server=False, reset=True)
    assert db["checkouts"].count_documents({}) == 0
