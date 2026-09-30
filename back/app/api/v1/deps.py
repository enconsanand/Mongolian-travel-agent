from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pymongo.database import Database

from app import crud
from app.core.config import settings
from app.core.token_denylist import TokenDenylistUnavailable, token_denylist
from app.db.mongo import get_database
from app.models.user import User
from app.schemas.user import TokenPayload

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    scheme_name="User",
)


def _credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_db() -> Database:
    """Get the MongoDB database handle (the client is shared and pooled)."""
    return get_database()


def decode_access_token(token: str) -> dict:
    """
    Decode and validate an access token.

    Raises:
        HTTPException: 401 if the token is invalid, of the wrong type, or revoked.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.ALGORITHM],
            # python-jose does not require these claims to be present by default
            options={"require_exp": True, "require_sub": True, "require_jti": True},
        )
    except JWTError:
        raise _credentials_exception()

    if payload.get("type") != "access_token":
        raise _credentials_exception()

    # Reject tokens revoked via logout; a denylist outage fails closed (503)
    # rather than letting a possibly-revoked token through
    try:
        revoked = token_denylist.contains(payload["jti"])
    except TokenDenylistUnavailable:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication temporarily unavailable. Please try again shortly.",
        )
    if revoked:
        raise _credentials_exception()

    return payload


def get_current_user(
    db: Annotated[Database, Depends(get_db)],
    token: Annotated[str, Depends(oauth2_scheme)],
) -> User:
    """
    Validate JWT token and return current user.

    Raises:
        HTTPException: 401 if token is invalid or user not found.
    """
    payload = decode_access_token(token)
    token_data = TokenPayload(**payload)

    if not token_data.sub:
        raise _credentials_exception()

    user = crud.user.get_by_email(db=db, email=token_data.sub)

    if user is None:
        raise _credentials_exception()

    return user


def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Get current user and verify they are active.

    Raises:
        HTTPException: 403 if user is inactive.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return current_user


# Type aliases for cleaner dependency injection
DbSession = Annotated[Database, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
ActiveUser = Annotated[User, Depends(get_current_active_user)]
