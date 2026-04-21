from __future__ import annotations

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class MinerUConfig(BaseModel):
    """MinerU PDF parsing service configuration."""

    model_config = ConfigDict(populate_by_name=True)

    base_url: str = Field(
        default="https://mineru.net",
        validation_alias=AliasChoices("BASE_URL", "MINERU__BASE_URL", "RFLOW_MINERU_BASE_URL"),
    )
    api_token: str | None = Field(
        default=None,
        validation_alias=AliasChoices("API_TOKEN", "MINERU__API_TOKEN", "RFLOW_MINERU_API_TOKEN"),
    )
    model: str = Field(
        default="vlm",
        validation_alias=AliasChoices("MODEL", "MINERU__MODEL", "RFLOW_MINERU_MODEL"),
    )
    http_timeout_seconds: float = Field(
        default=300.0,
        validation_alias=AliasChoices(
            "HTTP_TIMEOUT_SECONDS",
            "MINERU__HTTP_TIMEOUT_SECONDS",
            "RFLOW_MINERU_HTTP_TIMEOUT_SECONDS",
        ),
    )
    poll_interval_seconds: float = Field(
        default=5.0,
        validation_alias=AliasChoices(
            "POLL_INTERVAL_SECONDS",
            "MINERU__POLL_INTERVAL_SECONDS",
            "RFLOW_MINERU_POLL_INTERVAL_SECONDS",
        ),
    )
    poll_timeout_seconds: float = Field(
        default=900.0,
        validation_alias=AliasChoices(
            "POLL_TIMEOUT_SECONDS",
            "MINERU__POLL_TIMEOUT_SECONDS",
            "RFLOW_MINERU_POLL_TIMEOUT_SECONDS",
        ),
    )
    pdf_parse_excerpt_chars: int = Field(
        default=1200,
        validation_alias=AliasChoices(
            "PDF_PARSE_EXCERPT_CHARS",
            "MINERU__PDF_PARSE_EXCERPT_CHARS",
            "RFLOW_PDF_PARSE_EXCERPT_CHARS",
        ),
    )
    pdf_parse_min_chars: int = Field(
        default=200,
        validation_alias=AliasChoices(
            "PDF_PARSE_MIN_CHARS",
            "MINERU__PDF_PARSE_MIN_CHARS",
            "RFLOW_PDF_PARSE_MIN_CHARS",
        ),
    )
    llm_pdf_context_chars: int = Field(
        default=14000,
        validation_alias=AliasChoices(
            "LLM_PDF_CONTEXT_CHARS",
            "MINERU__LLM_PDF_CONTEXT_CHARS",
            "RFLOW_LLM_PDF_CONTEXT_CHARS",
        ),
    )
    llm_pdf_section_chars: int = Field(
        default=2600,
        validation_alias=AliasChoices(
            "LLM_PDF_SECTION_CHARS",
            "MINERU__LLM_PDF_SECTION_CHARS",
            "RFLOW_LLM_PDF_SECTION_CHARS",
        ),
    )
