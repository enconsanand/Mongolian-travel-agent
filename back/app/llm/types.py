"""Provider-neutral request and response types for the model gateway."""

from dataclasses import dataclass, field
from typing import Any, Literal

MessageRole = Literal["system", "user", "assistant", "tool"]


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class Message:
    role: MessageRole
    content: str = ""
    tool_calls: tuple[ToolCall, ...] = ()
    tool_call_id: str | None = None  # role=tool: the call this result answers
    name: str | None = None  # role=tool: the tool's name

    @classmethod
    def system(cls, content: str) -> "Message":
        return cls("system", content)

    @classmethod
    def user(cls, content: str) -> "Message":
        return cls("user", content)

    @classmethod
    def assistant(cls, content: str = "", tool_calls: tuple[ToolCall, ...] = ()) -> "Message":
        return cls("assistant", content, tool_calls)

    @classmethod
    def tool_result(cls, call: ToolCall, content: str) -> "Message":
        return cls("tool", content, tool_call_id=call.id, name=call.name)


@dataclass(frozen=True)
class ToolSpec:
    """A tool the model may call. ``parameters`` is a JSON Schema object."""

    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=lambda: {"type": "object", "properties": {}})


@dataclass(frozen=True)
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass(frozen=True)
class Completion:
    text: str = ""
    tool_calls: tuple[ToolCall, ...] = ()
    usage: Usage = Usage()
    provider: str = ""
    model: str = ""
