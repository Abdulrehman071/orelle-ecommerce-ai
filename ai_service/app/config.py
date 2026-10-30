"""Central configuration. Every secret/setting comes from environment variables (.env file)."""
from __future__ import annotations

import warnings
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL

# SQLite has no native Decimal type; our money columns are whole/2-decimal PKR amounts, so this is safe.
warnings.filterwarnings("ignore", message=".*does \\*not\\* support Decimal objects natively.*")

SERVICE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_STORE_DB = SERVICE_DIR.parent / "backend" / "db.sqlite3"  # the Django project's database


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=SERVICE_DIR / ".env", env_file_encoding="utf-8", extra="ignore")

    # --- business identity (future multi-store support: every assistant record carries business_id) ---
    store_name: str = "ORELLE"
    business_id: str = "orelle-main"
    business_timezone: str = "Asia/Karachi"
    currency: str = "PKR"

    # --- databases ---
    store_db_url: str = ""   # empty -> the Django project's db.sqlite3 (opened READ-ONLY)
    agent_db_url: str = ""   # empty -> ai_service/assistant.sqlite3 (assistant's own tables)

    # --- LLM ---
    # llm_provider: anthropic | groq | gemini | openrouter | ollama   (empty = anthropic if its key is set)
    llm_provider: str = ""
    llm_api_key: str = ""    # key for groq / gemini / openrouter (ollama needs none)
    llm_model: str = ""      # empty -> a sensible default for the chosen provider
    llm_base_url: str = ""   # empty -> the provider's standard URL
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5-5"
    llm_timeout_seconds: float = 30.0
    llm_max_retries: int = 2
    llm_max_tokens: int = 1200

    # --- limits ---
    max_agent_rounds: int = 6        # max LLM<->tool round trips inside ONE agent
    max_plan_steps: int = 3          # max agents the Manager may run for ONE request
    low_stock_threshold: int = 5     # default threshold for low-stock reports
    rate_limit_per_minute: int = 20  # per user (or per IP when anonymous)
    max_message_chars: int = 2000

    # --- web ---
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def store_url(self) -> str | URL:
        return self.store_db_url or URL.create("sqlite", database=str(DEFAULT_STORE_DB))

    @property
    def agent_url(self) -> str | URL:
        return self.agent_db_url or URL.create("sqlite", database=str(SERVICE_DIR / "assistant.sqlite3"))

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
