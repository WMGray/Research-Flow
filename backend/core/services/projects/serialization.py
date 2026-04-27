"""Dict conversion helpers for Project records."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from core.services.projects.models import (
    LinkedPaperRecord,
    ProjectDocumentRecord,
    ProjectRecord,
)


def records_to_dicts(records: list[LinkedPaperRecord]) -> list[dict[str, Any]]:
    return [asdict(record) for record in records]


def record_to_dict(record: ProjectRecord) -> dict[str, Any]:
    return {
        "project_id": record.project_id,
        "asset_id": record.asset_id,
        "name": record.name,
        "project_slug": record.project_slug,
        "status": record.status,
        "summary": record.summary,
        "owner": record.owner,
        "assets": record.assets,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }


def document_to_dict(record: ProjectDocumentRecord) -> dict[str, Any]:
    return {
        "project_id": record.project_id,
        "doc_id": record.doc_id,
        "doc_role": record.doc_role,
        "content": record.content,
        "version": record.version,
        "updated_at": record.updated_at,
    }
