import logging
import time
import uuid
from typing import Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import AppENV, settings
from app.middlewares.rate_limit import get_client_ip

logger = logging.getLogger(__name__)

SENSITIVE_HEADERS = {"authorization", "cookie", "x-api-key", "x-auth-token"}


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs every request and its outcome under a short request id, which is echoed back as X-Request-ID."""

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        start_time = time.time()
        logger.info("Request started", extra=self._request_details(request, request_id))

        try:
            response = await call_next(request)
        except Exception as e:
            logger.error(
                "Request failed",
                extra={
                    "request_id": request_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "process_time": time.time() - start_time,
                },
            )
            raise

        logger.log(
            logging.WARNING if response.status_code >= 400 else logging.INFO,
            "Request completed",
            extra={
                "request_id": request_id,
                "status_code": response.status_code,
                "content_type": response.headers.get("content-type"),
                "content_length": response.headers.get("content-length"),
                "process_time": round(time.time() - start_time, 4),
            },
        )
        response.headers["X-Request-ID"] = request_id
        return response

    @staticmethod
    def _request_details(request: Request, request_id: str) -> dict[str, Any]:
        details: dict[str, Any] = {
            "request_id": request_id,
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "client_ip": get_client_ip(request),
            "user_agent": request.headers.get("user-agent", "Unknown"),
            "content_type": request.headers.get("content-type"),
            "content_length": request.headers.get("content-length"),
        }
        if settings.ENV == AppENV.LOCAL:
            details["headers"] = {
                key: "[REDACTED]" if key.lower() in SENSITIVE_HEADERS else value
                for key, value in request.headers.items()
            }
        return details
