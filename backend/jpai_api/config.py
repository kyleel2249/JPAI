"""Typed runtime configuration with safe local defaults."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "JPAI"
    environment: str = "development"
    api_prefix: str = "/api/v1"
    host: str = "127.0.0.1"
    port: int = 8000
    log_level: str = "INFO"
    ollama_base_url: str = "http://127.0.0.1:11434"
    model_timeout_seconds: float = 90.0
    gateway_requests_per_minute: int = 60
    gateway_max_request_bytes: int = 22_020_096
    gateway_api_key: str | None = None
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    model_fabric_timeout_seconds: float = 180.0
    model_fabric_max_concurrency: int = 16

    model_config = SettingsConfigDict(env_prefix="JPAI_", env_file=".env", extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
