"""Unit tests for Settings validation (no database required)."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_requires_redis_in_production():
    # Rate limiting and token revocation only work across workers with Redis,
    # so production/staging must not silently fall back to per-process state.
    with pytest.raises(ValidationError):
        Settings(ENV="prod", REDIS_URL=None)


def test_settings_allows_missing_redis_outside_production():
    settings_obj = Settings(ENV="local", REDIS_URL=None)
    assert settings_obj.REDIS_URL is None


def test_settings_allows_redis_in_production():
    settings_obj = Settings(ENV="prod", REDIS_URL="redis://redis:6379/0")
    assert settings_obj.REDIS_URL == "redis://redis:6379/0"


def _required_settings_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROJECT_NAME", "test")
    monkeypatch.setenv("JWT_SECRET", "x" * 32)
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_USER", "postgres")
    monkeypatch.setenv("DB_PASS", "postgres")
    monkeypatch.setenv("DB_NAME", "test")
    monkeypatch.setenv("ENV", "local")


def test_settings_parses_comma_separated_cors_origins(monkeypatch: pytest.MonkeyPatch):
    _required_settings_env(monkeypatch)
    monkeypatch.setenv("BACKEND_CORS_ORIGINS", "http://localhost:3000, http://127.0.0.1:3000")

    settings_obj = Settings()

    assert [str(origin).rstrip("/") for origin in settings_obj.BACKEND_CORS_ORIGINS] == [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
