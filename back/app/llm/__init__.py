"""Model gateway: code asks for a role (``planner``, ``writer``), configuration picks provider and model.

Routes come from ``LLM_PLANNER`` / ``LLM_WRITER`` (``provider:model``, comma-separated fallbacks), with
redaction, tool-call checks, structured-output validation and usage metering in ``ModelGateway``.
Only ``app.modules.orchestrator`` may import this.
"""

from functools import lru_cache
from typing import TYPE_CHECKING

from app.llm.errors import LLMError, LLMErrorCode
from app.llm.gateway import ROLES, ModelGateway, RoleName, RolePolicy, Route, parse_routes
from app.llm.meter import UsageMeter
from app.llm.providers import FakeProvider, ModelProvider, OpenAICompatProvider, oyu_provider, workers_ai_provider
from app.llm.types import Completion, Message, ToolCall, ToolSpec, Usage

if TYPE_CHECKING:
    from app.core.config import Settings

__all__ = [
    "ROLES",
    "Completion",
    "FakeProvider",
    "LLMError",
    "LLMErrorCode",
    "Message",
    "ModelGateway",
    "ModelProvider",
    "OpenAICompatProvider",
    "RoleName",
    "RolePolicy",
    "Route",
    "ToolCall",
    "ToolSpec",
    "Usage",
    "UsageMeter",
    "build_gateway",
    "configured_gateway",
    "oyu_provider",
    "parse_routes",
    "workers_ai_provider",
]


def build_gateway(settings: "Settings") -> ModelGateway:
    routes = {"planner": parse_routes(settings.LLM_PLANNER), "writer": parse_routes(settings.LLM_WRITER)}
    used = {route.provider for role_routes in routes.values() for route in role_routes}
    providers: dict[str, ModelProvider] = {}
    if "workers_ai" in used:
        if not (settings.CLOUDFLARE_ACCOUNT_ID and settings.CLOUDFLARE_API_TOKEN):
            raise LLMError("not_configured", "workers_ai needs CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN")
        providers["workers_ai"] = workers_ai_provider(
            account_id=settings.CLOUDFLARE_ACCOUNT_ID,
            api_token=settings.CLOUDFLARE_API_TOKEN,
            gateway_id=settings.CLOUDFLARE_AI_GATEWAY,
            json_mode=settings.LLM_JSON_MODE,
            timeout=settings.LLM_TIMEOUT_SECONDS,
        )
    if "oyu" in used:
        if not settings.OYU_API_KEY:
            raise LLMError("not_configured", "oyu needs OYU_API_KEY")
        providers["oyu"] = oyu_provider(
            api_key=settings.OYU_API_KEY,
            json_mode=settings.OYU_JSON_MODE,
            timeout=settings.LLM_TIMEOUT_SECONDS,
        )
    if "fake" in used:
        providers["fake"] = FakeProvider()
    unknown = used - providers.keys()
    if unknown:
        raise LLMError("not_configured", f"unknown LLM providers: {sorted(unknown)}")
    policies = {
        role: RolePolicy(role_routes, max_tokens=settings.LLM_MAX_TOKENS) for role, role_routes in routes.items()
    }
    return ModelGateway(providers=providers, policies=policies)


def configured_gateway() -> ModelGateway:
    """The gateway chosen by settings (one per process: it holds HTTP clients and the usage meter)."""
    return _configured()


@lru_cache
def _configured() -> ModelGateway:
    from app.core.config import settings

    return build_gateway(settings)
