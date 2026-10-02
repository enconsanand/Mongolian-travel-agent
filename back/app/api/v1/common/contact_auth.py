"""Demo contact verification: no message delivery; an issued challenge accepts six digits."""

import re
from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field, TypeAdapter, field_validator
from pymongo.errors import DuplicateKeyError

from app.api.v1.deps import DbSession
from app.core.auth import create_access_token
from app.core.config import settings
from app.models.user import User
from app.schemas.user import Token

router = APIRouter()


class CodeRequest(BaseModel):
    contact: str = Field(min_length=1, max_length=254)
    purpose: Literal["login", "register"]
    name: str = Field(default="", max_length=100)
    previous_challenge: str | None = Field(default=None, max_length=100)

    @field_validator("contact")
    @classmethod
    def normalize(cls, value: str) -> str:
        value = value.strip().lower()
        if "@" in value:
            return str(TypeAdapter(EmailStr).validate_python(value))
        value = re.sub(r"[\s()-]", "", value)
        value = value.removeprefix("+976")
        if not re.fullmatch(r"[0-9]{8}", value):
            raise ValueError("Enter an email address or an 8-digit Mongolian phone number")
        return f"+976{value}"


class CodeVerify(BaseModel):
    challenge_id: str = Field(min_length=1, max_length=100)
    code: str = Field(pattern=r"^[0-9]{6}$")


def _contact_query(field: str, contact: str) -> dict:
    if field == "email":
        return {field: contact}
    # Older seeded profiles stored phones with spaces. Resolve those to the same account.
    digits = contact.removeprefix("+976")
    pattern = r"^(?:\+976[\s()-]*)?" + r"[\s()-]*".join(digits) + r"$"
    return {"phone": {"$regex": pattern}}


def _enabled() -> None:
    if not settings.DEMO_AUTH_ENABLED or not settings.ENV.is_development:
        raise HTTPException(503, detail={"code": "demo_auth_disabled"})


@router.post("/code/request")
def request_code(body: CodeRequest, db: DbSession) -> dict:
    _enabled()
    now = datetime.now(UTC)
    field = "email" if "@" in body.contact else "phone"
    user = db["users"].find_one(_contact_query(field, body.contact))
    if body.purpose == "login" and not user:
        raise HTTPException(409, detail={"code": "registration_required"})
    if body.purpose == "register" and user:
        raise HTTPException(409, detail={"code": "account_exists"})
    if user and not user.get("is_active", True):
        raise HTTPException(400, detail={"code": "account_unavailable"})
    if body.purpose == "register" and not body.name.strip():
        raise HTTPException(422, detail={"code": "name_required"})
    if body.previous_challenge:
        previous = db["auth_challenges"].find_one({"_id": body.previous_challenge})
        if previous and previous["created_at"] + timedelta(seconds=30) > now:
            raise HTTPException(429, detail={"code": "resend_wait"})
        db["auth_challenges"].delete_one({"_id": body.previous_challenge})
    challenge_id = token_urlsafe(32)
    db["auth_challenges"].insert_one(
        {
            "_id": challenge_id,
            "contact": body.contact,
            "field": field,
            "purpose": body.purpose,
            "name": body.name.strip(),
            "created_at": now,
            "expires_at": now + timedelta(minutes=5),
        }
    )
    return {"challenge_id": challenge_id, "contact": body.contact, "expires_in": 300, "resend_after": 30}


@router.post("/code/verify", response_model=Token)
def verify_code(body: CodeVerify, db: DbSession) -> Token:
    _enabled()
    challenge = db["auth_challenges"].find_one_and_delete(
        {"_id": body.challenge_id, "expires_at": {"$gt": datetime.now(UTC)}}
    )
    if not challenge:
        raise HTTPException(400, detail={"code": "code_expired"})
    query = {challenge["field"]: challenge["contact"]}
    doc = db["users"].find_one(_contact_query(challenge["field"], challenge["contact"]))
    if challenge["purpose"] == "register":
        if doc:
            raise HTTPException(409, detail={"code": "account_exists"})
        user = User(**query, first_name=challenge["name"], last_name="")
        try:
            db["users"].insert_one(user.to_mongo())
        except DuplicateKeyError as exc:
            raise HTTPException(409, detail={"code": "account_exists"}) from exc
    else:
        if not doc or not doc.get("is_active", True):
            raise HTTPException(400, detail={"code": "account_unavailable"})
        user = User.model_validate(doc)
    return Token(access_token=create_access_token(user.id, subject_kind="user_id"))
