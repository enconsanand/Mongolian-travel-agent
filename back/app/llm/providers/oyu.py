"""oyu (https://dev.oyu.so) through its OpenAI-compatible endpoint.

``oyuLLM`` is a Mongolian model with OpenAI-style tool calling, so it can serve both roles: the planner (tools and
structured output) and the writer (the Mongolian reply). Its docs do not promise ``response_format``, so structured
output defaults to asking in the prompt; the gateway validates the JSON either way.
"""

import httpx

from app.llm.providers.openai_compat import JsonMode, OpenAICompatProvider

OYU_BASE = "https://api.oyu.so/v1"


def oyu_provider(
    *,
    api_key: str,
    json_mode: JsonMode = "prompt",
    transport: httpx.BaseTransport | None = None,
    timeout: float = 60.0,
) -> OpenAICompatProvider:
    return OpenAICompatProvider(
        name="oyu",
        base_url=OYU_BASE,
        api_key=api_key,
        json_mode=json_mode,
        transport=transport,
        timeout=timeout,
    )
