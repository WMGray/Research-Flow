from __future__ import annotations

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class PaperDownloadConfig(BaseModel):
    """Runtime configuration for paper parsing and PDF downloading."""

    model_config = ConfigDict(populate_by_name=True)

    output_dir: str = Field(
        default="data/papers",
        validation_alias=AliasChoices(
            "OUTPUT_DIR",
            "PAPER_DOWNLOAD__OUTPUT_DIR",
            "PAPER_DOWNLOAD_OUTPUT_DIR",
            "EXTRACT_REFS_OUTPUT_DIR",
        ),
    )
    email: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "EMAIL",
            "PAPER_DOWNLOAD__EMAIL",
            "PAPER_DOWNLOAD_EMAIL",
            "EXTRACT_REFS_EMAIL",
        ),
    )
    s2_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "S2_API_KEY",
            "PAPER_DOWNLOAD__S2_API_KEY",
            "PAPER_DOWNLOAD_S2_API_KEY",
            "EXTRACT_REFS_S2_API_KEY",
        ),
    )
    openalex_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "OPENALEX_API_KEY",
            "PAPER_DOWNLOAD__OPENALEX_API_KEY",
            "PAPER_DOWNLOAD_OPENALEX_API_KEY",
            "EXTRACT_REFS_OPENALEX_API_KEY",
        ),
    )
    timeout: int = Field(
        default=30,
        validation_alias=AliasChoices(
            "TIMEOUT",
            "PAPER_DOWNLOAD__TIMEOUT",
            "PAPER_DOWNLOAD_TIMEOUT",
            "EXTRACT_REFS_TIMEOUT",
        ),
    )
    retries: int = Field(
        default=2,
        validation_alias=AliasChoices(
            "RETRIES",
            "PAPER_DOWNLOAD__RETRIES",
            "PAPER_DOWNLOAD_RETRIES",
            "EXTRACT_REFS_RETRIES",
        ),
    )
    retry_wait: int = Field(
        default=2,
        validation_alias=AliasChoices(
            "RETRY_WAIT",
            "PAPER_DOWNLOAD__RETRY_WAIT",
            "PAPER_DOWNLOAD_RETRY_WAIT",
            "EXTRACT_REFS_RETRY_WAIT",
        ),
    )
    rate_limit_wait: int = Field(
        default=20,
        validation_alias=AliasChoices(
            "RATE_LIMIT_WAIT",
            "PAPER_DOWNLOAD__RATE_LIMIT_WAIT",
            "PAPER_DOWNLOAD_RATE_LIMIT_WAIT",
            "EXTRACT_REFS_RATE_LIMIT_WAIT",
        ),
    )
    min_pdf_size: int = Field(
        default=4096,
        validation_alias=AliasChoices(
            "MIN_PDF_SIZE",
            "PAPER_DOWNLOAD__MIN_PDF_SIZE",
            "PAPER_DOWNLOAD_MIN_PDF_SIZE",
            "EXTRACT_REFS_MIN_PDF_SIZE",
        ),
    )
    overwrite: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "OVERWRITE",
            "PAPER_DOWNLOAD__OVERWRITE",
            "PAPER_DOWNLOAD_OVERWRITE",
            "EXTRACT_REFS_OVERWRITE",
        ),
    )
