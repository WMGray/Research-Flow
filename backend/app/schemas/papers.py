from __future__ import annotations

from pydantic import BaseModel, Field


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


class PaperResponse(BaseModel):
    paper_id: str
    title: str
    slug: str
    stage: str
    status: str
    domain: str
    area: str
    topic: str
    year: int | None
    venue: str
    doi: str
    tags: list[str]
    path: str
    paper_path: str
    note_path: str
    refined_path: str
    images_path: str
    metadata_path: str
    metadata_json_path: str
    state_path: str
    parsed_text_path: str
    parsed_sections_path: str
    pdf_analysis_path: str
    parser_status: str
    note_status: str
    read_status: str
    refined_review_status: str
    classification_status: str
    rejected: bool
    error: str
    updated_at: str
