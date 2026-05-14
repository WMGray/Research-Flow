from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from backend.app.dependencies import get_paper_service
from backend.app.schemas.common import APIEnvelope
from backend.app.schemas.papers import CandidateDecisionRequest
from backend.core.services.papers.service import PaperService

router = APIRouter(prefix="/api/discover", tags=["discover"])


def envelope(data: Any) -> APIEnvelope:
    return APIEnvelope(ok=True, data=data, error=None)


@router.post("/batches/{batch_id}/candidates/{candidate_id}/decision", response_model=APIEnvelope)
def set_candidate_decision(
    batch_id: str,
    candidate_id: str,
    request: CandidateDecisionRequest,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        candidate = service.set_candidate_decision(batch_id, candidate_id, request.decision)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Candidate not found") from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return envelope(candidate.to_dict())
