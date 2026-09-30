"""Errors raised by model providers and the gateway."""

from typing import Literal

LLMErrorCode = Literal[
    "not_configured",  # no provider or route for what was asked
    "unavailable",  # timeout, connection error, provider 5xx
    "rate_limited",  # provider 429 (Workers AI free allocation spent, for example)
    "refused",  # provider 4xx: bad request, unsupported model or option
    "bad_response",  # the reply could not be parsed, or called a tool that was not offered
    "schema_invalid",  # structured output did not validate after every attempt
    "all_failed",  # every route of a role failed
]


class LLMError(Exception):
    def __init__(
        self, code: LLMErrorCode, message: str = "", *, retryable: bool = False, status_code: int | None = None
    ) -> None:
        super().__init__(message or code)
        self.code: LLMErrorCode = code
        self.retryable = retryable
        self.status_code = status_code
