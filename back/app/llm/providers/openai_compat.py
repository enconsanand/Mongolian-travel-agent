"""Chat Completions in the OpenAI wire format.

Cloudflare Workers AI serves this at ``/accounts/{id}/ai/v1/chat/completions``, and many other providers speak
the same format, so one adapter covers them. The parser also accepts the Workers AI native ``/ai/run`` shape
(``result.response`` and ``result.tool_calls``), so switching endpoints does not break parsing.
"""

import json
from collections.abc import Mapping, Sequence
from typing import Any, Literal

import httpx

from app.llm.errors import LLMError
from app.llm.types import Completion, Message, ToolCall, ToolSpec, Usage

# How structured output is requested: a JSON Schema, plain JSON mode, or only the prompt (for providers that
# reject response_format). The gateway validates the result either way.
JsonMode = Literal["json_schema", "json_object", "prompt"]


class OpenAICompatProvider:
    def __init__(
        self,
        *,
        name: str,
        base_url: str,
        api_key: str,
        headers: Mapping[str, str] | None = None,
        path: str = "/chat/completions",
        json_mode: JsonMode = "json_schema",
        transport: httpx.BaseTransport | None = None,
        timeout: float = 60.0,
    ) -> None:
        self.name = name
        self._client = httpx.Client(base_url=base_url, timeout=timeout, transport=transport)
        self._path = path
        self._headers = {"Authorization": f"Bearer {api_key}", **(headers or {})}
        self._json_mode = json_mode

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
        body: dict[str, Any] = {
            "model": model,
            "messages": [message_to_wire(m) for m in messages],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if tools:
            body["tools"] = [tool_to_wire(t) for t in tools]
        if json_schema is not None and self._json_mode == "json_schema":
            body["response_format"] = {"type": "json_schema", "json_schema": {"name": "result", "schema": json_schema}}
        elif json_schema is not None and self._json_mode == "json_object":
            body["response_format"] = {"type": "json_object"}
        return parse_completion(self._post(body), provider=self.name, model=model)

    def _post(self, body: dict[str, Any]) -> dict[str, Any]:
        try:
            resp = self._client.post(self._path, json=body, headers=self._headers)
        except httpx.TimeoutException as exc:
            raise LLMError("unavailable", f"{self.name} timed out", retryable=True) from exc
        except httpx.HTTPError as exc:
            raise LLMError("unavailable", f"{self.name}: {exc}", retryable=True) from exc
        status = resp.status_code
        if status == 429:
            raise LLMError("rate_limited", f"{self.name}: {_error_text(resp)}", retryable=True, status_code=status)
        if status >= 500:
            raise LLMError(
                "unavailable", f"{self.name} {status}: {_error_text(resp)}", retryable=True, status_code=status
            )
        if status >= 400:
            raise LLMError("refused", f"{self.name} {status}: {_error_text(resp)}", status_code=status)
        try:
            data = resp.json()
        except ValueError as exc:
            raise LLMError("bad_response", f"{self.name} returned non-JSON") from exc
        if not isinstance(data, dict):
            raise LLMError("bad_response", f"{self.name} returned {type(data).__name__}")
        if data.get("success") is False:  # Cloudflare envelope
            raise LLMError("refused", f"{self.name}: {_cf_errors(data)}")
        return data


def message_to_wire(m: Message) -> dict[str, Any]:
    wire: dict[str, Any] = {"role": m.role, "content": m.content}
    if m.tool_calls:
        wire["tool_calls"] = [
            {
                "id": c.id,
                "type": "function",
                "function": {"name": c.name, "arguments": json.dumps(c.arguments, ensure_ascii=False)},
            }
            for c in m.tool_calls
        ]
    if m.role == "tool":
        wire["tool_call_id"] = m.tool_call_id
        if m.name:
            wire["name"] = m.name
    return wire


def tool_to_wire(t: ToolSpec) -> dict[str, Any]:
    return {"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.parameters}}


def parse_completion(data: dict[str, Any], *, provider: str, model: str) -> Completion:
    body = data["result"] if isinstance(data.get("result"), dict) else data
    if "choices" in body:
        choices = body["choices"]
        if not choices or not isinstance(choices[0], dict):
            raise LLMError("bad_response", f"{provider} returned no choices")
        message = choices[0].get("message") or {}
        text: Any = message.get("content") or ""
        raw_calls = message.get("tool_calls") or []
    else:
        text = body.get("response") or ""
        raw_calls = body.get("tool_calls") or []
    if not isinstance(text, str):  # Workers AI JSON mode returns the object itself
        text = json.dumps(text, ensure_ascii=False)
    usage = body.get("usage") or {}
    return Completion(
        text=text,
        tool_calls=tuple(_tool_call(c, i, provider) for i, c in enumerate(raw_calls)),
        usage=Usage(int(usage.get("prompt_tokens") or 0), int(usage.get("completion_tokens") or 0)),
        provider=provider,
        model=model,
    )


def _tool_call(raw: Any, index: int, provider: str) -> ToolCall:
    if not isinstance(raw, dict):
        raise LLMError("bad_response", f"{provider} returned a malformed tool call")
    fn = raw["function"] if isinstance(raw.get("function"), dict) else raw
    name = fn.get("name")
    args: Any = fn.get("arguments") or {}
    if isinstance(args, str):
        try:
            args = json.loads(args) if args.strip() else {}
        except ValueError as exc:
            raise LLMError("bad_response", f"{provider}: tool arguments for {name!r} are not JSON") from exc
    if not isinstance(name, str) or not name or not isinstance(args, dict):
        raise LLMError("bad_response", f"{provider} returned a malformed tool call")
    return ToolCall(id=str(raw.get("id") or f"call_{index}"), name=name, arguments=args)


def _error_text(resp: httpx.Response) -> str:
    try:
        data = resp.json()
    except ValueError:
        return resp.text[:300]
    if isinstance(data, dict):
        if data.get("errors"):
            return _cf_errors(data)
        err = data.get("error")
        if isinstance(err, dict):
            return str(err.get("message", err))[:300]
        if err:
            return str(err)[:300]
    return str(data)[:300]


def _cf_errors(data: dict[str, Any]) -> str:
    errors = data.get("errors") or []
    return "; ".join(str(e.get("message", e)) if isinstance(e, dict) else str(e) for e in errors)[:300] or "failed"
