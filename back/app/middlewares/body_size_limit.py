import logging

from fastapi import HTTPException, status
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import settings

logger = logging.getLogger(__name__)


class BodySizeLimitMiddleware:
    """
    Pure-ASGI middleware enforcing a maximum request body size.

    Counts bytes as they arrive, so chunked transfer encoding (which carries
    no Content-Length header) cannot bypass the limit. Requests with an
    oversized declared Content-Length are rejected before any body is read.
    """

    def __init__(self, app: ASGIApp, max_body_size: int | None = None):
        self.app = app
        self.max_body_size = max_body_size if max_body_size is not None else settings.MAX_REQUEST_BODY_BYTES

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        declared_size = self._declared_content_length(scope)
        if declared_size is not None and declared_size > self.max_body_size:
            response = JSONResponse(
                {"detail": "Request body too large"},
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )
            await response(scope, receive, send)
            return

        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_body_size:
                    logger.warning("Request body exceeded %d bytes, rejecting", self.max_body_size)
                    # Raised while the endpoint reads the body stream; converted
                    # to a 413 response by FastAPI's exception handling.
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="Request body too large",
                    )
            return message

        await self.app(scope, limited_receive, send)

    @staticmethod
    def _declared_content_length(scope: Scope) -> int | None:
        for name, value in scope.get("headers") or []:
            if name == b"content-length":
                try:
                    return int(value)
                except ValueError:
                    return None
        return None
