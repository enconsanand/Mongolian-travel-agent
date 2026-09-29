"""CRUD tests for users against a transactionally-isolated database session."""

import uuid

import pytest

from app import crud, schemas
from app.core.security import verify_password


def _unique_email(prefix: str = "user") -> str:
    return f"{prefix}-{uuid.uuid4().hex}@example.com"


def _make_user_in(email: str | None = None, password: str = "password1") -> schemas.UserCreate:
    return schemas.UserCreate(
        email=email or _unique_email(),
        first_name="Test",
        last_name="User",
        password=password,
    )


def test_create_user_hashes_password_and_assigns_id(db):
    user = crud.user.create(db=db, obj_in=_make_user_in(password="password1"))

    assert user.id is not None
    assert user.created_at is not None
    assert user.hashed_password != "password1"
    assert verify_password("password1", user.hashed_password)


def test_create_user_honors_is_active_flag(db):
    obj_in = schemas.UserCreate(
        email=_unique_email("inactive"),
        first_name="In",
        last_name="Active",
        password="password1",
        is_active=False,
    )
    user = crud.user.create(db=db, obj_in=obj_in)
    assert user.is_active is False


def test_get_by_email_is_case_insensitive(db):
    email = _unique_email("MixedCase")
    created = crud.user.create(db=db, obj_in=_make_user_in(email=email))

    found = crud.user.get_by_email(db=db, email=email.lower())

    assert found is not None
    assert found.id == created.id


def test_get_by_email_returns_none_when_missing(db):
    assert crud.user.get_by_email(db=db, email=_unique_email("missing")) is None


def test_get_returns_persisted_user(db):
    created = crud.user.create(db=db, obj_in=_make_user_in())
    assert crud.user.get(db=db, id=created.id).id == created.id


def test_update_user_rehashes_password(db):
    user = crud.user.create(db=db, obj_in=_make_user_in(password="password1"))
    old_hash = user.hashed_password

    updated = crud.user.update(db=db, db_obj=user, obj_in={"password": "newpassword2"})

    assert updated.hashed_password != old_hash
    assert verify_password("newpassword2", updated.hashed_password)


def test_update_user_changes_simple_field(db):
    user = crud.user.create(db=db, obj_in=_make_user_in())
    updated = crud.user.update(db=db, db_obj=user, obj_in={"first_name": "Renamed"})
    assert updated.first_name == "Renamed"


def test_remove_user(db):
    user = crud.user.create(db=db, obj_in=_make_user_in())
    crud.user.remove(db=db, id=user.id)
    assert crud.user.get(db=db, id=user.id) is None


def test_remove_missing_user_raises(db):
    with pytest.raises(ValueError):
        crud.user.remove(db=db, id=uuid.uuid4())


def test_count_increases_after_create(db):
    before = crud.user.count(db=db)
    crud.user.create(db=db, obj_in=_make_user_in())
    assert crud.user.count(db=db) == before + 1
