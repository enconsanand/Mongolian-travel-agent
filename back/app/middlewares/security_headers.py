import logging

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import AppENV, settings

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses
    Helps protect against various web vulnerabilities
    """

    def __init__(self, app):
        super().__init__(app)
        self.security_headers = self._get_security_headers()

    def _get_security_headers(self) -> dict[str, str]:
        """Get security headers based on environment"""
        headers = {
            # Prevent MIME type sniffing
            "X-Content-Type-Options": "nosniff",
            # Prevent clickjacking attacks
            "X-Frame-Options": "DENY",
            # Enable XSS protection (legacy but still useful)
            "X-XSS-Protection": "1; mode=block",
            # Control referrer information
            "Referrer-Policy": "strict-origin-when-cross-origin",
            # Prevent browsers from performing DNS prefetching
            "X-DNS-Prefetch-Control": "off",
        }

        # Add HSTS header for production environments
        if settings.ENV in [AppENV.PROD, AppENV.STG]:
            headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        # Add Content Security Policy
        csp_policy = self._get_csp_policy()
        if csp_policy:
            headers["Content-Security-Policy"] = csp_policy

        return headers

    def _get_csp_policy(self) -> str | None:
        """Generate Content Security Policy based on environment"""
        if settings.ENV == AppENV.LOCAL:
            # More permissive CSP for development
            return (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self' http://localhost:* ws://localhost:*; "
                "frame-ancestors 'none';"
            )
        else:
            # Stricter CSP for production
            return (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self';"
            )

    async def dispatch(self, request: Request, call_next):
        """Add security headers to response"""
        response = await call_next(request)

        # Add security headers
        for header_name, header_value in self.security_headers.items():
            # Skip CSP for Swagger/docs endpoints
            if header_name == "Content-Security-Policy" and request.url.path in ["/docs", "/redoc", "/openapi.json"]:
                continue
            response.headers[header_name] = header_value

        # Log security header addition for debugging
        if settings.ENV == AppENV.LOCAL:
            logger.debug(f"Added security headers to {request.url.path}")

        return response
