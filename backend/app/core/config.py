from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, BaseModel, Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)

from app.core.mcp_config import ZoteroConfig


def backend_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_settings_file() -> Path:
    return backend_root() / "config" / "settings.toml"


def configured_settings_file() -> Path:
    config_file = os.getenv("RESEARCH_FLOW_CONFIG_FILE")
    if config_file:
        return Path(config_file).expanduser().resolve()
    return default_settings_file()


def env_file_path() -> Path:
    return backend_root() / ".env"


def _load_env_file() -> None:
    """将 backend/.env 预加载到进程环境，但不覆盖已有系统环境变量。"""
    path = env_file_path()
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue

        if value and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]

        os.environ.setdefault(key, value)


class AppConfig(BaseModel):
    """General application settings shared by the backend service."""

    host: str = Field(
        default="127.0.0.1",
        validation_alias=AliasChoices("APP__HOST", "APP_HOST"),
    )
    port: int = Field(
        default=8000,
        validation_alias=AliasChoices("APP__PORT", "APP_PORT"),
    )
    env: str = Field(
        default="development",
        validation_alias=AliasChoices("APP__ENV", "APP_ENV"),
    )
    debug: bool = Field(
        default=True,
        validation_alias=AliasChoices("APP__DEBUG", "APP_DEBUG"),
    )


class Settings(BaseSettings):
    """Top-level settings object loaded from env, .env and TOML."""

    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        extra="ignore",
    )

    app: AppConfig = AppConfig()
    zotero: ZoteroConfig = ZoteroConfig()

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        toml_settings = TomlConfigSettingsSource(
            settings_cls,
            toml_file=configured_settings_file(),
        )
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            toml_settings,
            file_secret_settings,
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    _load_env_file()
    return Settings()


def reset_settings() -> None:
    get_settings.cache_clear()
