"""Shared resource services for Dataset, Knowledge, and Presentation."""

from core.services.resources.models import (
    DatasetRecord,
    KnowledgeRecord,
    PresentationDocumentRecord,
    PresentationRecord,
    ResourceLinkRecord,
    ResourceNotFoundError,
    ResourceRepositoryError,
)
from core.services.resources.repository import ResourceRepository

__all__ = [
    "DatasetRecord",
    "KnowledgeRecord",
    "PresentationDocumentRecord",
    "PresentationRecord",
    "ResourceLinkRecord",
    "ResourceNotFoundError",
    "ResourceRepository",
    "ResourceRepositoryError",
]
