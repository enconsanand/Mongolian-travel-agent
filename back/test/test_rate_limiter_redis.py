"""Integration tests for the Redis-backed rate limiter.

These run against a real Redis (the compose ``redis`` service). They are skipped
automatically when Redis is unreachable, e.g. in CI where no Redis is provided.

The Redis client must be created and used within a single event loop, so each
test builds the limiter inside its own ``asyncio.run`` coroutine.
"""

import asyncio
import os
import uuid

import pytest

from app.middlewares.rate_limit import RedisRateLimiter

REDIS_URL = os.getenv("TEST_REDIS_URL", "redis://redis:6379/0")


async def _make_limiter() -> RedisRateLimiter:
    limiter = RedisRateLimiter(REDIS_URL)
    try:
        await limiter._redis.ping()
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"Redis not available: {e}")
    return limiter


def test_redis_allows_up_to_limit_then_blocks():
    key = f"test:{uuid.uuid4().hex}"

    async def run():
        limiter = await _make_limiter()
        return [await limiter.is_allowed(key, limit=2, window=60) for _ in range(3)]

    assert asyncio.run(run()) == [True, True, False]


def test_redis_remaining_requests():
    key = f"test:{uuid.uuid4().hex}"

    async def run():
        limiter = await _make_limiter()
        await limiter.is_allowed(key, limit=5, window=60)
        await limiter.is_allowed(key, limit=5, window=60)
        return await limiter.get_remaining_requests(key, limit=5)

    assert asyncio.run(run()) == 3


def test_redis_record_and_count():
    key = f"test:{uuid.uuid4().hex}"

    async def run():
        limiter = await _make_limiter()
        await limiter.record(key, window=60)
        await limiter.record(key, window=60)
        return await limiter.count(key, window=60)

    assert asyncio.run(run()) == 2
