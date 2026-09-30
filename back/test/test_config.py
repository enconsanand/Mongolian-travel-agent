"""Unit tests for Settings validation (no database required)."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings

PROD_LLM = {
    "LLM_PLANNER": "workers_ai:@cf/meta/llama-3.3-70b-instruct-fp8-fast",
    "LLM_WRITER": "workers_ai:@cf/meta/llama-3.3-70b-instruct-fp8-fast",
    "CLOUDFLARE_ACCOUNT_ID": "acc",
    "CLOUDFLARE_API_TOKEN": "token",
}


def test_settings_requires_redis_in_production():
    # Rate limiting and token revocation only work across workers with Redis,
    # so production/staging must not silently fall back to per-process state.
    with pytest.raises(ValidationError):
        Settings(ENV="prod", REDIS_URL=None)


def test_settings_allows_missing_redis_outside_production():
    settings_obj = Settings(ENV="local", REDIS_URL=None)
    assert settings_obj.REDIS_URL is None


def test_settings_allows_redis_in_production():
    settings_obj = Settings(
        ENV="prod",
        REDIS_URL="redis://redis:6379/0",
        MONGO_URI="mongodb+srv://cluster/db",
        PAYMENT_RAIL="qpay",
        MERCHANT_KEY_PEM="-----BEGIN PRIVATE KEY-----",
        **PROD_LLM,
    )
    assert settings_obj.REDIS_URL == "redis://redis:6379/0"


def _required_settings_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROJECT_NAME", "test")
    monkeypatch.setenv("JWT_SECRET", "x" * 32)
    monkeypatch.setenv("ENV", "local")


def test_settings_parses_comma_separated_cors_origins(monkeypatch: pytest.MonkeyPatch):
    _required_settings_env(monkeypatch)
    monkeypatch.setenv("BACKEND_CORS_ORIGINS", "http://localhost:3000, http://127.0.0.1:3000")

    settings_obj = Settings()

    assert [str(origin).rstrip("/") for origin in settings_obj.BACKEND_CORS_ORIGINS] == [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


def test_settings_requires_mongo_uri_in_production():
    # The default points at the local dev container; production must not silently use it
    with pytest.raises(ValidationError):
        Settings(ENV="prod", REDIS_URL="redis://redis:6379/0")


def test_settings_defaults_mongo_uri_outside_production():
    assert Settings(ENV="local").MONGO_URI == "mongodb://mongo:27017/?directConnection=true"


def test_payment_simulator_is_refused_in_production():
    with pytest.raises(ValidationError, match="PAYMENT_RAIL"):
        Settings(ENV="prod", REDIS_URL="redis://redis:6379/0", MONGO_URI="mongodb+srv://cluster/db")


def test_payment_rail_defaults_to_the_simulator_locally():
    assert Settings(ENV="local").PAYMENT_RAIL == "sim"


def test_merchant_key_is_required_in_production():
    with pytest.raises(ValidationError, match="MERCHANT_KEY_PEM"):
        Settings(ENV="prod", REDIS_URL="redis://redis:6379/0", MONGO_URI="mongodb+srv://c/db", PAYMENT_RAIL="qpay")


def test_llm_defaults_to_the_fake_provider_locally():
    settings_obj = Settings(ENV="local")
    assert settings_obj.LLM_PLANNER == "fake"
    assert settings_obj.LLM_WRITER == "fake"


def test_fake_llm_is_refused_in_production():
    base = {
        "ENV": "prod",
        "REDIS_URL": "redis://redis:6379/0",
        "MONGO_URI": "mongodb+srv://c/db",
        "PAYMENT_RAIL": "qpay",
        "MERCHANT_KEY_PEM": "-----BEGIN PRIVATE KEY-----",
    }
    with pytest.raises(ValidationError, match="fake provider"):
        Settings(**base, **{**PROD_LLM, "LLM_WRITER": "workers_ai:@cf/x,fake"})


def test_workers_ai_needs_cloudflare_credentials():
    with pytest.raises(ValidationError, match="CLOUDFLARE_ACCOUNT_ID"):
        Settings(ENV="local", LLM_PLANNER="workers_ai:@cf/meta/llama-3.3-70b-instruct-fp8-fast")


def test_unknown_llm_provider_is_refused():
    with pytest.raises(ValidationError, match="unknown providers"):
        Settings(ENV="local", LLM_WRITER="openai:gpt")
    with pytest.raises(ValidationError, match="at least one provider"):
        Settings(ENV="local", LLM_PLANNER=" , ")
