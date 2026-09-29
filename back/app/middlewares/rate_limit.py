import logging
import time
import uuid
from collections import defaultdict, deque
from typing import Protocol

import redis.asyncio as aioredis
from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

logger = logging.getLogger(__name__)


class RateLimiter(Protocol):
    """Common async interface for rate limiter backends."""

    async def is_allowed(self, key: str, limit: int, window: int) -> bool: ...

    async def get_remaining_requests(self, key: str, limit: int) -> int: ...

    async def record(self, key: str, window: int) -> None: ...

    async def count(self, key: str, window: int) -> int: ...


class InMemoryRateLimiter:
    """
    Sliding-window rate limiter held in process memory.

    Correct for a single worker only; use the Redis backend when running
    multiple workers/instances so limits are shared and global.
    """

    def __init__(self):
        self.requests: dict[str, deque] = defaultdict(deque)
        self._last_prune = time.time()

    async def is_allowed(self, key: str, limit: int, window: int) -> bool:
        """
        Check if request is allowed based on rate limit

        Args:
            key: Identifier for the client (IP address + endpoint type)
            limit: Maximum number of requests allowed
            window: Time window in seconds

        Returns:
            True if request is allowed, False otherwise
        """
        now = time.time()
        self._maybe_prune(now, window)
        self._prune_key(key, now, window)

        # Check if limit is exceeded
        timestamps = self.requests[key]
        if len(timestamps) >= limit:
            return False

        # Add current request timestamp
        timestamps.append(now)
        return True

    async def get_remaining_requests(self, key: str, limit: int) -> int:
        """Get number of remaining requests for the key"""
        return max(0, limit - len(self.requests[key]))

    async def record(self, key: str, window: int) -> None:
        """Record an event (e.g. a failed login) without enforcing a limit."""
        now = time.time()
        self._prune_key(key, now, window)
        self.requests[key].append(now)

    async def count(self, key: str, window: int) -> int:
        """Count events recorded for the key within the window."""
        now = time.time()
        self._prune_key(key, now, window)
        return len(self.requests[key])

    def _prune_key(self, key: str, now: float, window: int) -> None:
        """Drop timestamps for the key that fall outside the window."""
        timestamps = self.requests[key]
        while timestamps and timestamps[0] <= now - window:
            timestamps.popleft()

    def _maybe_prune(self, now: float, window: int) -> None:
        """Periodically drop keys whose windows have fully expired to bound memory."""
        if now - self._last_prune < window:
            return
        self._last_prune = now
        stale_keys = [
            key for key, timestamps in self.requests.items() if not timestamps or timestamps[-1] <= now - window
        ]
        for key in stale_keys:
            del self.requests[key]


class RedisRateLimiter:
    """
    Distributed sliding-window rate limiter backed by Redis sorted sets.

    The check is performed in a single atomic Lua script so concurrent workers
    cannot exceed the limit. By default the limiter fails open (allows the
    request) on a Redis outage so it never takes the whole API down; pass
    ``fail_open=False`` for security-critical gates (e.g. login lockout) where
    an outage must block the protected action instead of letting it through.
    """

    # KEYS[1]=zset key  ARGV: now, window(s), limit, unique-member
    _SLIDING_WINDOW_LUA = """
    local key = KEYS[1]
    local now = tonumber(ARGV[1])
    local window = tonumber(ARGV[2])
    local limit = tonumber(ARGV[3])
    local member = ARGV[4]
    redis.call('ZREMRANGEBYSCORE', key, 0, now - window)
    local count = redis.call('ZCARD', key)
    if count < limit then
        redis.call('ZADD', key, now, member)
        redis.call('PEXPIRE', key, math.ceil(window * 1000))
        return 1
    end
    return 0
    """

    def __init__(self, redis_url: str, fail_open: bool = True):
        self._redis = aioredis.from_url(redis_url, encoding="utf-8", decode_responses=True)
        self._script = self._redis.register_script(self._SLIDING_WINDOW_LUA)
        self._fail_open = fail_open

    @staticmethod
    def _redis_key(key: str) -> str:
        return f"ratelimit:{key}"

    async def is_allowed(self, key: str, limit: int, window: int) -> bool:
        now = time.time()
        member = f"{now}:{uuid.uuid4().hex}"
        try:
            allowed = await self._script(keys=[self._redis_key(key)], args=[now, window, limit, member])
            return bool(allowed)
        except aioredis.RedisError:
            if self._fail_open:
                logger.error("Redis rate limiter unavailable, allowing request")
                return True
            raise

    async def get_remaining_requests(self, key: str, limit: int) -> int:
        try:
            count = await self._redis.zcard(self._redis_key(key))
        except aioredis.RedisError:  # pragma: no cover - network/redis failure path
            return limit
        return max(0, limit - int(count))

    async def record(self, key: str, window: int) -> None:
        """Record an event (e.g. a failed login) without enforcing a limit."""
        now = time.time()
        member = f"{now}:{uuid.uuid4().hex}"
        try:
            async with self._redis.pipeline(transaction=True) as pipe:
                pipe.zadd(self._redis_key(key), {member: now})
                pipe.pexpire(self._redis_key(key), window * 1000)
                await pipe.execute()
        except aioredis.RedisError as exc:  # pragma: no cover - network/redis failure path
            logger.error("Redis rate limiter unavailable, event not recorded: %s", exc)

    async def count(self, key: str, window: int) -> int:
        """Count events recorded for the key within the window."""
        now = time.time()
        try:
            await self._redis.zremrangebyscore(self._redis_key(key), 0, now - window)
            return int(await self._redis.zcard(self._redis_key(key)))
        except aioredis.RedisError:
            if self._fail_open:
                logger.error("Redis rate limiter unavailable, failing open")
                return 0
            raise


