"""Unit tests for password hashing, JWT creation, and auth dependencies (no database)."""

import time
from datetime import timedelta

import pytest
from fastapi import HTTPException
from jose import jwt

import app.core.auth as core_auth_module
from app.core.auth import _create_token, create_access_token
from app.core.config import settings
from app.core.security import get_password_hash, verify_password
from app.v1.deps import get_current_user


def test_password_hash_roundtrip():
    hashed = get_password_hash("super-secret")
    assert hashed != "super-secret"
    assert verify_password("super-secret", hashed)
    assert not verify_password("wrong-password", hashed)


def test_password_hash_is_salted():
    # Two hashes of the same password must differ (random per-hash salt).
    assert get_password_hash("same") != get_password_hash("same")


def test_access_token_contains_expected_claims():
    token = create_access_token(sub="user@example.com")
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.ALGORITHM])

    assert payload["sub"] == "user@example.com"
    assert payload["type"] == "access_token"
    assert "exp" in payload
    assert "iat" in payload
    assert payload["jti"]


def test_expired_token_is_rejected():
    token = create_access_token(sub="user@example.com", expires_delta=timedelta(minutes=-1))
    with pytest.raises(jwt.ExpiredSignatureError):
        jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.ALGORITHM])


def test_get_current_user_rejects_non_access_token():
    # A non-access token must be rejected before any database lookup happens.
    bad_token = _create_token(token_type="refresh_token", lifetime=timedelta(minutes=5), sub="user@example.com")
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(db=None, token=bad_token)
    assert exc_info.value.status_code == 401


def test_get_current_user_rejects_garbage_token():
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(db=None, token="not-a-jwt")
    assert exc_info.value.status_code == 401


def _craft_token(claims: dict) -> str:
    """Sign an arbitrary payload with the real secret (simulates a leaked-secret attacker)."""
    return jwt.encode(claims, settings.JWT_SECRET, algorithm=settings.ALGORITHM)


def test_get_current_user_rejects_token_without_exp():
    token = _craft_token({"type": "access_token", "sub": "user@example.com", "jti": "x"})
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(db=None, token=token)
    assert exc_info.value.status_code == 401


def test_get_current_user_rejects_token_without_sub():
    token = _craft_token({"type": "access_token", "exp": int(time.time()) + 300, "jti": "x"})
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(db=None, token=token)
    assert exc_info.value.status_code == 401


def test_authenticate_user_hashes_dummy_password_when_user_not_found(db, monkeypatch):
    # Both the "unknown email" and "wrong password" paths must call verify_password
    # so their timing is equivalent, preventing email enumeration via response timing.
    calls = []
    original_verify = core_auth_module.verify_password

    def spy(plain: str, hashed: str) -> bool:
        calls.append(hashed)
        return original_verify(plain, hashed)

    monkeypatch.setattr(core_auth_module, "verify_password", spy)

    result = core_auth_module.authenticate_user(db=db, email="nobody-xyz@example.com", password="whatever")

    assert result is None
    assert calls == [core_auth_module._DUMMY_HASH]


def test_get_current_user_rejects_token_without_jti():
    token = _craft_token({"type": "access_token", "sub": "user@example.com", "exp": int(time.time()) + 300})
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(db=None, token=token)
    assert exc_info.value.status_code == 401
