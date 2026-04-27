"""Project service layer — repository, DTOs, errors, and serialization helpers."""

from core.services.projects.models import (
    DEFAULT_PAPER_RELATION_TYPE,
    DEFAULT_PROJECT_STATUS,
    PROJECT_DOCUMENTS,
    LinkedPaperNotFoundError,
    LinkedPaperRecord,
    ProjectDocumentNotFoundError,
    ProjectDocumentRecord,
    ProjectDocumentVersionConflictError,
    ProjectNotFoundError,
    ProjectRecord,
    ProjectRepositoryError,
)
from core.services.projects.repository import ProjectRepository, slugify, utc_now
from core.services.projects.serialization import (
    document_to_dict,
    record_to_dict,
    records_to_dicts,
)

__all__ = [
    "DEFAULT_PAPER_RELATION_TYPE",
    "DEFAULT_PROJECT_STATUS",
    "LinkedPaperNotFoundError",
    "LinkedPaperRecord",
    "PROJECT_DOCUMENTS",
    "ProjectDocumentNotFoundError",
    "ProjectDocumentRecord",
    "ProjectDocumentVersionConflictError",
    "ProjectNotFoundError",
    "ProjectRecord",
    "ProjectRepository",
    "ProjectRepositoryError",
    "document_to_dict",
    "record_to_dict",
    "records_to_dicts",
    "slugify",
    "utc_now",
]
