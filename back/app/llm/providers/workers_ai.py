"""Cloudflare Workers AI through its OpenAI-compatible endpoint.

Free allocation: 10,000 neurons a day on any Workers plan (about 60 agent turns on Llama 3.3 70B); a 429 then
lets the gateway fall back. With ``gateway_id`` requests go through Cloudflare AI Gateway (caching, logs).
Model ids keep the ``@cf/`` prefix, for example ``@cf/meta/llama-3.3-70b-instruct-fp8-fast``.
"""

import httpx

from app.llm.providers.openai_compat import JsonMode, OpenAICompatProvider

WORKERS_AI_BASE = "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1"


def workers_ai_provider(
    *,
    account_id: str,
    api_token: str,
    gateway_id: str | None = None,
    json_mode: JsonMode = "json_schema",
    transport: httpx.BaseTransport | None = None,
    timeout: float = 60.0,
) -> OpenAICompatProvider:
    return OpenAICompatProvider(
        name="workers_ai",
        base_url=WORKERS_AI_BASE.format(account_id=account_id),
        api_key=api_token,
        headers={"cf-aig-gateway-id": gateway_id} if gateway_id else None,
        json_mode=json_mode,
        transport=transport,
        timeout=timeout,
    )
