from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field, field_validator, model_validator


class PaperResolveRequest(BaseModel):
    # 三种输入只允许三选一，和 gPaper 原生入口保持一致。
    url: str | None = None
    doi: str | None = None
    name: str | None = None
    title: str = ""
    year: str = ""
    venue: str = ""

    @model_validator(mode="after")
    def validate_single_input(self) -> "PaperResolveRequest":
        # 这里不额外引入复杂请求结构，直接约束 gPaper 支持的三类主输入。
        provided = [bool(self.url), bool(self.doi), bool(self.name)]
        if sum(provided) != 1:
            raise ValueError("Exactly one of url, doi, or name must be provided.")
        return self


class PaperDownloadRequest(PaperResolveRequest):
    # download 相比 resolve 只多两个运行时选项。
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
    year: str
    venue: str
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
