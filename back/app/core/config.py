import json
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import AnyHttpUrl, Field, computed_field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class AppENV(str, Enum):
    """Application environment enumeration."""

    LOCAL = "local"
    DEV = "dev"
    STG = "stg"
    PROD = "prod"

    @property
    def is_production(self) -> bool:
        return self in (AppENV.STG, AppENV.PROD)

    @property
    def is_development(self) -> bool:
        return self in (AppENV.LOCAL, AppENV.DEV)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Application ---
    ENV: AppENV = Field(default=AppENV.LOCAL, description="Current application environment")
    PROJECT_NAME: str = Field(..., description="Name of the project")
    API_V1_STR: str = Field(default="/api/v1", description="API version prefix")

    # --- CORS ---
    # NoDecode: pydantic-settings would otherwise JSON-decode this list before the validator runs.
    BACKEND_CORS_ORIGINS: Annotated[list[AnyHttpUrl], NoDecode] = Field(default=[], description="Allowed CORS origins")

    # --- JWT Configuration ---
    JWT_SECRET: str = Field(..., min_length=32, description="Secret key for JWT generation")
    ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=60 * 8, description="Access token expiration in minutes (default 8h)"
    )

    # --- Timezone & Localization ---
    TIMEZONE: str = Field(default="UTC", description="Application timezone")

    # --- Request Limits ---
    MAX_REQUEST_BODY_BYTES: int = Field(
        default=10 * 1024 * 1024,
        description="Maximum request body size in bytes, enforced even for chunked bodies",
    )

    # --- Rate Limiting ---
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = Field(default=60, description="Global rate limit")
    RATE_LIMIT_AUTH_REQUESTS_PER_MINUTE: int = Field(default=5, description="Auth-specific rate limit")
    LOGIN_MAX_FAILED_ATTEMPTS: int = Field(
        default=10, description="Failed logins per account before a temporary lockout"
    )
    LOGIN_FAILED_ATTEMPTS_WINDOW_SECONDS: int = Field(
        default=60, description="Sliding window in seconds for the per-account failed-login lockout"
    )
    REDIS_URL: str | None = Field(
        default=None,
        description="Redis URL for distributed rate limiting across workers; in-memory fallback if unset",
    )

    # --- Proxy ---
    TRUST_PROXY_HEADERS: bool = Field(
        default=False,
        description=(
            "Trust X-Forwarded-For / X-Real-IP headers. Enable ONLY behind a single trusted "
            "reverse proxy that appends the real client IP as the last X-Forwarded-For entry."
        ),
    )

    # --- Database (MongoDB) ---
    MONGO_URI: str = Field(
        default="mongodb://mongo:27017/?directConnection=true",
        description=(
            "MongoDB connection string (local replica-set container or Atlas SRV URI). "
            "Must point at a replica set: the booking saga and outbox use transactions and change streams."
        ),
    )
    MONGO_DB_NAME: str = Field(default="travel_mn", description="MongoDB database name")
    MONGO_INIT_ON_STARTUP: bool = Field(
        default=True, description="Create missing indexes when the app starts (idempotent)"
    )
    # --- Payments ---
    # sim: the QPay adapter against the qpay-sim service; qpay: real QPay Merchant V2 (sandbox or production)
    PAYMENT_RAIL: Literal["sim", "qpay", "bonum"] = Field(default="sim", description="Payment rail in use")
    QPAY_BASE_URL: str = Field(default="http://qpay-sim:8010", description="QPay Merchant V2 base URL")
    QPAY_USERNAME: str = Field(default="sim_merchant", description="QPay merchant username")
    QPAY_PASSWORD: str = Field(default="sim_password", description="QPay merchant password")
    QPAY_INVOICE_CODE: str = Field(default="SIM_INVOICE", description="QPay invoice code of the merchant")
    # AP2 merchant of record: the platform signs checkouts with this key; payee id in every Payment Mandate
    MERCHANT_ID: str = Field(default="merchant_mta", description="Merchant id used as AP2 payee")
    MERCHANT_KEY_PEM: str | None = Field(default=None, description="PKCS#8 EC P-256 private key (PEM)")
    # Where payment rails reach our webhooks (the compose service name for qpay-sim; a public URL for QPay)
    PUBLIC_BASE_URL: str = Field(default="http://back:8000", description="Base URL for payment callbacks")

    MOCK_DATA_DIR: str = Field(
        default=str(Path(__file__).resolve().parents[3] / "data" / "mock"),
        description="Folder with the mock-data JSON collections loaded by the seeder",
    )

    @computed_field
    @property
    def OPENAPI_URL(self) -> str | None:
        """Disable OpenAPI in production environments."""
        if self.ENV.is_production:
            return None
        return f"{self.API_V1_STR}/openapi.json"

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str] | str:
        """Parse CORS origins from a comma-separated string or a JSON list."""
        if not isinstance(v, str):
            return v
        value = v.strip()
        if not value:
            return []
        if value.startswith("["):
            parsed = json.loads(value)
            if not isinstance(parsed, list):
                raise ValueError("BACKEND_CORS_ORIGINS JSON value must be a list")
            return parsed
        return [item.strip() for item in value.split(",") if item.strip()]

    @model_validator(mode="after")
    def _require_redis_in_production(self) -> "Settings":
        """Rate limiting and token revocation only work across workers with Redis."""
        if self.ENV.is_production and not self.REDIS_URL:
            raise ValueError("REDIS_URL must be set when ENV is 'stg' or 'prod'")
        # The default points at the local dev container; production must say where its database is
        if self.ENV.is_production and "MONGO_URI" not in self.model_fields_set:
            raise ValueError("MONGO_URI must be set when ENV is 'stg' or 'prod'")
        # The simulator must never stand in for real payments outside development
        if self.ENV.is_production and self.PAYMENT_RAIL == "sim":
            raise ValueError("PAYMENT_RAIL=sim is not allowed when ENV is 'stg' or 'prod'")
        if self.ENV.is_production and not self.MERCHANT_KEY_PEM:
            raise ValueError("MERCHANT_KEY_PEM must be set when ENV is 'stg' or 'prod'")
        return self


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
