from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Research-Flow"
    api_prefix: str = "/api"
    data_root: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[2] / "data")
    frontend_origin: str = "http://127.0.0.1:5173"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