def build_rate_limiter(fail_open: bool = True) -> RateLimiter:
    """Select the rate limiter backend based on configuration."""
    if settings.REDIS_URL:
        logger.info("Rate limiting backend: Redis (distributed)")
        return RedisRateLimiter(settings.REDIS_URL, fail_open=fail_open)
    if settings.ENV.is_production:
        logger.warning(
            "REDIS_URL not set while ENV=%s; using per-process rate limiter. "
            "Limits will NOT be shared across workers/instances.",
            settings.ENV.value,
        )
    logger.info("Rate limiting backend: in-memory (single process)")
    return InMemoryRateLimiter()


def get_client_ip(request: Request) -> str:
    """Extract the client IP address from a request, honoring trusted-proxy config."""
    # Only trust forwarded headers when explicitly running behind a trusted proxy,
    # otherwise clients could spoof them to bypass rate limiting.
    if settings.TRUST_PROXY_HEADERS:
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Rightmost IP is the one appended by the trusted proxy; leftmost
            # entries are client-supplied and spoofable (assumes one trusted proxy)
            return forwarded_for.split(",")[-1].strip()

        # Only safe when the proxy overwrites (not appends) this header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

    # Fall back to direct client IP
    return request.client.host if request.client else "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware for FastAPI
    Applies different rate limits based on endpoint patterns
    """

    def __init__(self, app):
        super().__init__(app)
        self.limiter: RateLimiter = build_rate_limiter()
        self.default_limit = settings.RATE_LIMIT_REQUESTS_PER_MINUTE
        self.auth_limit = settings.RATE_LIMIT_AUTH_REQUESTS_PER_MINUTE
        self.window = 60  # 1 minute window in seconds

    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting"""

        # Skip rate limiting for health checks and static files
        if self._should_skip_rate_limiting(request.url.path):
            return await call_next(request)

        client_ip = get_client_ip(request)

        # Determine rate limit based on endpoint
        if self._is_auth_endpoint(request.url.path):
            limit = self.auth_limit
            limit_type = "auth"
        else:
            limit = self.default_limit
            limit_type = "general"

        # Create unique key for this IP and endpoint type
        rate_limit_key = f"{client_ip}:{limit_type}"

        # Check rate limit
        if not await self.limiter.is_allowed(rate_limit_key, limit, self.window):
            logger.warning(f"Rate limit exceeded for {client_ip} on {limit_type} endpoints")
            return Response(
                content=f"Rate limit exceeded. Maximum {limit} requests per minute allowed for {limit_type} endpoints.",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Window": str(self.window),
                    "X-RateLimit-Reset": str(int(time.time()) + self.window),
                    "Retry-After": "60",
                },
            )

        # Continue with request processing
        response = await call_next(request)

        # Add rate limit headers to response
        remaining = await self.limiter.get_remaining_requests(rate_limit_key, limit)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Window"] = str(self.window)
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + self.window)

        return response

    def _is_auth_endpoint(self, path: str) -> bool:
        """Check if the endpoint is authentication related"""
        auth_patterns = [
            "/auth/login",
            "/auth/register",
            "/auth/refresh",
            "/auth/reset-password",
            "/auth/forgot-password",
            "/auth/token",
        ]
        return any(pattern in path for pattern in auth_patterns)

    def _should_skip_rate_limiting(self, path: str) -> bool:
        """Check if rate limiting should be skipped for this path"""
        skip_patterns = ["/health", "/docs", "/openapi.json", "/favicon.ico", "/static/"]
        return any(pattern in path for pattern in skip_patterns)
