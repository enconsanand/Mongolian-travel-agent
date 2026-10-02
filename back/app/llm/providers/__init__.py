"""Model providers behind one ``ModelProvider`` protocol."""

from app.llm.providers.base import ModelProvider
from app.llm.providers.fake import FakeProvider
from app.llm.providers.openai_compat import OpenAICompatProvider, parse_completion
from app.llm.providers.oyu import OYU_BASE, oyu_provider
from app.llm.providers.workers_ai import WORKERS_AI_BASE, workers_ai_provider

__all__ = [
    "OYU_BASE",
    "WORKERS_AI_BASE",
    "FakeProvider",
    "ModelProvider",
    "OpenAICompatProvider",
    "oyu_provider",
    "parse_completion",
    "workers_ai_provider",
]
