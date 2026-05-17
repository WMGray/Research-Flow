from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from backend.app.dependencies import get_paper_service
from backend.app.schemas.common import APIEnvelope
from backend.app.schemas.papers import BatchCandidateDecisionRequest, CandidateDecisionRequest, CreateSearchBatchRequest
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


@router.post("/batches/{batch_id}/candidates/batch-decision", response_model=APIEnvelope)
def set_candidate_batch_decision(
    batch_id: str,
    request: BatchCandidateDecisionRequest,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        candidates = service.set_candidate_batch_decision(batch_id, request.candidate_ids, request.decision)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Candidate not found") from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return envelope({"items": [candidate.to_dict() for candidate in candidates], "total": len(candidates)})


@router.post("/search-batches", response_model=APIEnvelope)
def create_search_batch(
    request: CreateSearchBatchRequest,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        result = service.create_search_batch(request.model_dump())
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return envelope(result)


@router.get("/search-jobs/{job_id}", response_model=APIEnvelope)
def get_search_job(
    job_id: str,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        job = service.get_search_job(job_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Search job not found") from error
    return envelope(job)
