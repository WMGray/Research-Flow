from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class PaperResolveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_url: str | None = None
    doi: str | None = None
    title: str | None = None
    year: str = ""
    venue: str = ""

    @model_validator(mode="after")
    def validate_single_input(self) -> "PaperResolveRequest":
        provided = [bool(self.source_url), bool(self.doi), bool(self.title)]
        if sum(provided) != 1:
            raise ValueError("Exactly one of source_url, doi, or title must be provided.")
        return self


class PaperDownloadRequest(PaperResolveRequest):
    output_dir: str | None = None
    overwrite: bool | None = None

    @field_validator("output_dir")
    @classmethod
    def validate_output_dir(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip()
        if not normalized:
            return None

        path = Path(normalized)
        if path.is_absolute() or path.drive or ".." in path.parts:
            raise ValueError(
                "output_dir must be a relative subdirectory without parent traversal."
            )
        return normalized


class PaperResolveResponse(BaseModel):
    raw_input: str
    title: str
    authors: list[str] = Field(default_factory=list)
    year: str
    venue: str
    ccf_rank: str = ""
    sci_quartile: str = ""
    doi: str
    resolve_method: str
    source: str
    status: str
    pdf_url: str
    landing_url: str
    final_url: str
    http_status: str
    content_type: str
    detail: str
    error_code: str
    metadata_source: str
    metadata_confidence: str
    suggested_filename: str
    target_path: str
    probe_trace: list[str] = Field(default_factory=list)


class PaperDownloadResponse(BaseModel):
    resolution: PaperResolveResponse
    download_status: str
    file_path: str | None = None
    detail: str = ""
    error_code: str = ""
