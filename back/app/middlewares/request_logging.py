import logging
import time
import uuid
from typing import Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import AppENV, settings

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for comprehensive request/response logging
    Provides structured logging for monitoring and debugging
    """

    def __init__(self, app):
        super().__init__(app)
        self.sensitive_headers = {"authorization", "cookie", "x-api-key", "x-auth-token"}
        self.sensitive_paths = {"/auth/login", "/auth/register", "/auth/reset-password"}

    async def dispatch(self, request: Request, call_next):
        """Log request and response details"""

        # Generate unique request ID
        request_id = str(uuid.uuid4())[:8]

        # Start timing
        start_time = time.time()

        # Extract request details
        request_details = self._extract_request_details(request, request_id)

        # Log incoming request
        logger.info("Request started", extra=request_details)

        # Process request
        try:
            response = await call_next(request)

            # Calculate processing time
            process_time = time.time() - start_time

            # Extract response details
            response_details = self._extract_response_details(response, request_id, process_time)

            # Log response
            log_level = logging.WARNING if response.status_code >= 400 else logging.INFO
            logger.log(log_level, "Request completed", extra=response_details)

            # Add request ID to response headers for tracing
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as e:
            # Log error
            error_details = {
                "request_id": request_id,
                "error": str(e),
                "error_type": type(e).__name__,
                "process_time": time.time() - start_time,
            }
            logger.error("Request failed", extra=error_details)
            raise

    def _extract_request_details(self, request: Request, request_id: str) -> dict[str, Any]:
        """Extract relevant request details for logging"""
        client_ip = self._get_client_ip(request)

        # Filter sensitive headers
        headers = {}
        for key, value in request.headers.items():
            if key.lower() in self.sensitive_headers:
                headers[key] = "[REDACTED]"
            else:
                headers[key] = value

        details: dict[str, Any] = {
            "request_id": request_id,
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "client_ip": client_ip,
            "user_agent": request.headers.get("user-agent", "Unknown"),
            "content_type": request.headers.get("content-type"),
            "content_length": request.headers.get("content-length"),
        }

        # Add headers only in debug mode or local environment
        if settings.ENV == AppENV.LOCAL:
            details["headers"] = headers

        return details

    def _extract_response_details(self, response, request_id: str, process_time: float) -> dict[str, Any]:
        """Extract response details for logging"""
        return {
            "request_id": request_id,
            "status_code": response.status_code,
            "content_type": response.headers.get("content-type"),
            "content_length": response.headers.get("content-length"),
            "process_time": round(process_time, 4),
        }

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address"""
        # Only trust forwarded headers when explicitly running behind a trusted proxy.
        if settings.TRUST_PROXY_HEADERS:
            forwarded_for = request.headers.get("x-forwarded-for")
            if forwarded_for:
                return forwarded_for.split(",")[0].strip()

            real_ip = request.headers.get("x-real-ip")
            if real_ip:
                return real_ip

        return request.client.host if request.client else "unknown"
