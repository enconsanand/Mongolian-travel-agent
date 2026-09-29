"""The seeder loads data/mock into MongoDB and makes the mock travellers able to log in."""

import json
import shutil
from pathlib import Path

import pytest

from app import crud
from app.core.config import settings
from app.core.security import verify_password
from app.seeds.mock_seed import load_mock_collections, upsert_mock_users


def _load(db, **kwargs):
    load_mock_collections(db, real_server=False, **kwargs)


def test_load_mock_collections_fills_every_collection(db):
    _load(db)

    names = set(db.list_collection_names())
    assert {"regions", "places", "routes", "stays", "events", "payments", "shared_rides"} <= names
    assert db["regions"].count_documents({}) == 4
    assert db["stays"].count_documents({"region": "west"}) > 0
    assert "image_pool" not in names
    assert not any(n.startswith(("translations", "_seed_tmp_")) for n in names)


def test_reseeding_replaces_instead_of_duplicating(db):
    _load(db)
    first = db["stays"].count_documents({})
    _load(db)
    assert db["stays"].count_documents({}) == first


def test_mock_users_can_log_in_and_keep_their_password(db):
    upsert_mock_users(db, password="seed-password-1")
    user = crud.user.get_by_email(db=db, email="anand@nashatech.com")
    assert user is not None
    assert verify_password("seed-password-1", user.hashed_password)
    assert user.payment_methods[0]["is_test_card"] is True

    # A second run must not reset an existing password
    upsert_mock_users(db, password="another-password")
    user = crud.user.get_by_email(db=db, email="anand@nashatech.com")
    assert verify_password("seed-password-1", user.hashed_password)
    assert db["users"].count_documents({}) == 3


def test_reseed_keeps_runtime_data_and_inventory(db):
    _load(db)
    db["trips"].insert_one({"_id": "trip_real_user", "title": {"mn": "Жинхэнэ", "en": "Real"}})
    db["payments"].update_one({"_id": "pay_jamba_001"}, {"$set": {"status": "paid"}})
    row = {"stay_id": "stay_khatgal_camp_blue_pearl", "date": "2026-10-03", "unit_type": "ger"}
    db["stay_availability"].update_one(row, {"$set": {"available": 0}})

    _load(db)

    assert db["trips"].find_one({"_id": "trip_real_user"}) is not None
    assert db["payments"].find_one({"_id": "pay_jamba_001"})["status"] == "paid"  # not reset to the demo value
    assert db["stay_availability"].find_one(row)["available"] == 0  # a booked unit stays booked


def test_reset_replaces_runtime_data(db):
    _load(db)
    db["trips"].insert_one({"_id": "trip_real_user"})
    _load(db, reset=True)
    assert db["trips"].find_one({"_id": "trip_real_user"}) is None
    assert db["trips"].find_one({"_id": "trip_jamba_east"}) is not None


def test_invalid_mock_file_changes_nothing(db, tmp_path):
    _load(db)
    stays_before = db["stays"].count_documents({})
    for path in Path(settings.MOCK_DATA_DIR).glob("*.json"):
        shutil.copy(path, tmp_path / path.name)
    places = json.loads((tmp_path / "places.json").read_text(encoding="utf-8"))
    places[0]["fuel_available"] = "yes"  # lax mode would coerce this; strict must refuse
    (tmp_path / "places.json").write_text(json.dumps(places), encoding="utf-8")

    with pytest.raises(ValueError):
        _load(db, data_dir=str(tmp_path))
    assert db["stays"].count_documents({}) == stays_before


def test_reseed_keeps_account_fields(db):
    upsert_mock_users(db, password="seed-password-1")
    db["users"].update_one({"email": "anand@nashatech.com"}, {"$set": {"is_active": False}})
    created = db["users"].find_one({"email": "anand@nashatech.com"})["created_at"]

    upsert_mock_users(db, password="seed-password-1")

    user = db["users"].find_one({"email": "anand@nashatech.com"})
    assert user["is_active"] is False
    assert user["created_at"] == created
    assert user["email"] == "anand@nashatech.com"


def test_user_without_login_fields_is_not_a_500(db):
    # e.g. users.json loaded with a plain mongoimport: profile only, no password hash
    db["users"].insert_one({"_id": "user_x", "email": "x@example.com", "first_name": "X"})
    assert crud.user.get_by_email(db=db, email="x@example.com") is None
