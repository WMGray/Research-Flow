from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


PaperStatus = Literal["imported", "parse_queued", "parsed", "failed", "deleted"]
DocumentRole = Literal["llm", "human", "parsed"]
JobStatus = Literal["queued", "running", "completed", "failed", "cancelled"]


class APIError(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class APIEnvelope(BaseModel):
    data: Any = None
    meta: dict[str, Any] = Field(default_factory=dict)
    error: APIError | None = None


class PaperCreateRequest(BaseModel):
    title: str = Field(min_length=1)
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    venue: str = ""
    venue_short: str = ""
    doi: str = ""
    url: str = ""
    pdf_url: str = ""
    category_id: int | None = None
    tags: list[str] = Field(default_factory=list)
    download_pdf: bool = False
    parse_after_import: bool = False


class PaperUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    authors: list[str] | None = None
    year: int | None = None
    venue: str | None = None
    venue_short: str | None = None
    doi: str | None = None
    url: str | None = None
    pdf_url: str | None = None
    category_id: int | None = None
    tags: list[str] | None = None
    status: PaperStatus | None = None

    @model_validator(mode="after")
    def validate_has_update(self) -> "PaperUpdateRequest":
        if not self.model_dump(exclude_unset=True):
            raise ValueError("At least one field must be provided.")
        return self


class PaperResponse(BaseModel):
    paper_id: int
    asset_id: int
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    venue: str = ""
    venue_short: str = ""
    doi: str = ""
    url: str = ""
    pdf_url: str = ""
    category_id: int | None = None
    tags: list[str] = Field(default_factory=list)
    status: PaperStatus
    assets: dict[str, int] = Field(default_factory=dict)
    created_at: str
    updated_at: str
    parse_job_id: str | None = None


class PaperListQuery(BaseModel):
    q: str = ""
    category_id: int | None = None
    status: PaperStatus | None = None
    year_from: int | None = None
    year_to: int | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort: str = "updated_at"
    order: Literal["asc", "desc"] = "desc"


class DocumentResponse(BaseModel):
    paper_id: int
    doc_role: DocumentRole
    content: str
    version: int
    updated_at: str


class DocumentUpdateRequest(BaseModel):
    content: str
    base_version: int | None = None


class ParsePaperRequest(BaseModel):
    parser: Literal["mineru"] = "mineru"
    force: bool = False
    llm_refine: bool = True
    split_sections: bool = True


class ParsedContentResponse(BaseModel):
    paper_id: int
    page_count: int
    char_count: int
    excerpt: str
    sections: list[dict[str, Any]] = Field(default_factory=list)
    artifacts: dict[str, int] = Field(default_factory=dict)


class JobResponse(BaseModel):
    job_id: str
    type: str
    status: JobStatus
    progress: float
    message: str
    resource_type: str
    resource_id: int
    created_at: str
    updated_at: str
    result: dict[str, Any] | None = None
    error: APIError | None = None
