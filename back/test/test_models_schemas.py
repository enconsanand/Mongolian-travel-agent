"""Unit tests for the User model and Pydantic schemas (no database required)."""

import pytest
from pydantic import ValidationError

from app.models.user import User
from app.schemas.user import UserCreate, UserResponse


def _build_user(**overrides) -> User:
    data = {
        "email": "user@example.com",
        "first_name": "Jane",
        "last_name": "Doe",
        "hashed_password": "x",
    }
    data.update(overrides)
    return User(**data)


def test_email_is_normalized_on_assignment():
    user = _build_user(email="  Foo@BAR.com ")
    assert user.email == "foo@bar.com"


def test_full_name_property():
    user = _build_user(first_name="Jane", last_name="Doe")
    assert user.full_name == "Jane Doe"


def test_user_create_accepts_valid_payload():
    obj = UserCreate(
        email="valid@example.com",
        first_name="A",
        last_name="B",
        password="password1",
    )
    assert obj.email == "valid@example.com"
    assert obj.password == "password1"


@pytest.mark.parametrize("password", ["short", "x" * 7])
def test_user_create_rejects_short_password(password):
    with pytest.raises(ValidationError):
        UserCreate(email="a@b.com", first_name="A", last_name="B", password=password)


def test_user_create_rejects_password_over_bcrypt_limit():
    with pytest.raises(ValidationError):
        UserCreate(email="a@b.com", first_name="A", last_name="B", password="x" * 73)


def test_user_create_rejects_invalid_email():
    with pytest.raises(ValidationError):
        UserCreate(email="not-an-email", first_name="A", last_name="B", password="password1")


def test_user_create_rejects_blank_names():
    with pytest.raises(ValidationError):
        UserCreate(email="a@b.com", first_name="", last_name="B", password="password1")


def test_user_response_excludes_password():
    # UserResponse has no password/hashed_password field, so it can never leak one.
    assert "password" not in UserResponse.model_fields
    assert "hashed_password" not in UserResponse.model_fields
