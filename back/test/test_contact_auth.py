"""The demo flow produces real, revocable sessions for email and phone-only accounts."""

from datetime import UTC, datetime, timedelta

import pytest

from app.core.config import AppENV, settings

BASE = "/api/v1/auth/code"


def request(client, contact="new@example.com", purpose="register", **extra):
    return client.post(f"{BASE}/request", json={"contact": contact, "purpose": purpose, "name": "Traveller", **extra})


def verify(client, challenge, code="000000"):
    return client.post(f"{BASE}/verify", json={"challenge_id": challenge, "code": code})


@pytest.mark.parametrize(
    "contact,field,normalized",
    [
        (" New@Example.com ", "email", "new@example.com"),
        ("9911 2233", "phone", "+97699112233"),
        ("+976 8811-2233", "phone", "+97688112233"),
    ],
)
def test_register_login_profile_and_logout(client, contact, field, normalized):
    issued = request(client, contact).json()
    assert issued["contact"] == normalized
    result = verify(client, issued["challenge_id"])
    assert result.status_code == 200, result.text
    headers = {"Authorization": f"Bearer {result.json()['access_token']}"}
    profile = client.get("/api/v1/auth/me", headers=headers).json()
    assert profile[field] == normalized and profile["first_name"] == "Traveller"
    assert profile["email"] is None if field == "phone" else profile["phone"] is None
    assert "hashed_password" not in profile
    assert verify(client, issued["challenge_id"]).status_code == 400
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 204
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
    login = request(client, contact, "login").json()
    assert verify(client, login["challenge_id"], "123456").status_code == 200


def test_multiple_phone_only_accounts_and_duplicate_contact(client):
    for phone in ("99112233", "88112233"):
        assert verify(client, request(client, phone).json()["challenge_id"]).status_code == 200
    assert request(client, "+97699112233").json()["detail"]["code"] == "account_exists"
    assert request(client, "missing@example.com", "login").json()["detail"]["code"] == "registration_required"


@pytest.mark.parametrize("code", ["", "12345", "1234567", "abcdef", "１２３４５６", "12345\n"])
def test_invalid_codes_do_not_consume_challenge(client, code):
    challenge = request(client).json()["challenge_id"]
    assert verify(client, challenge, code).status_code == 422
    assert verify(client, challenge).status_code == 200


@pytest.mark.parametrize("contact", ["bad-email", "123", "+11234567890", "abc99112233"])
def test_invalid_contacts(client, contact):
    assert request(client, contact).status_code == 422


def test_expiry_and_resend(client, db):
    challenge = request(client).json()["challenge_id"]
    assert request(client, previous_challenge=challenge).status_code == 429
    db["auth_challenges"].update_one(
        {"_id": challenge},
        {
            "$set": {
                "created_at": datetime.now(UTC) - timedelta(minutes=6),
                "expires_at": datetime.now(UTC) - timedelta(minutes=1),
            }
        },
    )
    assert verify(client, challenge).status_code == 400
    replacement = request(client, previous_challenge=challenge).json()["challenge_id"]
    assert replacement != challenge
    assert verify(client, replacement).status_code == 200


def test_demo_disabled_and_production(client, monkeypatch):
    monkeypatch.setattr(settings, "DEMO_AUTH_ENABLED", False)
    assert request(client).status_code == 503
    monkeypatch.setattr(settings, "DEMO_AUTH_ENABLED", True)
    monkeypatch.setattr(settings, "ENV", AppENV.PROD)
    assert request(client).status_code == 503
    assert verify(client, "anything").status_code == 503


def test_inactive_user_cannot_use_demo(client, db):
    challenge = request(client).json()["challenge_id"]
    verify(client, challenge)
    issued = request(client, purpose="login").json()["challenge_id"]
    db["users"].update_one({"email": "new@example.com"}, {"$set": {"is_active": False}})
    assert verify(client, issued).status_code == 400
    assert request(client, purpose="login").status_code == 400


def test_existing_formatted_phone_resolves_same_account(client, db):
    from app.models.user import User

    user = User(email="legacy@example.com", phone="+976 9900 0001", first_name="Existing", last_name="Traveller")
    db["users"].insert_one(user.to_mongo())
    assert request(client, "99000001").json()["detail"]["code"] == "account_exists"
    issued = request(client, "99000001", "login").json()["challenge_id"]
    token = verify(client, issued).json()["access_token"]
    profile = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    assert profile["id"] == user.id
    assert db["users"].count_documents({}) == 1
