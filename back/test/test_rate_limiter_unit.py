"""Unit tests for the in-memory sliding-window rate limiter (no server required)."""

import asyncio

import pytest
import redis.asyncio as aioredis
from starlette.requests import Request

from app.core.config import settings
from app.middlewares.rate_limit import InMemoryRateLimiter, RedisRateLimiter, build_rate_limiter, get_client_ip


def test_allows_up_to_limit_then_blocks():
    limiter = InMemoryRateLimiter()

    async def run():
        return [await limiter.is_allowed("client:auth", limit=2, window=60) for _ in range(3)]

    assert asyncio.run(run()) == [True, True, False]


def test_separate_keys_are_independent():
    limiter = InMemoryRateLimiter()

    async def run():
        a = await limiter.is_allowed("a:general", limit=1, window=60)
        b = await limiter.is_allowed("b:general", limit=1, window=60)
        a_again = await limiter.is_allowed("a:general", limit=1, window=60)
        return a, b, a_again

    assert asyncio.run(run()) == (True, True, False)


def test_window_expiry_allows_again():
    limiter = InMemoryRateLimiter()

    async def run():
        first = await limiter.is_allowed("k:general", limit=1, window=0)
        # window=0 means every prior timestamp is immediately outside the window
        second = await limiter.is_allowed("k:general", limit=1, window=0)
        return first, second

    assert asyncio.run(run()) == (True, True)


def test_remaining_requests_decreases():
    limiter = InMemoryRateLimiter()

    async def run():
        await limiter.is_allowed("k:general", limit=5, window=60)
        await limiter.is_allowed("k:general", limit=5, window=60)
        return await limiter.get_remaining_requests("k:general", limit=5)

    assert asyncio.run(run()) == 3


def test_build_rate_limiter_defaults_to_in_memory():
    # With REDIS_URL unset (default in tests), the in-memory backend is selected.
    assert isinstance(build_rate_limiter(), InMemoryRateLimiter)


def test_record_and_count_within_window():
    limiter = InMemoryRateLimiter()

    async def run():
        await limiter.record("acct", window=60)
        await limiter.record("acct", window=60)
        return await limiter.count("acct", window=60)

    assert asyncio.run(run()) == 2


def test_count_prunes_expired_events():
    limiter = InMemoryRateLimiter()

    async def run():
        # window=0 means every prior timestamp is immediately outside the window
        await limiter.record("acct", window=0)
        return await limiter.count("acct", window=0)

    assert asyncio.run(run()) == 0


def test_record_does_not_affect_other_keys():
    limiter = InMemoryRateLimiter()

    async def run():
        await limiter.record("a", window=60)
        return await limiter.count("b", window=60)

    assert asyncio.run(run()) == 0


def _request(headers: dict[str, str] | None = None, client_host: str = "10.0.0.1") -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/auth/login",
        "headers": [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()],
        "client": (client_host, 12345),
    }
    return Request(scope)


def test_client_ip_ignores_forwarded_headers_by_default(monkeypatch):
    monkeypatch.setattr(settings, "TRUST_PROXY_HEADERS", False)
    request = _request({"X-Forwarded-For": "1.2.3.4"})
    assert get_client_ip(request) == "10.0.0.1"


def test_client_ip_uses_rightmost_forwarded_ip(monkeypatch):
    # Leftmost entries are attacker-supplied; the trusted proxy appends the real IP last.
    monkeypatch.setattr(settings, "TRUST_PROXY_HEADERS", True)
    request = _request({"X-Forwarded-For": "1.2.3.4, 5.6.7.8, 203.0.113.9"})
    assert get_client_ip(request) == "203.0.113.9"


def test_client_ip_falls_back_to_x_real_ip(monkeypatch):
    monkeypatch.setattr(settings, "TRUST_PROXY_HEADERS", True)
    request = _request({"X-Real-IP": "203.0.113.9"})
    assert get_client_ip(request) == "203.0.113.9"


def test_client_ip_falls_back_to_direct_client(monkeypatch):
    monkeypatch.setattr(settings, "TRUST_PROXY_HEADERS", True)
    assert get_client_ip(_request()) == "10.0.0.1"


class _BrokenRedis:
    """Stand-in for a Redis client that always raises, without needing a live server."""

    async def zremrangebyscore(self, *args, **kwargs):
        raise aioredis.RedisError("boom")

    async def zcard(self, *args, **kwargs):
        raise aioredis.RedisError("boom")


def _broken_limiter(fail_open: bool) -> RedisRateLimiter:
    limiter = RedisRateLimiter("redis://localhost:6399/0", fail_open=fail_open)
    limiter._redis = _BrokenRedis()

    async def _raise_script(*args, **kwargs):
        raise aioredis.RedisError("boom")

    limiter._script = _raise_script
    return limiter


def test_redis_is_allowed_fails_open_by_default():
    limiter = _broken_limiter(fail_open=True)
    assert asyncio.run(limiter.is_allowed("k", limit=5, window=60)) is True


def test_redis_is_allowed_fails_closed_when_configured():
    limiter = _broken_limiter(fail_open=False)
    with pytest.raises(aioredis.RedisError):
        asyncio.run(limiter.is_allowed("k", limit=5, window=60))


def test_redis_count_fails_open_by_default():
    limiter = _broken_limiter(fail_open=True)
    assert asyncio.run(limiter.count("k", window=60)) == 0


def test_redis_count_fails_closed_when_configured():
    limiter = _broken_limiter(fail_open=False)
    with pytest.raises(aioredis.RedisError):
        asyncio.run(limiter.count("k", window=60))


def test_build_rate_limiter_passes_fail_open_flag_to_redis_backend(monkeypatch):
    monkeypatch.setattr(settings, "REDIS_URL", "redis://localhost:6399/0")
    limiter = build_rate_limiter(fail_open=False)
    assert isinstance(limiter, RedisRateLimiter)
    assert limiter._fail_open is False
