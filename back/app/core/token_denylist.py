import logging
import threading
import time
from typing import Protocol

import redis

from app.core.config import settings

logger = logging.getLogger(__name__)


class TokenDenylistUnavailable(Exception):
    """Raised when the denylist backend cannot be reached; callers must fail closed."""


class TokenDenylist(Protocol):
    """Common interface for revoked-token storage backends."""

    def add(self, jti: str, ttl_seconds: int) -> None: ...

    def contains(self, jti: str) -> bool: ...


class InMemoryTokenDenylist:
    """
    Revoked-token store held in process memory.

    Correct for a single worker only; use the Redis backend when running
    multiple workers/instances so revocation is shared and global.
    """

    def __init__(self):
        self._entries: dict[str, float] = {}
        self._lock = threading.Lock()

    def add(self, jti: str, ttl_seconds: int) -> None:
        now = time.time()
        with self._lock:
            self._prune(now)
            self._entries[jti] = now + ttl_seconds

    def contains(self, jti: str) -> bool:
        now = time.time()
        with self._lock:
            self._prune(now)
            return jti in self._entries

    def _prune(self, now: float) -> None:
        expired = [jti for jti, expires_at in self._entries.items() if expires_at <= now]
        for jti in expired:
            del self._entries[jti]


class RedisTokenDenylist:
    """
    Distributed revoked-token store backed by Redis with per-entry TTL.

    Revocation is a security-critical guarantee: on a Redis error both `add`
    and `contains` raise `TokenDenylistUnavailable` instead of failing open,
    so callers can reject the request rather than risk letting a revoked or
    unrevocable token through.
    """

    def __init__(self, redis_url: str):
        self._redis = redis.Redis.from_url(redis_url, decode_responses=True)

    @staticmethod
    def _key(jti: str) -> str:
        return f"token-denylist:{jti}"

    def add(self, jti: str, ttl_seconds: int) -> None:
        try:
            self._redis.set(self._key(jti), "1", ex=ttl_seconds)
        except redis.RedisError as exc:
            raise TokenDenylistUnavailable("Token revocation store unavailable") from exc

    def contains(self, jti: str) -> bool:
        try:
            return bool(self._redis.exists(self._key(jti)))
        except redis.RedisError as exc:
            raise TokenDenylistUnavailable("Token revocation store unavailable") from exc


def build_token_denylist() -> TokenDenylist:
    """Select the denylist backend based on configuration."""
    if settings.REDIS_URL:
        logger.info("Token denylist backend: Redis (distributed)")
        return RedisTokenDenylist(settings.REDIS_URL)
    if settings.ENV.is_production:
        logger.warning(
            "REDIS_URL not set while ENV=%s; using per-process token denylist. "
            "Logout/revocation will NOT be shared across workers/instances.",
            settings.ENV.value,
        )
    logger.info("Token denylist backend: in-memory (single process)")
    return InMemoryTokenDenylist()


token_denylist = build_token_denylist()
