"""Model gateway: routing and fallback, redaction, tool-call checks, structured output, configuration."""

from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from app.llm import (
    Completion,
    FakeProvider,
    LLMError,
    Message,
    ModelGateway,
    RolePolicy,
    Route,
    ToolCall,
    ToolSpec,
    Usage,
    build_gateway,
    parse_routes,
    smoke,
)
from app.llm.redaction import redact

TOOL = ToolSpec("find_stays_near", "Find stays")


def gateway(*providers: FakeProvider, **kwargs) -> ModelGateway:
    routes = tuple(Route(p.name, f"model-{p.name}") for p in providers)
    return ModelGateway(
        providers={p.name: p for p in providers},
        policies={"planner": RolePolicy(routes), "writer": RolePolicy(routes)},
        **kwargs,
    )


def test_routes_parse_model_ids_with_slashes_and_at_signs():
    assert Route.parse(" workers_ai:@cf/meta/llama-3.3-70b-instruct-fp8-fast ") == Route(
        "workers_ai", "@cf/meta/llama-3.3-70b-instruct-fp8-fast"
    )
    assert Route.parse("fake") == Route("fake", "fake")
    assert parse_routes("workers_ai:@cf/a, fake") == (Route("workers_ai", "@cf/a"), Route("fake", "fake"))
    with pytest.raises(ValueError):
        parse_routes(" , ")
    with pytest.raises(ValueError):
        Route.parse(":model")


def test_first_healthy_route_answers_and_usage_is_metered():
    primary = FakeProvider(Completion("hi", usage=Usage(10, 2)), name="primary")
    backup = FakeProvider(name="backup")
    gw = gateway(primary, backup)

    result = gw.complete("writer", [Message.user("сайн уу")])

    assert (result.text, result.provider, result.model) == ("hi", "primary", "model-primary")
    assert backup.requests == []
    assert gw.meter.snapshot() == [
        {
            "role": "writer",
            "provider": "primary",
            "model": "model-primary",
            "requests": 1,
            "failures": 0,
            "input_tokens": 10,
            "output_tokens": 2,
        }
    ]


def test_failed_route_falls_through_to_the_next():
    primary = FakeProvider(LLMError("rate_limited", "free allocation used", retryable=True), name="primary")
    backup = FakeProvider(Completion("from backup"), name="backup")
    gw = gateway(primary, backup)

    assert gw.complete("planner", [Message.user("x")]).text == "from backup"
    tallies = {row["provider"]: row for row in gw.meter.snapshot()}
    assert tallies["primary"]["failures"] == 1
    assert tallies["backup"]["requests"] == 1


def test_all_routes_failing_reports_each_one():
    gw = gateway(
        FakeProvider(LLMError("unavailable", "timeout", retryable=True), name="a"),
        FakeProvider(LLMError("refused", "bad model"), name="b"),
    )
    with pytest.raises(LLMError) as err:
        gw.complete("planner", [Message.user("x")])
    assert err.value.code == "all_failed"
    assert "a/model-a: unavailable" in str(err.value)
    assert "b/model-b: refused" in str(err.value)


def test_unconfigured_route_and_role():
    gw = ModelGateway(
        providers={"fake": FakeProvider(Completion("ok"))},
        policies={"planner": RolePolicy((Route("missing", "m"), Route("fake", "fake")))},
    )
    assert gw.complete("planner", [Message.user("x")]).text == "ok"
    with pytest.raises(LLMError) as err:
        gw.complete("writer", [Message.user("x")])
    assert err.value.code == "not_configured"


def test_tool_calls_outside_the_offered_tools_are_rejected():
    rogue = FakeProvider(Completion(tool_calls=(ToolCall("c", "start_payment", {}),)), name="rogue")
    honest = FakeProvider(
        Completion(tool_calls=(ToolCall("c", "find_stays_near", {"place": "Terelj"}),)), name="honest"
    )
    result = gateway(rogue, honest).complete("planner", [Message.user("x")], tools=[TOOL])
    assert result.provider == "honest"
    assert result.tool_calls[0].name == "find_stays_near"


def test_user_and_tool_content_is_redacted_before_it_leaves():
    fake = FakeProvider(name="fake")
    call = ToolCall("c", "find_stays_near", {})
    gateway(fake).complete(
        "writer",
        [
            Message.system("Operator phone 99112233 stays"),
            Message.user("Утас +976 8811-2233, имэйл bat.bold@mail.mn, карт 4111 1111 1111 1111"),
            Message.tool_result(call, "owner 95001122"),
        ],
    )
    sent = fake.requests[0]["messages"]
    assert sent[0].content == "Operator phone 99112233 stays"
    assert sent[1].content == "Утас [phone], имэйл [email], карт [number]"
    assert sent[2].content == "owner [phone]"


