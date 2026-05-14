from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


def default_tags() -> list[str]:
    return ["paper"]


@dataclass(frozen=True, slots=True)
class IngestPaperInput:
    source: Path
    domain: str | None = None
    area: str | None = None
    topic: str | None = None
    target_path: str | None = None
    move: bool = False


@dataclass(frozen=True, slots=True)
class GenerateNoteInput:
    title: str = ""
    year: int | str | None = None
    venue: str = ""
    doi: str = ""
    domain: str = ""
    area: str = ""
    topic: str = ""
    status: str = "draft"
    tags: list[str] = field(default_factory=default_tags)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "year": self.year,
            "venue": self.venue,
            "doi": self.doi,
            "domain": self.domain,
            "area": self.area,
            "topic": self.topic,
            "status": self.status,
            "tags": self.tags or default_tags(),
        }


@dataclass(frozen=True, slots=True)
class ParsePdfInput:
    paper_id: str
    force: bool = False
    parser: str = "auto"


@dataclass(slots=True)
class BatchRecord:
    batch_id: str
    title: str
    candidate_total: int
    keep_total: int
    reject_total: int
    review_status: str
    path: str
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class CandidateRecord:
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
    recommendation_reason: str
    landing_status: str
    result_path: str
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ParserRunRecord:
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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class PaperRecord:
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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
