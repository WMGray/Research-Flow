from __future__ import annotations

from fastapi import Request

from backend.core.config import get_settings
from backend.core.services.papers.service import PaperService


def get_paper_service(request: Request) -> PaperService:
    library = getattr(request.app.state, "library", None)
    if isinstance(library, PaperService):
        return library

    service = getattr(request.app.state, "paper_service", None)
    if isinstance(service, PaperService):
        return service

    service = PaperService(data_root=get_settings().data_root)
    request.app.state.paper_service = service
    return service
