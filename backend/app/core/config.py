"""Application settings, loaded from environment variables (never hardcoded)."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo-root .env, resolved from this file so it works regardless of the working directory.
# Real environment variables (e.g. injected by AWS later) take precedence over the file.
ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    # extra="ignore": .env also holds POSTGRES_* values for docker-compose that the app doesn't need.
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    # Required: the app refuses to start without it, rather than guessing a default.
    database_url: str
    cors_origins: str = "http://localhost:5173"

    # --- AI coach ---
    # Which LLMClient implementation to use. Only "ollama" exists so far.
    llm_provider: str = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:4b"
    # Per LLM call. Generous because local CPU inference is slow (~30s+ per call on a laptop).
    llm_timeout_seconds: float = 180.0
    llm_temperature: float = 0.3
    # Safety bound on the model <-> tool loop, so a confused model can't loop forever.
    chat_max_tool_rounds: int = 4
    # The app stores plain numbers with no currency, so the coach's currency symbol is configuration.
    currency_symbol: str = "$"

    # --- Tool backend for the AI coach ---
    # "direct": run tools in-process.  "mcp": run them through the SpendSmart MCP server.
    tool_provider: str = "direct"
    # Where the FastAPI app finds the MCP server (client side)...
    mcp_server_url: str = "http://127.0.0.1:8001/mcp"
    mcp_timeout_seconds: float = 30.0
    # ...and where the MCP server listens (server side). Localhost only: it has no authentication.
    mcp_host: str = "127.0.0.1"
    mcp_port: int = 8001

    @property
    def cors_origin_list(self) -> list[str]:
        # Env vars are plain strings, so a comma-separated value is split into a list here.
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    # Cached so the .env file is parsed once, not on every call.
    return Settings()
