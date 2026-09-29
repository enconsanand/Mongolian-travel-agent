"""End-to-end tests for the auth endpoints using FastAPI's TestClient."""

import uuid

import redis.asyncio as aioredis

from app import crud, schemas
from app.core.config import settings
from app.core.token_denylist import TokenDenylistUnavailable
from app.core.token_denylist import token_denylist as denylist_instance
from app.models.user import User
from app.v1.common import auth as auth_module
from app.v1.common.auth import _subnet_for

LOGIN_URL = "/api/v1/auth/login"
LOGOUT_URL = "/api/v1/auth/logout"
ME_URL = "/api/v1/auth/me"


def _create_user(db, password: str = "password1", is_active: bool = True) -> User:
    payload = schemas.UserCreate(
        email=f"api-{uuid.uuid4().hex}@example.com",
        first_name="Api",
        last_name="User",
        password=password,
        is_active=is_active,
    )
    user = crud.user.create(db=db, obj_in=payload)
    db.flush()
    return user


def test_login_success_returns_bearer_token(client, db):
    user = _create_user(db, password="password1")

    response = client.post(LOGIN_URL, data={"username": user.email, "password": "password1"})

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_wrong_password_is_unauthorized(client, db):
    user = _create_user(db, password="password1")

    response = client.post(LOGIN_URL, data={"username": user.email, "password": "wrong-password"})

    assert response.status_code == 401


def test_login_unknown_user_is_unauthorized(client, db):
    response = client.post(LOGIN_URL, data={"username": "nobody@example.com", "password": "password1"})
    assert response.status_code == 401


