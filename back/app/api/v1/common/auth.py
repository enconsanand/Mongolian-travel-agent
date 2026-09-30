import ipaddress
import math
import time
from typing import Annotated

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.concurrency import run_in_threadpool
from fastapi.security import OAuth2PasswordRequestForm

from app.api.v1.deps import ActiveUser, DbSession, decode_access_token, oauth2_scheme
from app.core.auth import authenticate_user, create_access_token
from app.core.config import settings
from app.core.token_denylist import TokenDenylistUnavailable, token_denylist
from app.middlewares.rate_limit import build_rate_limiter, get_client_ip
from app.schemas.user import Token, UserResponse

router = APIRouter()

# Failed-login tracker; Redis-backed when REDIS_URL is set so the per-account
# lockout is shared across all workers. fail_open=False: a Redis outage must
# block login rather than silently disable brute-force protection.
_login_failures = build_rate_limiter(fail_open=False)


def _subnet_for(ip: str) -> str:
    """Coarse network for an IP: /24 for IPv4, /64 for IPv6, else the raw value."""
    try:
        network = ipaddress.ip_network(f"{ip}/24" if "." in ip else f"{ip}/64", strict=False)
    except ValueError:
        return ip
    return str(network)


def _account_key(username: str, request: Request) -> str:
    # Keying on account + requesting subnet means an attacker can only lock out
    # their own subnet's login attempts for this account, not the real owner's.
    subnet = _subnet_for(get_client_ip(request))
    return f"account-failed:{username.strip().lower()}:{subnet}"


@router.post("/login", response_model=Token)
async def login(
    db: DbSession,
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    """Authenticate user and return access token."""
    account_key = _account_key(form_data.username, request)
    window = settings.LOGIN_FAILED_ATTEMPTS_WINDOW_SECONDS

    # Per-account lockout keyed on the target email + subnet, so brute-force
    # attempts distributed across many IPs are still throttled without letting
    # an attacker lock out the legitimate owner from a different network.
    try:
        locked_out = await _login_failures.count(account_key, window) >= settings.LOGIN_MAX_FAILED_ATTEMPTS
    except aioredis.RedisError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Login temporarily unavailable. Please try again shortly.",
        )

    if locked_out:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Please try again later.",
            headers={"Retry-After": str(window)},
        )

    # bcrypt + DB access run in a worker thread to keep the event loop free
    user = await run_in_threadpool(authenticate_user, db=db, email=form_data.username, password=form_data.password)

    # Uniform 401 for all failures (unknown email, wrong password, inactive
    # account) to prevent account enumeration.
    if not user:
        await _login_failures.record(account_key, window)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return Token(access_token=create_access_token(sub=user.email))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(token: Annotated[str, Depends(oauth2_scheme)]) -> None:
    """Revoke the presented access token so it is unusable after logout."""
    payload = decode_access_token(token)

    # Keep the jti denylisted for the token's remaining lifetime; ceil so any
    # positive remainder (even sub-second) still gets denylisted
    ttl = math.ceil(payload["exp"] - time.time())
    if ttl > 0:
        try:
            token_denylist.add(payload["jti"], ttl)
        except TokenDenylistUnavailable:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Logout temporarily unavailable. Please try again shortly.",
            )


@router.get("/me", response_model=UserResponse)
def get_current_user(user: ActiveUser) -> UserResponse:
    """Get current authenticated user profile."""
    return UserResponse.model_validate(user)
