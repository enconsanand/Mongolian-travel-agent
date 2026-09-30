"""Model gateway: callers ask for a role, configuration picks provider and model.

Roles:
- ``planner``: tool calling and structured output (Workers AI today).
- ``writer``: the reply the user reads, in Mongolian (Workers AI until the Mongolian LLM adapter lands).

Each role has an ordered list of routes; a failed route falls through to the next. User and tool content is
redacted before it leaves the process, tool calls are checked against the tools offered (arguments are coerced
to the tool's schema: Workers AI sends "2" for an integer), and structured output is validated with Pydantic
and repaired once.
"""

import json
import logging
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, ValidationError, create_model

from app.llm.errors import LLMError
from app.llm.meter import UsageMeter
from app.llm.providers.base import ModelProvider
from app.llm.redaction import redact_message
from app.llm.types import Completion, Message, ToolCall, ToolSpec

log = logging.getLogger(__name__)

RoleName = Literal["planner", "writer"]
ROLES: tuple[RoleName, ...] = ("planner", "writer")
M = TypeVar("M", bound=BaseModel)

_FENCE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)


@dataclass(frozen=True)
class Route:
    provider: str
    model: str

    @classmethod
    def parse(cls, spec: str) -> "Route":
        """``provider:model``; the model id may itself contain ``/`` and ``@``. ``fake`` alone is allowed."""
        provider, _, model = spec.strip().partition(":")
        if not provider:
            raise ValueError(f"route {spec!r} has no provider")
        return cls(provider, model or provider)


def parse_routes(spec: str) -> tuple[Route, ...]:
    routes = tuple(Route.parse(part) for part in spec.split(",") if part.strip())
    if not routes:
        raise ValueError("at least one route is required")
    return routes


@dataclass(frozen=True)
class RolePolicy:
    routes: tuple[Route, ...]
    max_tokens: int = 1024
    temperature: float = 0.2


class ModelGateway:
    def __init__(
        self,
        *,
        providers: Mapping[str, ModelProvider],
        policies: Mapping[str, RolePolicy],
        meter: UsageMeter | None = None,
        redact: bool = True,
    ) -> None:
        self._providers = dict(providers)
        self._policies = dict(policies)
        self.meter = meter or UsageMeter()
        self._redact = redact

    def complete(
        self,
        role: RoleName,
        messages: Sequence[Message],
        *,
        tools: Sequence[ToolSpec] = (),
        json_schema: dict[str, Any] | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> Completion:
        policy = self._policies.get(role)
        if policy is None:
            raise LLMError("not_configured", f"no routes for role {role!r}")
        outgoing = [redact_message(m) for m in messages] if self._redact else list(messages)
        offered = {t.name: t for t in tools}
        failures: list[str] = []
        for route in policy.routes:
            provider = self._providers.get(route.provider)
            if provider is None:
                failures.append(f"{route.provider}: not configured")
                continue
            try:
                result = provider.complete(
                    model=route.model,
                    messages=outgoing,
                    tools=tools,
                    max_tokens=max_tokens or policy.max_tokens,
                    temperature=policy.temperature if temperature is None else temperature,
                    json_schema=json_schema,
                )
                unknown = [c.name for c in result.tool_calls if c.name not in offered]
                if unknown:
                    raise LLMError("bad_response", f"called tools that were not offered: {unknown}")
                result = replace(result, tool_calls=tuple(_checked_call(c, offered[c.name]) for c in result.tool_calls))
            except LLMError as exc:
                self.meter.failure(role, route.provider, route.model)
                failures.append(f"{route.provider}/{route.model}: {exc.code} {exc}")
                log.warning("llm %s failed on %s/%s: %s %s", role, route.provider, route.model, exc.code, exc)
                continue
            self.meter.record(role, route.provider, route.model, result.usage)
            log.info(
                "llm %s via %s/%s: %d in, %d out, %d tool calls",
                role,
                route.provider,
                route.model,
                result.usage.input_tokens,
                result.usage.output_tokens,
                len(result.tool_calls),
            )
            return result
        raise LLMError("all_failed", f"{role}: " + " | ".join(failures))

    def structured(self, role: RoleName, messages: Sequence[Message], output: type[M], *, attempts: int = 2) -> M:
        """Ask for one JSON object matching ``output``; on invalid output, show the error and ask again."""
        schema = output.model_json_schema()
        conversation = _with_json_instruction(messages, schema)
        error = ""
        for _ in range(max(attempts, 1)):
            result = self.complete(role, conversation, json_schema=schema)
            try:
                return output.model_validate_json(_extract_json(result.text))
            except ValidationError as exc:
                error = _short(exc)
            conversation = [
                *conversation,
                Message.assistant(result.text),
                Message.user(f"That reply was not valid: {error}. Reply with the JSON object only."),
            ]
        raise LLMError("schema_invalid", f"{role}: {output.__name__}: {error}")


_JSON_TYPES: dict[str, Any] = {"string": str, "integer": int, "number": float, "boolean": bool, "array": list}


def _arguments_model(tool: ToolSpec) -> type[BaseModel]:
    """A lax Pydantic model of the tool's top-level properties, so ``"2"`` becomes ``2`` for an integer."""
    schema = tool.parameters
    required = set(schema.get("required", []))
    fields: dict[str, Any] = {}
    for name, prop in schema.get("properties", {}).items():
        annotation = _JSON_TYPES.get(prop.get("type", ""), Any)
        bounds = {"ge": prop.get("minimum"), "le": prop.get("maximum")}
        default = ... if name in required else None
        if name not in required:
            annotation = annotation | None
        fields[name] = (annotation, Field(default, **{k: v for k, v in bounds.items() if v is not None}))
    return create_model(f"{tool.name}_arguments", __config__=ConfigDict(extra="allow"), **fields)


def _checked_call(call: ToolCall, tool: ToolSpec) -> ToolCall:
    try:
        arguments = _arguments_model(tool).model_validate(call.arguments)
    except ValidationError as exc:
        raise LLMError("bad_response", f"arguments for {call.name!r} do not fit its schema: {_short(exc)}") from exc
    return replace(call, arguments=arguments.model_dump(exclude_unset=True))


def _with_json_instruction(messages: Sequence[Message], schema: dict[str, Any]) -> list[Message]:
    instruction = "Reply with a single JSON object that matches this JSON Schema, and nothing else:\n" + json.dumps(
        schema, ensure_ascii=False
    )
    if messages and messages[0].role == "system":
        return [Message.system(f"{messages[0].content}\n\n{instruction}"), *messages[1:]]
    return [Message.system(instruction), *messages]


def _extract_json(text: str) -> str:
    text = text.strip()
    fenced = _FENCE.match(text)
    if fenced:
        text = fenced.group(1)
    if not text.startswith("{"):
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            text = text[start : end + 1]
    return text


def _short(exc: ValidationError) -> str:
    return "; ".join(f"{'.'.join(map(str, e['loc'])) or 'value'}: {e['msg']}" for e in exc.errors()[:5])
