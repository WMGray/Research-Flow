from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from backend.app.dependencies import get_paper_service
from backend.app.schemas.common import APIEnvelope
from backend.app.schemas.papers import SearchAgentSettingsRequest
from backend.core.services.papers.service import PaperService

router = APIRouter(prefix="/api/settings", tags=["settings"])


def envelope(data: Any) -> APIEnvelope:
    return APIEnvelope(ok=True, data=data, error=None)


@router.get("/search-agent", response_model=APIEnvelope)
def get_search_agent_settings(
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    return envelope(service.get_search_agent_settings())


@router.patch("/search-agent", response_model=APIEnvelope)
def update_search_agent_settings(
    request: SearchAgentSettingsRequest,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        settings = service.update_search_agent_settings(request.model_dump(exclude_unset=True))
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return envelope(settings)
