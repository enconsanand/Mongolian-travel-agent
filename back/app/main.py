import asyncio
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app import workers
from app.api.v1 import bookings, payments, travel
from app.api.v1.api_user import user_router
from app.core.config import settings
from app.db.mongo import ensure_indexes, get_database
from app.middlewares.body_size_limit import BodySizeLimitMiddleware
from app.middlewares.input_validation import InputValidationMiddleware
from app.middlewares.rate_limit import RateLimitMiddleware
from app.middlewares.request_logging import RequestLoggingMiddleware
from app.middlewares.security_headers import SecurityHeadersMiddleware

# ============================================================================
# Logging Configuration
# ============================================================================
logging.basicConfig(
    format="%(levelname)s %(pathname)s:%(funcName)s(%(lineno)d) %(message)s",
    level=logging.DEBUG if settings.ENV.is_development else logging.INFO,
)
logger = logging.getLogger(__name__)


# ============================================================================
# Application Lifespan
# ============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    logger.info("Starting %s in %s mode", settings.PROJECT_NAME, settings.ENV.value)
    if settings.MONGO_INIT_ON_STARTUP:
        # Geo queries and the unique email need these even if the seeder never ran on this database.
        # Blocking pymongo calls run in a thread so the event loop stays free.
        failed = await asyncio.to_thread(ensure_indexes, get_database())
        if failed:
            logger.error("MongoDB indexes missing on: %s (geo search may fail)", ", ".join(failed))
    stop = workers.start() if settings.BACKGROUND_WORKERS else None
    yield
    if stop:
        stop.set()
    logger.info("Shutting down %s", settings.PROJECT_NAME)


# ============================================================================
# Application Factory
# ============================================================================
def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        openapi_url=settings.OPENAPI_URL,
        debug=settings.ENV.is_development,
        lifespan=lifespan,
    )

    _configure_cors(app)
    _configure_middlewares(app)
    _configure_routes(app)

    return app


def _configure_cors(app: FastAPI) -> None:
    """Configure CORS middleware."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin).rstrip("/") for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=[
            "Accept",
            "Accept-Language",
            "Content-Language",
            "Content-Type",
            "Authorization",
            "X-Requested-With",
            "X-Request-ID",
        ],
        expose_headers=["X-Request-ID", "X-RateLimit-Remaining", "X-RateLimit-Limit"],
    )


def _configure_middlewares(app: FastAPI) -> None:
    """
    Configure application middlewares.

    Order matters: last added = first executed.
    """
    # Body size cap (innermost - counts bytes as endpoints read the stream,
    # so chunked bodies without Content-Length cannot bypass the limit)
    app.add_middleware(BodySizeLimitMiddleware)

    # Rate limiting (first to execute - reject early)
    app.add_middleware(RateLimitMiddleware)

    # Input validation
    app.add_middleware(InputValidationMiddleware)

    # Request logging
    app.add_middleware(RequestLoggingMiddleware)

    # Security headers (last to execute - always add headers)
    app.add_middleware(SecurityHeadersMiddleware)

    # Process time header
    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next) -> Response:
        start_time = time.perf_counter()
        response = await call_next(request)
        process_time = time.perf_counter() - start_time
        response.headers["X-Process-Time"] = f"{process_time:.4f}"
        return response


def _configure_routes(app: FastAPI) -> None:
    """Configure application routes."""
    app.include_router(user_router, prefix=settings.API_V1_STR)
    app.include_router(travel.router, prefix=settings.API_V1_STR)
    app.include_router(payments.router, prefix=settings.API_V1_STR)
    app.include_router(bookings.router, prefix=settings.API_V1_STR)

    @app.get("/", tags=["Root"])
    async def root() -> dict:
        """Root endpoint returning basic API information."""
        return {
            "project": settings.PROJECT_NAME,
            "version": "1.0.0",
            "environment": settings.ENV.value,
            "docs_url": "/docs" if not settings.ENV.is_production else None,
            "health_url": "/health",
        }

    @app.get("/health", tags=["Health"])
    async def health_check() -> dict:
        """Health check endpoint for monitoring."""
        return {
            "status": "healthy",
            "timestamp": time.time(),
            "environment": settings.ENV.value,
            "project": settings.PROJECT_NAME,
        }

    if settings.ENV.is_development:

        @app.get("/test-rate-limit", tags=["Debug"])
        async def test_rate_limit() -> dict:
            """Test endpoint to verify rate limiting (dev only)."""
            return {"message": "Rate limiting is working!"}


app = create_app()