def test_redaction_can_be_turned_off():
    fake = FakeProvider(name="fake")
    gateway(fake, redact=False).complete("writer", [Message.user("99112233")])
    assert fake.requests[0]["messages"][0].content == "99112233"


@pytest.mark.parametrize("text", ["2026-10-05", "150000 төгрөг", "3 шөнө 2 хүн", "захиалга 12345"])
def test_redaction_leaves_dates_prices_and_counts(text):
    assert redact(text) == text


class Intent(BaseModel):
    destination: str
    nights: int


def test_structured_output_is_validated_and_repaired_once():
    fake = FakeProvider(
        Completion('Sure! {"destination": "Terelj"}'),
        Completion('```json\n{"destination": "Terelj", "nights": 2}\n```'),
    )
    gw = gateway(fake)

    intent = gw.structured("planner", [Message.system("You plan."), Message.user("Тэрэлж 2 шөнө")], Intent)

    assert intent == Intent(destination="Terelj", nights=2)
    first, second = fake.requests
    assert first["json_schema"] == Intent.model_json_schema()
    assert first["messages"][0].role == "system"
    assert first["messages"][0].content.startswith("You plan.\n\nReply with a single JSON object")
    assert len(first["messages"]) == 2
    assert "nights: Field required" in second["messages"][-1].content


def test_structured_output_gives_up_after_the_attempts():
    gw = gateway(FakeProvider(Completion("no"), Completion("still no"), name="fake"))
    with pytest.raises(LLMError) as err:
        gw.structured("planner", [Message.user("x")], Intent)
    assert err.value.code == "schema_invalid"


def test_structured_output_adds_a_system_message_when_there_is_none():
    fake = FakeProvider(Completion('{"destination": "Khuvsgul", "nights": 3}'))
    gateway(fake).structured("planner", [Message.user("x")], Intent)
    assert [m.role for m in fake.requests[0]["messages"]] == ["system", "user"]


def test_fake_provider_defaults_and_callable_steps():
    fake = FakeProvider()
    assert fake.complete(model="m", messages=[Message.user("сайн уу")]).text == "[fake] сайн уу"
    assert fake.complete(model="m", messages=[Message.user("x")], json_schema={}).text == "{}"
    fake.push(lambda messages, tools: Completion(f"{len(messages)} msgs, {len(tools)} tools"))
    assert fake.complete(model="m", messages=[Message.user("x")], tools=[TOOL]).text == "1 msgs, 1 tools"


def _settings(**overrides):
    base = dict(
        LLM_PLANNER="fake",
        LLM_WRITER="fake",
        LLM_MAX_TOKENS=256,
        LLM_TIMEOUT_SECONDS=5.0,
        LLM_JSON_MODE="prompt",
        CLOUDFLARE_ACCOUNT_ID=None,
        CLOUDFLARE_API_TOKEN=None,
        CLOUDFLARE_AI_GATEWAY=None,
    )
    return SimpleNamespace(**{**base, **overrides})


def test_build_gateway_from_settings():
    gw = build_gateway(_settings())
    assert gw.complete("writer", [Message.user("сайн уу")]).text == "[fake] сайн уу"

    gw = build_gateway(
        _settings(
            LLM_PLANNER="workers_ai:@cf/meta/llama-3.3-70b-instruct-fp8-fast,fake",
            CLOUDFLARE_ACCOUNT_ID="acc",
            CLOUDFLARE_API_TOKEN="tok",
        )
    )
    assert set(gw._providers) == {"workers_ai", "fake"}

    with pytest.raises(LLMError, match="CLOUDFLARE_ACCOUNT_ID"):
        build_gateway(_settings(LLM_WRITER="workers_ai:@cf/x"))
    with pytest.raises(LLMError, match="unknown LLM providers"):
        build_gateway(_settings(LLM_WRITER="openai:gpt"))


def test_smoke_script_runs_every_check(monkeypatch, capsys):
    fake = FakeProvider(
        Completion(tool_calls=(ToolCall("c", "find_stays_near", {"place": "Terelj", "nights": 2, "guests": 2}),)),
        Completion('{"destination": "Terelj", "nights": 2, "guests": 2, "language": "mn"}'),
        Completion("Тэрэлжид 2 шөнө байх газрууд байна."),
    )
    monkeypatch.setattr(smoke, "configured_gateway", lambda: gateway(fake))
    assert smoke.main(smoke.DEFAULT_PROMPT) == 0
    out = capsys.readouterr().out
    assert "tool: find_stays_near" in out
    assert "'destination': 'Terelj'" in out
    assert "Тэрэлжид 2 шөнө" in out

    failing = FakeProvider(*(LLMError("rate_limited", "used", retryable=True) for _ in range(3)))
    monkeypatch.setattr(smoke, "configured_gateway", lambda: gateway(failing))
    assert smoke.main("x") == 1
    assert "FAILED: all_failed" in capsys.readouterr().out
