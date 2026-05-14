from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from backend.app.dependencies import get_paper_service
from backend.app.schemas.common import APIEnvelope
from backend.core.services.papers.service import PaperService

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def envelope(data: Any) -> APIEnvelope:
    return APIEnvelope(ok=True, data=data, error=None)


@router.get("/home", response_model=APIEnvelope)
def dashboard_home(
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    return envelope(service.dashboard_home())


@router.get("/papers-overview", response_model=APIEnvelope)
def dashboard_papers_overview(
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    return envelope(service.dashboard_papers_overview())


@router.get("/discover", response_model=APIEnvelope)
def dashboard_discover(
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    return envelope(service.dashboard_discover())


@router.get("/acquire", response_model=APIEnvelope)
def dashboard_acquire(
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    return envelope(service.dashboard_acquire())


@router.get("/library", response_model=APIEnvelope)
def dashboard_library(
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    return envelope(service.dashboard_library())
