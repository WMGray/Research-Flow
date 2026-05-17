from __future__ import annotations

from pydantic import BaseModel, Field


class ImportPaperRequest(BaseModel):
    title: str
    source: str | None = None
    domain: str = ""
    area: str = ""
    topic: str = ""
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    venue: str = ""
    doi: str = ""
    arxiv_id: str = ""
    url: str = ""
    abstract: str = ""
    summary: str = ""
    tags: list[str] = Field(default_factory=lambda: ["paper"])
    refresh_metadata: bool = False


class IngestRequest(BaseModel):
    source: str
    domain: str | None = None
    area: str | None = None
    topic: str | None = None
    target_path: str | None = None
    move: bool = False


class GenerateNoteRequest(BaseModel):
    title: str | None = None
    year: int | None = None
    venue: str | None = None
    doi: str | None = None
    domain: str | None = None
    area: str | None = None
    topic: str | None = None
    tags: list[str] = Field(default_factory=lambda: ["paper"])


class GeneratePaperNoteRequest(BaseModel):
    overwrite: bool = False


class ParsePdfRequest(BaseModel):
    force: bool = False
    parser: str = "auto"


class ReviewDecisionRequest(BaseModel):
    decision: str
    comment: str = ""


class UpdateClassificationRequest(BaseModel):
    domain: str = ""
    area: str = ""
    topic: str = ""
    title: str | None = None
    venue: str | None = None
    year: int | None = None
    tags: list[str] | None = None
    status: str | None = None
    paper_path: str | None = None
    note_path: str | None = None
    refined_path: str | None = None


class UpdateMetadataRequest(BaseModel):
    title: str | None = None
    authors: list[str] | None = None
    year: int | None = None
    venue: str | None = None
    doi: str | None = None
    arxiv_id: str | None = None
    url: str | None = None
    abstract: str | None = None
    summary: str | None = None
    domain: str | None = None
    area: str | None = None
    topic: str | None = None
    tags: list[str] | None = None


class RefreshMetadataRequest(BaseModel):
    title: str | None = None
    doi: str | None = None
    arxiv_id: str | None = None
    url: str | None = None
    force: bool = False


class UpdateStarRequest(BaseModel):
    starred: bool


class BindAssetsRequest(BaseModel):
    source: str
    move: bool = False


class ResearchLogRequest(BaseModel):
    title: str = "阅读记录"
    bullets: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    tasks: list[dict[str, str | bool]] = Field(default_factory=list)


class SearchAgentSettingsRequest(BaseModel):
    command_template: str | None = None
    prompt_template: str | None = None
    max_results: int | None = None
    default_source: str | None = None


class CreateSearchBatchRequest(BaseModel):
    keywords: str
    venue: str = ""
    year_start: int | None = None
    year_end: int | None = None
    source: str = ""
    max_results: int | None = None


class BatchCandidateDecisionRequest(BaseModel):
    decision: str
    candidate_ids: list[str] = Field(default_factory=list)


class CreateLibraryFolderRequest(BaseModel):
    path: str


class CandidateDecisionRequest(BaseModel):
    decision: str


class BatchResponse(BaseModel):
    batch_id: str
    title: str
    candidate_total: int
    keep_total: int
    reject_total: int
    review_status: str
    path: str
    updated_at: str


class CandidateResponse(BaseModel):
    candidate_id: str
    batch_id: str
    title: str
    authors: list[str]
    year: int | None
    venue: str
    decision: str
    source_type: str
    collection_role: str
    paper_type: str
    quality: int
    relevance: int
    landing_status: str
    recommendation_reason: str
    abstract: str
    url: str
    doi: str
    arxiv_id: str
    pdf_url: str
    result_path: str
    updated_at: str


class ParserRunResponse(BaseModel):
    run_id: str
    paper_id: str
    status: str
    parser: str
    source_pdf: str
    refined_path: str
    image_dir: str
    text_path: str
    sections_path: str
    error: str
    started_at: str
    finished_at: str


class PaperEventResponse(BaseModel):
    timestamp: str
    event: str
    actor: str
    result: str
    message: str
    technical_detail: str
    next_action: str


class PaperResponse(BaseModel):
    paper_id: str
    title: str
    slug: str
    stage: str
    status: str
    workflow_status: str
    asset_status: str
    review_status: str
    domain: str
    area: str
    topic: str
    year: int | None
    venue: str
    doi: str
    authors: list[str]
    abstract: str
    summary: str
    url: str
    arxiv_id: str
    starred: bool
    tags: list[str]
    path: str
    paper_path: str
    note_path: str
    refined_path: str
    images_path: str
    metadata_path: str
    metadata_json_path: str
    state_path: str
    events_path: str
    parsed_text_path: str
    parsed_sections_path: str
    pdf_analysis_path: str
    parser_status: str
    note_status: str
    note_review_status: str
    parser_artifacts: dict[str, str]
    capabilities: dict[str, bool]
    read_status: str
    refined_review_status: str
    classification_status: str
    rejected: bool
    error: str
    updated_at: str
