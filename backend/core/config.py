"""后端共享配置加载入口。

本模块只依赖 core 内部配置模型，可被 FastAPI app、Celery worker 和脚本共同使用。
配置优先级为：初始化参数 > 环境变量/.env > config/settings.toml > file secret。
"""

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

from core.llm_config import LLMConfig
from core.mcp_config import ZoteroConfig
from core.mineru_config import MinerUConfig
from core.paper_download_config import PaperDownloadConfig
from core.pdf_parser_config import MarkdownRefineConfig, PDFParserConfig


def backend_root() -> Path:
    """返回 backend 目录根路径。"""

    return Path(__file__).resolve().parents[1]


def default_settings_file() -> Path:
    """返回版本化默认配置文件路径。"""

    return backend_root() / "config" / "settings.toml"


def configured_settings_file() -> Path:
    """解析当前应使用的 TOML 配置文件。"""

    config_file = os.getenv("RESEARCH_FLOW_CONFIG_FILE")
    if config_file:
        return Path(config_file).expanduser().resolve()
    return default_settings_file()


def env_file_path() -> Path | None:
    """解析 .env 文件路径；允许通过环境变量显式关闭。"""

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
    """FastAPI 主服务通用配置。"""

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
    """后端顶层配置对象，从 env、.env 和 TOML 聚合加载。"""

    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        extra="ignore",
    )

    app: AppConfig = AppConfig()
    llm: LLMConfig = LLMConfig()
    mineru: MinerUConfig = MinerUConfig()
    paper_download: PaperDownloadConfig = PaperDownloadConfig()
    pdf_parser: PDFParserConfig = PDFParserConfig()
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
        """定义配置源优先级，并把版本化 TOML 纳入加载链路。"""

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
    """返回缓存后的全局配置对象。"""

    _load_env_file()
    settings = Settings()
    return _apply_flat_env_overrides(settings)


def reset_settings() -> None:
    """清空配置缓存，主要供测试在修改环境变量后重载配置。"""

    get_settings.cache_clear()


def _env_subset(names: tuple[str, ...]) -> dict[str, str]:
    """从当前进程环境中提取指定变量子集。"""

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
    pdf_parser_markdown_refine_overrides = _env_subset(
        (
            "PDF_PARSER_MARKDOWN_REFINE_ENABLED",
            "PDF_PARSER_MARKDOWN_REFINE_FEATURE",
            "PDF_PARSER_MARKDOWN_REFINE_RUNTIME_INSTRUCTION_KEY",
            "PDF_PARSER_MARKDOWN_REFINE_INSTRUCTION_OVERRIDE",
            "PDF_PARSER_MARKDOWN_REFINE_MAX_INPUT_CHARS",
            "PDF_PARSER_MARKDOWN_REFINE_OUTPUT_FILENAME",
            "PDF_PARSER_MARKDOWN_REFINE_FAIL_OPEN",
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

    pdf_parser = settings.pdf_parser
    if pdf_parser_markdown_refine_overrides:
        markdown_refine_update = MarkdownRefineConfig.model_validate(
            pdf_parser_markdown_refine_overrides
        )
        pdf_parser = pdf_parser.model_copy(
            update={
                "markdown_refine": pdf_parser.markdown_refine.model_copy(
                    update=markdown_refine_update.model_dump(exclude_unset=True)
                )
            }
        )

    return settings.model_copy(
        update={
            "app": app,
            "zotero": zotero,
            "paper_download": paper_download,
            "mineru": mineru,
            "pdf_parser": pdf_parser,
        }
    )
