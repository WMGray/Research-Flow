from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from backend.app.dependencies import get_paper_service
from backend.app.schemas.common import APIEnvelope
from backend.core.services.papers.service import PaperService

router = APIRouter(prefix="/api/config", tags=["config"])


def envelope(data: Any) -> APIEnvelope:
    return APIEnvelope(ok=True, data=data, error=None)


@router.get("", response_model=APIEnvelope)
def config_health(
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    return envelope(service.config_health())
