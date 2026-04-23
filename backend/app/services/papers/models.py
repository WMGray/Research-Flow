from __future__ import annotations

import json
from dataclasses import dataclass
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
    url: str
    pdf_url: str
    category_id: int | None
    tags: list[str]
    status: str
    assets: dict[str, int]
    created_at: str
    updated_at: str


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


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def paper_record_from_row(row: Any, assets: dict[str, int]) -> PaperRecord:
    asset_id = int(row["asset_id"])
    return PaperRecord(
        paper_id=asset_id,
        asset_id=asset_id,
        title=str(row["title"]),
        authors=json.loads(row["authors"] or "[]"),
        year=row["pub_year"],
        venue=str(row["venue"]),
        venue_short=str(row["venue_short"]),
        doi=str(row["doi"]),
        url=str(row["url"]),
        pdf_url=str(row["pdf_url"]),
        category_id=row["category_id"],
        tags=json.loads(row["tags"] or "[]"),
        status=str(row["status"]),
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
        "status": "bp.status",
        "created_at": "ar.created_at",
        "updated_at": "ar.updated_at",
    }.get(sort, "ar.updated_at")
