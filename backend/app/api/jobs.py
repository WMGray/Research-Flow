from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException

from app.api.papers import envelope
from app.schemas.papers import APIEnvelope, JobResponse
from core.services.papers.models import PaperNotFoundError
from core.services.papers.service import PaperService


router = APIRouter(prefix="/api/v1", tags=["jobs"])


def get_paper_service() -> PaperService:
    return PaperService()


@router.get("/jobs/{job_id}", response_model=APIEnvelope)
def get_job(
    job_id: str,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        return envelope(JobResponse.model_validate(asdict(service.get_job(job_id))))
    except PaperNotFoundError as exc:
        raise HTTPException(
            status_code=404, detail={"code": exc.code, "message": str(exc)}
        )
