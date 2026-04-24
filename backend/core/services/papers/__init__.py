"""Paper 共享业务服务包。"""

from core.services.papers.models import (
    DocumentNotFoundError,
    DocumentUpdateInput,
    DocumentVersionConflictError,
    DuplicatePaperError,
    PaperCreateInput,
    PaperListInput,
    PaperNotFoundError,
    PaperUpdateInput,
    ParsePaperInput,
)
from core.services.papers.service import PaperService

__all__ = [
    "DocumentNotFoundError",
    "DocumentUpdateInput",
    "DocumentVersionConflictError",
    "DuplicatePaperError",
    "PaperCreateInput",
    "PaperListInput",
    "PaperNotFoundError",
    "PaperService",
    "PaperUpdateInput",
    "ParsePaperInput",
]
