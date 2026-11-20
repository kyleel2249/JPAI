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

    model_config = SettingsConfigDict(env_prefix="JPAI_", env_file=".env", extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
