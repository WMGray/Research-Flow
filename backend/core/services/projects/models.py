"""Project DTOs, errors, and constants."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


PROJECT_DOCUMENTS: tuple[tuple[str, str, str], ...] = (
    ("overview", "overview.md", "# Overview\n\n"),
    ("related_work", "related-work.md", "# Related Work\n\n"),
    ("method", "method.md", "# Method\n\n"),
    ("experiment", "experiment.md", "# Experiment\n\n"),
    ("conclusion", "conclusion.md", "# Conclusion\n\n"),
    ("manuscript", "manuscript.md", "# Manuscript\n\n"),
)
DEFAULT_PROJECT_STATUS = "planning"
DEFAULT_PAPER_RELATION_TYPE = "related_work"


class ProjectRepositoryError(RuntimeError):
    code = "PROJECT_REPOSITORY_ERROR"


class ProjectNotFoundError(ProjectRepositoryError):
    code = "PROJECT_NOT_FOUND"


class ProjectDocumentNotFoundError(ProjectRepositoryError):
    code = "PROJECT_DOCUMENT_NOT_FOUND"


class ProjectDocumentVersionConflictError(ProjectRepositoryError):
    code = "PROJECT_DOCUMENT_VERSION_CONFLICT"


class LinkedPaperNotFoundError(ProjectRepositoryError):
    code = "PAPER_NOT_FOUND"


@dataclass(frozen=True, slots=True)
class ProjectRecord:
    project_id: int
    asset_id: int
    name: str
    project_slug: str
    status: str
    summary: str
    owner: str
    assets: dict[str, int]
    created_at: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class ProjectDocumentRecord:
    project_id: int
    doc_id: int
    doc_role: str
    path: Path
    content: str
    version: int
    updated_at: str


@dataclass(frozen=True, slots=True)
class LinkedPaperRecord:
    paper_id: int
    title: str
    status: str
    relation_type: str
