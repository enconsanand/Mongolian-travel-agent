import json
import logging
import re
from typing import Any

from fastapi import HTTPException, Request, status
from pydantic import ValidationError
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

logger = logging.getLogger(__name__)


class InputValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for input validation and sanitization
    Helps prevent common injection attacks and malicious input
    """

    def __init__(self, app):
        super().__init__(app)

        # Common malicious patterns
        self.malicious_patterns = [
            # SQL Injection patterns
            r"(?i)(\bUNION\b\s+\bSELECT\b)",  # UNION SELECT
            r"(?i)(\bSELECT\b\s+.+\s+\bFROM\b)",  # SELECT ... FROM
            r"(?i)(\bINSERT\b\s+INTO\b)",  # INSERT INTO
            r"(?i)(\bUPDATE\b\s+\w+\s+\bSET\b)",  # UPDATE ... SET
            r"(?i)(\bDELETE\b\s+FROM\b)",  # DELETE FROM
            r"(?i)(\bDROP\b\s+(TABLE|DATABASE)\b)",  # DROP TABLE or DATABASE
            r"(?i)(\bCREATE\b\s+(TABLE|DATABASE)\b)",  # CREATE TABLE or DATABASE
            r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",  # tautology
            r"(\'|\"|`)(.*?)(\'|\"|`)",  # suspicious quoting
            # XSS patterns
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"on\w+\s*=",
            r"<iframe[^>]*>.*?</iframe>",
            # Command injection
            r"(\||;|&|\$\(|\`)",
            r"\b(cat|ls|pwd|rm|cp|mv|chmod|sudo|su)\b",
            # Path traversal
            r"\.\./+",
            r"\.\.\\+",
        ]

        # Compile patterns for better performance
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.malicious_patterns]

        # Paths to validate more strictly
        self.strict_validation_paths = [
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/users",
        ]

    async def dispatch(self, request: Request, call_next):
        """Validate and sanitize request input"""

        try:
            # Skip validation for certain paths
            if self._should_skip_validation(request.url.path):
                return await call_next(request)

            # Validate URL parameters
            self._validate_query_params(request)

            # Validate request body for POST/PUT/PATCH requests
            if request.method in ["POST", "PUT", "PATCH"]:
                await self._validate_request_body(request)

            # Validate headers
            self._validate_headers(request)

            # Continue with request processing
            response = await call_next(request)
            return response

        except HTTPException:
            # Re-raise HTTP exceptions (validation failures)
            raise
        except (ValueError, KeyError, json.JSONDecodeError, ValidationError) as e:
            logger.error(f"Input validation error: {e}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid request format")

    def _should_skip_validation(self, path: str) -> bool:
        """Check if validation should be skipped for this path"""
        skip_patterns = ["/docs", "/openapi.json", "/health", "/static/", "/favicon.ico"]
        return any(pattern in path for pattern in skip_patterns)

    def _validate_query_params(self, request: Request):
        """Validate URL query parameters"""
        for key, value in request.query_params.items():
            if self._contains_malicious_content(str(value)):
                logger.warning(f"Malicious content detected in query param '{key}': {value}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid characters in parameter '{key}'"
                )

    async def _validate_request_body(self, request: Request):
        """Validate request body content without consuming the stream"""
        try:
            # For basic security, we'll skip body validation in middleware
            # and rely on Pydantic models in endpoints for validation
            # This prevents consuming the request stream that FastAPI needs

            # Fast-path Content-Length check; chunked/undeclared bodies are
            # enforced by BodySizeLimitMiddleware while the stream is read
            content_length = request.headers.get("content-length")
            if content_length:
                try:
                    size = int(content_length)
                    if size > settings.MAX_REQUEST_BODY_BYTES:
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Request body too large"
                        )
                except ValueError:
                    pass

            # Check Content-Type for suspicious types
            content_type = request.headers.get("content-type", "")
            if any(suspicious in content_type.lower() for suspicious in ["script", "javascript", "vbscript"]):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid content type")

        except HTTPException:
            raise
        except (ValueError, KeyError, json.JSONDecodeError, ValidationError) as e:
            logger.error(f"Request body validation error: {e}")
            # Don't fail the request for validation errors

    def _validate_json_content(self, content: Any):
        """
        Recursively validate JSON content
        Note: This method is preserved for potential future use with endpoint-level validation
        """
        if isinstance(content, dict):
            for key, value in content.items():
                if isinstance(value, str) and self._contains_malicious_content(value):
                    logger.warning(f"Malicious content detected in field '{key}': {value}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid characters in field '{key}'"
                    )
                elif isinstance(value, (dict, list)):
                    self._validate_json_content(value)
        elif isinstance(content, list):
            for item in content:
                self._validate_json_content(item)
        elif isinstance(content, str) and self._contains_malicious_content(content):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid characters in request content")

    def _validate_headers(self, request: Request):
        """Validate request headers"""
        suspicious_headers = ["x-forwarded-host", "host"]

        for header_name in suspicious_headers:
            header_value = request.headers.get(header_name)
            if header_value and self._contains_malicious_content(header_value):
                logger.warning(f"Malicious content detected in header '{header_name}': {header_value}")
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid request headers")

    def _contains_malicious_content(self, content: str) -> bool:
        """Check if content contains malicious patterns"""
        if not content:
            return False

        # Check against compiled patterns
        return any(pattern.search(content) for pattern in self.compiled_patterns)
