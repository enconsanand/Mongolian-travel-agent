"""Scripted provider for tests and offline demos.

Queue replies with ``push``: a ``Completion``, an ``LLMError`` to raise, or a function of
``(messages, tools)`` returning a ``Completion``. With nothing queued it echoes the last user message
(``{}`` when structured output is asked), so the app runs with no credentials at all.
"""

from collections import deque
from collections.abc import Callable, Sequence
from dataclasses import replace
from typing import Any

from app.llm.errors import LLMError
from app.llm.types import Completion, Message, ToolSpec

Step = Completion | LLMError | Callable[[Sequence[Message], Sequence[ToolSpec]], Completion]


class FakeProvider:
    def __init__(self, *steps: Step, name: str = "fake") -> None:
        self.name = name
        self._steps: deque[Step] = deque(steps)
        self.requests: list[dict[str, Any]] = []

    def push(self, *steps: Step) -> None:
        self._steps.extend(steps)

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
        self.requests.append(
            {"model": model, "messages": list(messages), "tools": list(tools), "json_schema": json_schema}
        )
        if not self._steps:
            last = next((m.content for m in reversed(messages) if m.role == "user"), "")
            return Completion(
                text="{}" if json_schema is not None else f"[fake] {last}", provider=self.name, model=model
            )
        step = self._steps.popleft()
        if isinstance(step, LLMError):
            raise step
        if not isinstance(step, Completion):
            step = step(messages, tools)
        return replace(step, provider=self.name, model=model)
