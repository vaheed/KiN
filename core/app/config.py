from __future__ import annotations

from functools import lru_cache
from typing import Literal
from urllib.parse import quote

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore", case_sensitive=False)

    app_name: str = "KiN"
    version: str = "0.1.0"
    env: Literal["development", "test", "production"] = Field(default="production", alias="KiN_ENV")
    log_level: str = Field(default="INFO", alias="KiN_LOG_LEVEL")
    host: str = Field(default="0.0.0.0", alias="KiN_HOST")
    port: int = Field(default=8000, alias="KiN_PORT", ge=1, le=65535)

    db_name: str = Field(default="kin", alias="KiN_DB_NAME")
    db_user: str = Field(default="kin", alias="KiN_DB_USER")
    db_password: str = Field(default="change-this-kin-database-secret", alias="KiN_DB_PASSWORD")
    db_host: str = Field(default="postgres", alias="KiN_DB_HOST")
    db_port: int = Field(default=5432, alias="KiN_DB_PORT", ge=1, le=65535)
    db_pool_min: int = Field(default=1, alias="KiN_DB_POOL_MIN", ge=1)
    db_pool_max: int = Field(default=8, alias="KiN_DB_POOL_MAX", ge=1)

    redis_host: str = Field(default="redis", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT", ge=1, le=65535)
    redis_db: int = Field(default=0, alias="REDIS_DB", ge=0)
    working_memory_ttl_seconds: int = Field(default=86400, alias="KiN_WORKING_MEMORY_TTL_SECONDS", ge=60)
    session_max_context_items: int = Field(default=30, alias="KiN_SESSION_MAX_CONTEXT_ITEMS", ge=1, le=500)

    autonomy_profile: Literal["cautious", "balanced", "autonomous"] = Field(default="balanced", alias="KiN_AUTONOMY_PROFILE")

    bifrost_url: str = Field(default="http://bifrost:8080", alias="BIFROST_URL")
    bifrost_api_key: str = Field(default="", alias="BIFROST_API_KEY")
    decision_model: str = Field(default="anthropic/claude-sonnet-5.5", alias="KiN_DECISION_MODEL")
    decision_model_fast: str = Field(default="google/gemini-3.8-flash", alias="KiN_DECISION_MODEL_FAST")
    decision_model_deep: str = Field(default="anthropic/claude-opus-5.5", alias="KiN_DECISION_MODEL_DEEP")
    decision_gate_enabled: bool = Field(default=False, alias="KiN_DECISION_GATE_ENABLED")
    decision_gate_model: str = Field(default="typesafe/jev-1.13", alias="KiN_DECISION_GATE_MODEL")
    # Mem0 durable memory configuration. Mem0's LLM and embedder both use the
    # internal OpenAI-compatible Bifrost endpoint; OPENROUTER_API_KEY is never
    # injected into the KiN container, so Mem0 cannot bypass Bifrost.
    memory_llm_model: str = Field(default="google/gemini-3.8-flash", alias="KiN_MEMORY_LLM_MODEL")
    memory_user_id: str = Field(default="owner", alias="KiN_MEMORY_USER_ID")
    memory_agent_id: str = Field(default="kin", alias="KiN_MEMORY_AGENT_ID")
    memory_collection: str = Field(default="kin_memories", alias="KiN_MEMORY_COLLECTION")
    memory_history_db_path: str = Field(default="/app/data/mem0/history.db", alias="KiN_MEMORY_HISTORY_DB_PATH")
    embedding_model: str = Field(default="openai/text-embedding-3-small", alias="KiN_EMBEDDING_MODEL")
    embedding_dimensions: int = Field(default=1536, alias="KiN_EMBEDDING_DIMENSIONS", ge=1, le=4096)
    memory_search_limit: int = Field(default=8, alias="KiN_MEMORY_SEARCH_LIMIT", ge=1, le=50)
    memory_min_similarity: float = Field(default=0.15, alias="KiN_MEMORY_MIN_SIMILARITY", ge=0.0, le=1.0)

    trueforge_url: str = Field(default="http://trueforge:8790", alias="TRUEFORGE_URL")
    trueforge_token: str = Field(default="", alias="TRUEFORGE_TOKEN")
    trueforge_agent_name: str = Field(default="", alias="TRUEFORGE_AGENT_NAME")
    trueforge_model: str = Field(default="openai/gpt-4o-mini", alias="TRUEFORGE_MODEL")
    trueforge_enabled: bool = Field(default=True, alias="KiN_TRUEFORGE_ENABLED")
    disable_dependency_startup: bool = Field(default=False, alias="KiN_DISABLE_DEPENDENCY_STARTUP")

    @field_validator("db_pool_max")
    @classmethod
    def validate_pool(cls, value: int, info):
        pool_min = info.data.get("db_pool_min", 1)
        if value < pool_min:
            raise ValueError("KiN_DB_POOL_MAX must be >= KiN_DB_POOL_MIN")
        return value

    @property
    def database_url(self) -> str:
        user = quote(self.db_user, safe="")
        password = quote(self.db_password, safe="")
        database = quote(self.db_name, safe="")
        return f"postgresql://{user}:{password}@{self.db_host}:{self.db_port}/{database}"

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