def test_login_inactive_user_gets_same_401_as_bad_credentials(client, db):
    # Inactive accounts must be indistinguishable from wrong credentials (anti-enumeration)
    user = _create_user(db, password="password1", is_active=False)

    response = client.post(LOGIN_URL, data={"username": user.email, "password": "password1"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


def test_me_returns_current_user_with_valid_token(client, db):
    user = _create_user(db, password="password1")
    login = client.post(LOGIN_URL, data={"username": user.email, "password": "password1"})
    token = login.json()["access_token"]

    response = client.get(ME_URL, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["email"] == user.email


def test_me_requires_authentication(client):
    assert client.get(ME_URL).status_code == 401


def test_logout_revokes_token(client, db):
    user = _create_user(db, password="password1")
    login = client.post(LOGIN_URL, data={"username": user.email, "password": "password1"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    assert client.get(ME_URL, headers=headers).status_code == 200
    assert client.post(LOGOUT_URL, headers=headers).status_code == 204
    # The same token must be rejected after logout
    assert client.get(ME_URL, headers=headers).status_code == 401


def test_logout_requires_authentication(client):
    assert client.post(LOGOUT_URL).status_code == 401


def test_logout_does_not_affect_other_sessions(client, db):
    user = _create_user(db, password="password1")
    first = client.post(LOGIN_URL, data={"username": user.email, "password": "password1"})
    second = client.post(LOGIN_URL, data={"username": user.email, "password": "password1"})
    first_headers = {"Authorization": f"Bearer {first.json()['access_token']}"}
    second_headers = {"Authorization": f"Bearer {second.json()['access_token']}"}

    assert client.post(LOGOUT_URL, headers=first_headers).status_code == 204

    # Only the revoked token is invalidated; each token has its own jti
    assert client.get(ME_URL, headers=first_headers).status_code == 401
    assert client.get(ME_URL, headers=second_headers).status_code == 200


def test_login_locks_account_after_repeated_failures(client, db, monkeypatch):
    monkeypatch.setattr(settings, "LOGIN_MAX_FAILED_ATTEMPTS", 3)
    user = _create_user(db, password="password1")

    for _ in range(3):
        response = client.post(LOGIN_URL, data={"username": user.email, "password": "wrong"})
        assert response.status_code == 401

    # Locked out even with the correct password; keyed on the account, not the IP
    response = client.post(LOGIN_URL, data={"username": user.email, "password": "password1"})
    assert response.status_code == 429
    assert response.headers["Retry-After"] == str(settings.LOGIN_FAILED_ATTEMPTS_WINDOW_SECONDS)

    # Other accounts are unaffected
    other = _create_user(db, password="password1")
    response = client.post(LOGIN_URL, data={"username": other.email, "password": "password1"})
    assert response.status_code == 200


def test_successful_logins_do_not_trip_lockout(client, db, monkeypatch):
    monkeypatch.setattr(settings, "LOGIN_MAX_FAILED_ATTEMPTS", 2)
    user = _create_user(db, password="password1")

    for _ in range(3):
        response = client.post(LOGIN_URL, data={"username": user.email, "password": "password1"})
        assert response.status_code == 200


def test_subnet_for_ipv4_groups_addresses_into_a_slash_24():
    assert _subnet_for("203.0.113.55") == "203.0.113.0/24"
    assert _subnet_for("203.0.113.200") == "203.0.113.0/24"


def test_subnet_for_ipv6_groups_addresses_into_a_slash_64():
    assert _subnet_for("2001:db8::1") == "2001:db8::/64"


def test_subnet_for_invalid_ip_returns_raw_value():
    assert _subnet_for("testclient") == "testclient"


def test_lockout_is_scoped_to_attacker_subnet_not_the_account(client, db, monkeypatch):
    # Distributed brute-force across a single subnet must not lock out a
    # legitimate owner logging in from a different network.
    monkeypatch.setattr(settings, "TRUST_PROXY_HEADERS", True)
    monkeypatch.setattr(settings, "LOGIN_MAX_FAILED_ATTEMPTS", 3)
    user = _create_user(db, password="password1")

    attacker_headers = {"X-Forwarded-For": "203.0.113.10"}
    for ip in ["203.0.113.11", "203.0.113.12", "203.0.113.13"]:
        response = client.post(
            LOGIN_URL,
            data={"username": user.email, "password": "wrong"},
            headers={"X-Forwarded-For": ip},
        )
        assert response.status_code == 401

    # Attacker's own subnet is now locked out, even with the correct password
    response = client.post(LOGIN_URL, data={"username": user.email, "password": "password1"}, headers=attacker_headers)
    assert response.status_code == 429

    # A legitimate owner on an unrelated subnet can still log in
    legit_headers = {"X-Forwarded-For": "198.51.100.7"}
    response = client.post(LOGIN_URL, data={"username": user.email, "password": "password1"}, headers=legit_headers)
    assert response.status_code == 200


def test_login_returns_503_when_lockout_backend_unavailable(client, db, monkeypatch):
    async def _raise(*args, **kwargs):
        raise aioredis.RedisError("boom")

    monkeypatch.setattr(auth_module._login_failures, "count", _raise)
    user = _create_user(db, password="password1")

    response = client.post(LOGIN_URL, data={"username": user.email, "password": "password1"})
    assert response.status_code == 503


def test_me_returns_503_when_denylist_unavailable(client, db, monkeypatch):
    user = _create_user(db, password="password1")
    login = client.post(LOGIN_URL, data={"username": user.email, "password": "password1"})
    token = login.json()["access_token"]

    def _raise(*args, **kwargs):
        raise TokenDenylistUnavailable("boom")

    monkeypatch.setattr(denylist_instance, "contains", _raise)

    response = client.get(ME_URL, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 503


def test_logout_returns_503_when_denylist_unavailable(client, db, monkeypatch):
    user = _create_user(db, password="password1")
    login = client.post(LOGIN_URL, data={"username": user.email, "password": "password1"})
    token = login.json()["access_token"]

    def _raise(*args, **kwargs):
        raise TokenDenylistUnavailable("boom")

    monkeypatch.setattr(denylist_instance, "add", _raise)

    response = client.post(LOGOUT_URL, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 503


def test_logout_ceils_subsecond_ttl_before_denylisting(client, monkeypatch):
    fixed_now = 1_000_000.0
    monkeypatch.setattr(auth_module.time, "time", lambda: fixed_now)
    monkeypatch.setattr(
        auth_module, "decode_access_token", lambda token: {"exp": fixed_now + 0.4, "jti": "ceil-test-jti"}
    )

    recorded = {}

    def _add(jti, ttl):
        recorded["jti"] = jti
        recorded["ttl"] = ttl

    monkeypatch.setattr(auth_module.token_denylist, "add", _add)

    response = client.post(LOGOUT_URL, headers={"Authorization": "Bearer whatever"})

    assert response.status_code == 204
    # int(0.4) would be 0 and skip denylisting entirely; ceil(0.4) is 1
    assert recorded == {"jti": "ceil-test-jti", "ttl": 1}
