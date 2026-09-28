"""Chooses the LLM client from configuration. The one place that knows which providers exist."""
from functools import lru_cache

from app.ai.llm_client import LLMClient
from app.ai.ollama_client import OllamaLLMClient
from app.core.config import get_settings


@lru_cache
def get_llm_client() -> LLMClient:
    # Cached so one HTTP connection pool is shared across requests.
    # Adding Bedrock later = one more `if` branch here plus a BedrockLLMClient class.
    settings = get_settings()
    if settings.llm_provider == "ollama":
        return OllamaLLMClient(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            timeout=settings.llm_timeout_seconds,
            temperature=settings.llm_temperature,
        )
    raise ValueError(f"Unsupported LLM_PROVIDER: {settings.llm_provider!r}")
