"""Workers AI / OpenAI-compatible adapter: wire format out, both response shapes in, errors mapped."""

import json

import httpx
import pytest

from app.llm import LLMError, Message, ToolCall, ToolSpec, workers_ai_provider
from app.llm.providers import OpenAICompatProvider, parse_completion
from app.llm.providers.openai_compat import message_to_wire

MODEL = "@cf/meta/llama-3.3-70b-instruct-fp8-fast"
TOOL = ToolSpec("find_stays_near", "Find stays", {"type": "object", "properties": {"place": {"type": "string"}}})


class Recorder:
    def __init__(self, *responses: httpx.Response | Exception) -> None:
        self.responses = list(responses)
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    @property
    def body(self) -> dict:
        return json.loads(self.requests[-1].content)


def openai_reply(content="", tool_calls=None, usage=(12, 3)):
    message = {"role": "assistant", "content": content}
    if tool_calls is not None:
        message["tool_calls"] = tool_calls
    return httpx.Response(
        200,
        json={
            "choices": [{"index": 0, "message": message, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": usage[0], "completion_tokens": usage[1]},
        },
    )


def provider(recorder, **kwargs):
    return workers_ai_provider(account_id="acc123", api_token="tok", transport=httpx.MockTransport(recorder), **kwargs)


def test_request_goes_to_the_openai_compatible_endpoint_with_tools():
    rec = Recorder(openai_reply("hi"))
    result = provider(rec).complete(model=MODEL, messages=[Message.system("s"), Message.user("u")], tools=[TOOL])

    req = rec.requests[0]
    assert str(req.url) == "https://api.cloudflare.com/client/v4/accounts/acc123/ai/v1/chat/completions"
    assert req.headers["authorization"] == "Bearer tok"
    assert "cf-aig-gateway-id" not in req.headers
    body = rec.body
    assert body["model"] == MODEL
    assert body["messages"] == [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}]
    assert body["tools"] == [
        {
            "type": "function",
            "function": {"name": "find_stays_near", "description": "Find stays", "parameters": TOOL.parameters},
        }
    ]
    assert "response_format" not in body
    assert result.text == "hi"
    assert (result.provider, result.model) == ("workers_ai", MODEL)
    assert (result.usage.input_tokens, result.usage.output_tokens) == (12, 3)


def test_ai_gateway_is_selected_by_header():
    rec = Recorder(openai_reply("ok"))
    provider(rec, gateway_id="mta").complete(model=MODEL, messages=[Message.user("u")])
    assert rec.requests[0].headers["cf-aig-gateway-id"] == "mta"


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("json_schema", {"type": "json_schema", "json_schema": {"name": "result", "schema": {"type": "object"}}}),
        ("json_object", {"type": "json_object"}),
        ("prompt", None),
    ],
)
def test_json_modes(mode, expected):
    rec = Recorder(openai_reply("{}"))
    provider(rec, json_mode=mode).complete(model=MODEL, messages=[Message.user("u")], json_schema={"type": "object"})
    assert rec.body.get("response_format") == expected


def test_tool_calls_with_string_arguments_are_parsed():
    rec = Recorder(
        openai_reply(
            None,
            [
                {
                    "id": "c1",
                    "type": "function",
                    "function": {"name": "find_stays_near", "arguments": '{"place": "Тэрэлж"}'},
                }
            ],
        )
    )
    result = provider(rec).complete(model=MODEL, messages=[Message.user("u")], tools=[TOOL])
    assert result.text == ""
    assert result.tool_calls == (ToolCall("c1", "find_stays_near", {"place": "Тэрэлж"}),)


def test_native_run_shape_is_parsed():
    data = {
        "success": True,
        "result": {
            "response": {"destination": "Terelj"},
            "tool_calls": [{"name": "find_stays_near", "arguments": {"place": "Terelj"}}, {"name": "noop"}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 7},
        },
    }
    result = parse_completion(data, provider="workers_ai", model=MODEL)
    assert json.loads(result.text) == {"destination": "Terelj"}
    assert result.tool_calls == (
        ToolCall("call_0", "find_stays_near", {"place": "Terelj"}),
        ToolCall("call_1", "noop", {}),
    )
    assert result.usage.output_tokens == 7


@pytest.mark.parametrize(
    ("response", "code", "retryable"),
    [
        (httpx.Response(429, json={"errors": [{"message": "daily free allocation used"}]}), "rate_limited", True),
        (httpx.Response(503, text="upstream"), "unavailable", True),
        (
            httpx.Response(400, json={"success": False, "errors": [{"code": 5006, "message": "bad input"}]}),
            "refused",
            False,
        ),
        (httpx.Response(401, json={"error": {"message": "bad token"}}), "refused", False),
        (httpx.Response(404, json={"error": "no such model"}), "refused", False),
        (
            httpx.Response(200, json={"success": False, "errors": [{"message": "JSON Mode couldn't be met"}]}),
            "refused",
            False,
        ),
        (httpx.Response(200, text="<html>"), "bad_response", False),
        (httpx.Response(200, json=["x"]), "bad_response", False),
        (httpx.Response(200, json={"choices": []}), "bad_response", False),
        (httpx.ReadTimeout("slow"), "unavailable", True),
        (httpx.ConnectError("down"), "unavailable", True),
    ],
)
def test_errors_are_mapped(response, code, retryable):
    with pytest.raises(LLMError) as err:
        provider(Recorder(response)).complete(model=MODEL, messages=[Message.user("u")])
    assert err.value.code == code
    assert err.value.retryable is retryable


def test_error_text_is_kept_for_diagnosis():
    with pytest.raises(LLMError, match="daily free allocation used"):
        provider(Recorder(httpx.Response(429, json={"errors": [{"message": "daily free allocation used"}]}))).complete(
            model=MODEL, messages=[Message.user("u")]
        )


@pytest.mark.parametrize(
    "call",
    [
        {"id": "c", "function": {"name": "x", "arguments": "{not json"}},
        {"id": "c", "function": {"name": "", "arguments": "{}"}},
        {"id": "c", "function": {"name": "x", "arguments": "[1]"}},
        "junk",
    ],
)
def test_malformed_tool_calls_are_bad_responses(call):
    with pytest.raises(LLMError) as err:
        provider(Recorder(openai_reply("", [call]))).complete(model=MODEL, messages=[Message.user("u")])
    assert err.value.code == "bad_response"


def test_multi_turn_tool_messages_use_the_openai_format():
    call = ToolCall("c1", "find_stays_near", {"place": "Тэрэлж"})
    assert message_to_wire(Message.assistant("", (call,))) == {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": "c1",
                "type": "function",
                "function": {"name": "find_stays_near", "arguments": '{"place": "Тэрэлж"}'},
            }
        ],
    }
    assert message_to_wire(Message.tool_result(call, "[]")) == {
        "role": "tool",
        "content": "[]",
        "tool_call_id": "c1",
        "name": "find_stays_near",
    }


def test_generic_provider_keeps_its_name_and_extra_headers():
    rec = Recorder(openai_reply("сайн"))
    generic = OpenAICompatProvider(
        name="other",
        base_url="https://llm.example/v1",
        api_key="k",
        headers={"X-Org": "mta"},
        transport=httpx.MockTransport(rec),
    )
    result = generic.complete(model="m", messages=[Message.user("u")])
    assert str(rec.requests[0].url) == "https://llm.example/v1/chat/completions"
    assert rec.requests[0].headers["x-org"] == "mta"
    assert result.provider == "other"
