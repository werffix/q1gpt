from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment or .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: str = Field(alias="BOT_TOKEN")
    llm_api_key: str = Field(alias="LLM_API_KEY")
    llm_base_url: str = Field(default="https://vibecode.moe/v1/codex", alias="LLM_BASE_URL")
    database_url: str = Field(default="sqlite+aiosqlite:///./bot.db", alias="DATABASE_URL")
    admin_ids: str = Field(default="", alias="ADMIN_IDS")
    max_context_messages: int = Field(default=20, alias="MAX_CONTEXT_MESSAGES")
    llm_timeout: float = Field(default=120.0, alias="LLM_TIMEOUT")

    @property
    def admin_id_set(self) -> set[int]:
        return {int(value.strip()) for value in self.admin_ids.split(",") if value.strip().isdigit()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
