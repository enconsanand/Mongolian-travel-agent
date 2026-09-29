from datetime import datetime, timedelta
from secrets import token_urlsafe
from uuid import uuid4
from zoneinfo import ZoneInfo

from jose import jwt
from sqlalchemy.orm import Session

from app import crud
from app.core.config import settings
from app.core.security import get_password_hash, verify_password
from app.models.user import User

# Precomputed at import time so the "user not found" path spends the same
# bcrypt work as a real password check, preventing timing-based email enumeration.
_DUMMY_HASH = get_password_hash(token_urlsafe(32))


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    """
    Authenticate a user by email and password.

    Returns the user if successful, None otherwise. Inactive accounts are
    treated like bad credentials so responses cannot be used to enumerate
    account state.
    """
    user = crud.user.get_by_email(db=db, email=email)
    if not user:
        verify_password(password, _DUMMY_HASH)
        return None
    if not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None
    return user


def create_access_token(sub: str, expires_delta: timedelta | None = None) -> str:
    """
    Create a JWT access token.

    Args:
        sub: Subject (typically user email or ID)
        expires_delta: Optional custom expiration time
    """
    lifetime = expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return _create_token(token_type="access_token", lifetime=lifetime, sub=sub)


def _create_token(*, token_type: str, lifetime: timedelta, sub: str) -> str:
    """
    Create a JWT token with the given parameters.

    Uses the configured application timezone.
    """
    tz = ZoneInfo(settings.TIMEZONE)
    now = datetime.now(tz)

    payload = {
        "type": token_type,
        "exp": now + lifetime,
        "iat": now,
        # Unique token id enabling server-side revocation on logout
        "jti": uuid4().hex,
        "sub": sub,
    }

    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.ALGORITHM)
