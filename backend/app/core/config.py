from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, BaseModel, ConfigDict, Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)

from app.core.llm_config import LLMConfig
from app.core.mcp_config import ZoteroConfig
from app.core.mineru_config import MinerUConfig
from app.core.paper_download_config import PaperDownloadConfig


def backend_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_settings_file() -> Path:
    return backend_root() / "config" / "settings.toml"


def configured_settings_file() -> Path:
    config_file = os.getenv("RESEARCH_FLOW_CONFIG_FILE")
    if config_file:
        return Path(config_file).expanduser().resolve()
    return default_settings_file()


def env_file_path() -> Path | None:
    env_file = os.getenv("RESEARCH_FLOW_ENV_FILE")
    if env_file:
        if env_file.strip().lower() in {"none", "off", "false"}:
            return None
        return Path(env_file).expanduser().resolve()
    return backend_root() / ".env"


def _load_env_file() -> None:
    """将 backend/.env 预加载到进程环境，但不覆盖已有系统环境变量。"""
    path = env_file_path()
    if path is None or not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
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

    model_config = ConfigDict(populate_by_name=True)

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
    llm: LLMConfig = LLMConfig()
    mineru: MinerUConfig = MinerUConfig()
    paper_download: PaperDownloadConfig = PaperDownloadConfig()
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
    settings = Settings()
    return _apply_flat_env_overrides(settings)


def reset_settings() -> None:
    get_settings.cache_clear()


def _env_subset(names: tuple[str, ...]) -> dict[str, str]:
    return {name: os.environ[name] for name in names if name in os.environ}


def _apply_flat_env_overrides(settings: Settings) -> Settings:
    """兼容历史扁平环境变量，并将其映射到嵌套配置模型。

    `pydantic-settings` 对嵌套模型默认更偏向 `APP__HOST` 这类命名。
    项目早期已经约定了 `APP_HOST`、`ZOTERO_MCP_TIMEOUT_SECONDS` 等扁平命名，
    因此这里做一次显式映射，避免 TOML 与 .env 并存时出现“看似设置了但没生效”的问题。
    """

    app_overrides = _env_subset(
        (
            "APP_HOST",
            "APP_PORT",
            "APP_ENV",
            "APP_DEBUG",
        )
    )
    zotero_overrides = _env_subset(
        (
            "ZOTERO_MCP_ENABLED",
            "ZOTERO_MCP_COMMAND",
            "ZOTERO_MCP_ARGS",
            "ZOTERO_MCP_TRANSPORT",
            "ZOTERO_LOCAL",
            "ZOTERO_API_KEY",
            "ZOTERO_LIBRARY_ID",
            "ZOTERO_LIBRARY_TYPE",
            "PYTHONIOENCODING",
            "PYTHONUTF8",
            "UNPAYWALL_EMAIL",
            "UNSAFE_OPERATIONS",
            "ZOTERO_MCP_TIMEOUT_SECONDS",
        )
    )
    paper_download_overrides = _env_subset(
        (
            "PAPER_DOWNLOAD_OUTPUT_DIR",
            "PAPER_DOWNLOAD_EMAIL",
            "PAPER_DOWNLOAD_S2_API_KEY",
            "PAPER_DOWNLOAD_OPENALEX_API_KEY",
            "PAPER_DOWNLOAD_TIMEOUT",
            "PAPER_DOWNLOAD_RETRIES",
            "PAPER_DOWNLOAD_RETRY_WAIT",
            "PAPER_DOWNLOAD_RATE_LIMIT_WAIT",
            "PAPER_DOWNLOAD_MIN_PDF_SIZE",
            "PAPER_DOWNLOAD_OVERWRITE",
            "EXTRACT_REFS_OUTPUT_DIR",
            "EXTRACT_REFS_EMAIL",
            "EXTRACT_REFS_S2_API_KEY",
            "EXTRACT_REFS_OPENALEX_API_KEY",
            "EXTRACT_REFS_TIMEOUT",
            "EXTRACT_REFS_RETRIES",
            "EXTRACT_REFS_RETRY_WAIT",
            "EXTRACT_REFS_RATE_LIMIT_WAIT",
            "EXTRACT_REFS_MIN_PDF_SIZE",
            "EXTRACT_REFS_OVERWRITE",
        )
    )
    mineru_overrides = _env_subset(
        (
            "RFLOW_MINERU_BASE_URL",
            "RFLOW_MINERU_API_TOKEN",
            "RFLOW_MINERU_MODEL",
            "RFLOW_MINERU_HTTP_TIMEOUT_SECONDS",
            "RFLOW_MINERU_POLL_INTERVAL_SECONDS",
            "RFLOW_MINERU_POLL_TIMEOUT_SECONDS",
            "RFLOW_PDF_PARSE_EXCERPT_CHARS",
            "RFLOW_PDF_PARSE_MIN_CHARS",
            "RFLOW_LLM_PDF_CONTEXT_CHARS",
            "RFLOW_LLM_PDF_SECTION_CHARS",
            "MINERU__BASE_URL",
            "MINERU__API_TOKEN",
            "MINERU__MODEL",
            "MINERU__HTTP_TIMEOUT_SECONDS",
            "MINERU__POLL_INTERVAL_SECONDS",
            "MINERU__POLL_TIMEOUT_SECONDS",
            "MINERU__PDF_PARSE_EXCERPT_CHARS",
            "MINERU__PDF_PARSE_MIN_CHARS",
            "MINERU__LLM_PDF_CONTEXT_CHARS",
            "MINERU__LLM_PDF_SECTION_CHARS",
        )
    )

    app = settings.app
    if app_overrides:
        app_update = AppConfig.model_validate(app_overrides)
        app = app.model_copy(update=app_update.model_dump(exclude_unset=True))

    zotero = settings.zotero
    if zotero_overrides:
        zotero_update = ZoteroConfig.model_validate(zotero_overrides)
        zotero = zotero.model_copy(update=zotero_update.model_dump(exclude_unset=True))

    paper_download = settings.paper_download
    if paper_download_overrides:
        paper_download_update = PaperDownloadConfig.model_validate(paper_download_overrides)
        paper_download = paper_download.model_copy(
            update=paper_download_update.model_dump(exclude_unset=True)
        )

    mineru = settings.mineru
    if mineru_overrides:
        mineru_update = MinerUConfig.model_validate(mineru_overrides)
        mineru = mineru.model_copy(update=mineru_update.model_dump(exclude_unset=True))

    return settings.model_copy(
        update={"app": app, "zotero": zotero, "paper_download": paper_download, "mineru": mineru}
    )
