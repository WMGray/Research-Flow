from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class PaperRepositoryError(RuntimeError):
    code = "PAPER_REPOSITORY_ERROR"


class PaperNotFoundError(PaperRepositoryError):
    code = "PAPER_NOT_FOUND"


class DuplicatePaperError(PaperRepositoryError):
    code = "PAPER_DUPLICATE"


class DocumentNotFoundError(PaperRepositoryError):
    code = "DOCUMENT_NOT_FOUND"


class DocumentVersionConflictError(PaperRepositoryError):
    code = "DOCUMENT_VERSION_CONFLICT"


class JobNotFoundError(PaperRepositoryError):
    code = "JOB_NOT_FOUND"


class JobCancelNotAllowedError(PaperRepositoryError):
    code = "JOB_CANCEL_NOT_ALLOWED"


@dataclass(frozen=True, slots=True)
class PaperRecord:
    paper_id: int
    asset_id: int
    title: str
    authors: list[str]
    year: int | None
    venue: str
    venue_short: str
    doi: str
    source_url: str
    pdf_url: str
    category_id: int | None
    tags: list[str]
    paper_stage: str
    download_status: str
    parse_status: str
    refine_status: str
    review_status: str
    note_status: str
    assets: dict[str, int]
    created_at: str
    updated_at: str
    download_job_id: str | None = None
    parse_job_id: str | None = None
    paper_slug: str = ""
    abstract: str = ""
    source_kind: str = "manual"
    ccf_rank: str = ""
    sci_quartile: str = ""
    latest_job_id: str | None = None
    latest_job_type: str = ""
    latest_job_status: str = ""
    latest_job_message: str = ""
    source_pdf_size: int = 0
    source_pdf_is_real: bool = False


@dataclass(frozen=True, slots=True)
class DocumentRecord:
    paper_id: int
    doc_id: int
    doc_role: str
    path: Path
    content: str
    version: int
    updated_at: str


@dataclass(frozen=True, slots=True)
class JobRecord:
    job_id: str
    type: str
    status: str
    progress: float
    message: str
    resource_type: str
    resource_id: int
    created_at: str
    updated_at: str
    result: dict[str, Any] | None
    error: dict[str, Any] | None


@dataclass(frozen=True, slots=True)
class JobListInput:
    page: int = 1
    page_size: int = 20
    resource_type: str | None = None
    resource_id: int | None = None
    status: str | None = None


@dataclass(frozen=True, slots=True)
class PaperArtifactRecord:
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
    metadata: dict[str, Any]
    created_at: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class PaperPipelineRunRecord:
    run_id: str
    paper_id: int
    job_id: str | None
    stage: str
    status: str
    input_artifacts: list[str]
    output_artifacts: list[str]
    metrics: dict[str, Any]
    error: dict[str, Any] | None
    created_at: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class PaperCreateInput:
    title: str
    abstract: str = ""
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    venue: str = ""
    venue_short: str = ""
    ccf_rank: str = ""
    sci_quartile: str = ""
    doi: str = ""
    source_url: str = ""
    pdf_url: str = ""
    source_kind: str = "manual"
    category_id: int | None = None
    tags: list[str] = field(default_factory=list)
    download_pdf: bool = False
    parse_after_import: bool = False


@dataclass(frozen=True, slots=True)
class PaperPipelineInput:
    download_pdf: bool = True
    parse: bool = True
    refine_parse: bool = True
    split_sections: bool = True
    generate_note: bool = True
    parser: str = "mineru"
    force_parse: bool = False
    refine_instruction: str = ""
    require_review_confirmation: bool = False


@dataclass(frozen=True, slots=True)
class PaperPipelineRecord:
    paper_id: int
    status: str
    message: str
    stopped_at: str | None
    jobs: list[JobRecord]
    paper: PaperRecord


@dataclass(frozen=True, slots=True)
class PaperUpdateInput:
    values: dict[str, Any]


@dataclass(frozen=True, slots=True)
class PaperListInput:
    q: str = ""
    category_id: int | None = None
    paper_stage: str | None = None
    year_from: int | None = None
    year_to: int | None = None
    page: int = 1
    page_size: int = 20
    sort: str = "updated_at"
    order: str = "desc"


@dataclass(frozen=True, slots=True)
class DocumentUpdateInput:
    content: str
    base_version: int | None = None


@dataclass(frozen=True, slots=True)
class ParsePaperInput:
    parser: str = "mineru"
    force: bool = False


@dataclass(frozen=True, slots=True)
class RefineParseInput:
    skill_key: str = "paper_refine_parse"
    instruction: str = ""


@dataclass(frozen=True, slots=True)
class ParsedContentRecord:
    paper_id: int
    page_count: int
    char_count: int
    excerpt: str
    sections: list[dict[str, Any]]
    artifacts: dict[str, int]


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def paper_record_from_row(row: Any, assets: dict[str, int]) -> PaperRecord:
    asset_id = int(row["asset_id"])
    return PaperRecord(
        paper_id=asset_id,
        asset_id=asset_id,
        title=str(row["title"]),
        paper_slug=str(row["paper_slug"] or f"paper-{asset_id}"),
        authors=json.loads(row["authors"] or "[]"),
        abstract=str(row["abstract"] or ""),
        year=row["pub_year"],
        venue=str(row["venue"]),
        venue_short=str(row["venue_short"]),
        ccf_rank=str(row["ccf_rank"] or ""),
        sci_quartile=str(row["sci_quartile"] or ""),
        doi=str(row["doi"]),
        source_url=str(row["source_url"]),
        pdf_url=str(row["pdf_url"]),
        source_kind=str(row["source_kind"] or "manual"),
        category_id=row["category_id"],
        tags=json.loads(row["tags"] or "[]"),
        paper_stage=str(row["paper_stage"]),
        download_status=str(row["download_status"]),
        parse_status=str(row["parse_status"]),
        refine_status=str(row["refine_status"]),
        review_status=str(row["review_status"]),
        note_status=str(row["note_status"]),
        assets=assets,
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


def map_paper_update_values(values: dict[str, Any]) -> dict[str, Any]:
    key_map = {"year": "pub_year"}
    mapped: dict[str, Any] = {}
    for key, value in values.items():
        column = key_map.get(key, key)
        if column in {"authors", "tags"}:
            value = json.dumps(value, ensure_ascii=False)
        mapped[column] = value
    return mapped


def paper_sort_column(sort: str) -> str:
    return {
        "paper_id": "bp.asset_id",
        "title": "bp.title",
        "year": "bp.pub_year",
        "paper_stage": "bp.paper_stage",
        "created_at": "ar.created_at",
        "updated_at": "ar.updated_at",
    }.get(sort, "ar.updated_at")
