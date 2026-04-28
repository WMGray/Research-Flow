from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


PaperStage = Literal[
    "metadata_ready",
    "downloaded",
    "parsed",
    "refined",
    "review_confirmed",
    "sectioned",
    "noted",
    "knowledge_extracted",
    "dataset_extracted",
    "completed",
    "error",
]
PipelineStatus = Literal["pending", "queued", "running", "succeeded", "failed"]
ReviewStatus = Literal["pending", "waiting_review", "confirmed"]
NoteStatus = Literal["empty", "clean_generated", "user_modified", "merged", "conflict_pending"]
DocumentRole = Literal["note", "refined"]
JobStatus = Literal[
    "queued",
    "running",
    "waiting_review",
    "waiting_confirm",
    "succeeded",
    "failed",
    "cancelled",
]


class APIError(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class APIEnvelope(BaseModel):
    data: Any = None
    meta: dict[str, Any] = Field(default_factory=dict)
    error: APIError | None = None


class PaperCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    venue: str = ""
    venue_short: str = ""
    doi: str = ""
    source_url: str = ""
    pdf_url: str = ""
    category_id: int | None = None
    tags: list[str] = Field(default_factory=list)
    download_pdf: bool = False
    parse_after_import: bool = False


class PaperUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1)
    authors: list[str] | None = None
    year: int | None = None
    venue: str | None = None
    venue_short: str | None = None
    doi: str | None = None
    source_url: str | None = None
    pdf_url: str | None = None
    category_id: int | None = None
    tags: list[str] | None = None

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
    source_url: str = ""
    pdf_url: str = ""
    category_id: int | None = None
    tags: list[str] = Field(default_factory=list)
    paper_stage: PaperStage
    download_status: PipelineStatus
    parse_status: PipelineStatus
    refine_status: PipelineStatus
    review_status: ReviewStatus
    note_status: NoteStatus
    assets: dict[str, int] = Field(default_factory=dict)
    created_at: str
    updated_at: str
    download_job_id: str | None = None
    parse_job_id: str | None = None


class PaperListQuery(BaseModel):
    q: str = ""
    category_id: int | None = None
    paper_stage: PaperStage | None = None
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
    model_config = ConfigDict(extra="forbid")

    content: str
    base_version: int | None = None


class ParsePaperRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parser: Literal["mineru"] = "mineru"
    force: bool = False


class RefineParseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skill_key: str = Field(default="paper_refine_parse", min_length=1)
    instruction: str = ""


class PaperPipelineRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    download_pdf: bool = True
    parse: bool = True
    refine_parse: bool = True
    split_sections: bool = True
    generate_note: bool = True
    parser: Literal["mineru"] = "mineru"
    force_parse: bool = False
    refine_instruction: str = ""
    require_review_confirmation: bool = False


class ParsedContentResponse(BaseModel):
    paper_id: int
    page_count: int
    char_count: int
    excerpt: str
    sections: list[dict[str, Any]] = Field(default_factory=list)
    artifacts: dict[str, int] = Field(default_factory=dict)


class SectionDocumentResponse(BaseModel):
    section_key: Literal[
        "introduction",
        "related_work",
        "method",
        "experiment",
        "conclusion",
        "appendix",
    ]
    title: str
    content: str
    char_count: int


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


class PaperArtifactResponse(BaseModel):
    artifact_id: int
    paper_id: int
    asset_id: int
    artifact_key: str
    artifact_type: str
    stage: str
    storage_path: str
    content_hash: str
    file_size: int
    version: int
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    updated_at: str


class PaperPipelineRunResponse(BaseModel):
    run_id: str
    paper_id: int
    job_id: str | None = None
    stage: str
    status: str
    input_artifacts: list[str] = Field(default_factory=list)
    output_artifacts: list[str] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    error: APIError | None = None
    created_at: str
    updated_at: str


class PaperPipelineResponse(BaseModel):
    paper_id: int
    status: Literal["succeeded", "failed", "waiting_review"]
    message: str
    stopped_at: str | None = None
    jobs: list[JobResponse] = Field(default_factory=list)
    paper: PaperResponse
