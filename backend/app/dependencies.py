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

    settings = get_settings()
    service = PaperService(data_root=settings.data_root, data_layout=settings.data_layout)
    request.app.state.paper_service = service
    return service
