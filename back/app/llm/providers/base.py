from collections.abc import Sequence
from typing import Any, Protocol

from app.llm.types import Completion, Message, ToolSpec


class ModelProvider(Protocol):
    name: str

    def complete(
        self,
        *,
        model: str,
        messages: Sequence[Message],
        tools: Sequence[ToolSpec] = (),
        max_tokens: int = 1024,
        temperature: float = 0.2,
        json_schema: dict[str, Any] | None = None,
    ) -> Completion:
        """One chat completion. Raises ``LLMError``; ``retryable`` marks failures another route may not share."""
        ...
