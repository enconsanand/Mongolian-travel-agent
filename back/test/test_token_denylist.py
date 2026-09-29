"""Unit tests for the token denylist backends (Redis test skips when unreachable)."""

import os
import uuid

import pytest
import redis

from app.core.token_denylist import (
    InMemoryTokenDenylist,
    RedisTokenDenylist,
    TokenDenylistUnavailable,
    build_token_denylist,
)

REDIS_URL = os.getenv("TEST_REDIS_URL", "redis://redis:6379/0")


def test_add_and_contains():
    denylist = InMemoryTokenDenylist()
    denylist.add("abc", ttl_seconds=60)

    assert denylist.contains("abc")
    assert not denylist.contains("other")


def test_expired_entries_are_pruned():
    denylist = InMemoryTokenDenylist()
    # ttl=0 expires immediately
    denylist.add("abc", ttl_seconds=0)

    assert not denylist.contains("abc")


def test_build_token_denylist_defaults_to_in_memory():
    # With REDIS_URL unset (default in tests), the in-memory backend is selected.
    assert isinstance(build_token_denylist(), InMemoryTokenDenylist)


def test_redis_denylist_roundtrip():
    denylist = RedisTokenDenylist(REDIS_URL)
    try:
        denylist._redis.ping()
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"Redis not available: {e}")

    jti = uuid.uuid4().hex
    denylist.add(jti, ttl_seconds=60)

    assert denylist.contains(jti)
    assert not denylist.contains(uuid.uuid4().hex)


class _BrokenRedis:
    """Stand-in for a Redis client that always raises, without needing a live server."""

    def set(self, *args, **kwargs):
        raise redis.RedisError("boom")

    def exists(self, *args, **kwargs):
        raise redis.RedisError("boom")


def _broken_denylist() -> RedisTokenDenylist:
    denylist = RedisTokenDenylist("redis://localhost:6399/0")
    denylist._redis = _BrokenRedis()
    return denylist


def test_redis_add_raises_denylist_unavailable_on_error():
    with pytest.raises(TokenDenylistUnavailable):
        _broken_denylist().add("abc", ttl_seconds=60)


def test_redis_contains_raises_denylist_unavailable_on_error():
    # A denylist that cannot be reached must fail closed, not silently return False.
    with pytest.raises(TokenDenylistUnavailable):
        _broken_denylist().contains("abc")
