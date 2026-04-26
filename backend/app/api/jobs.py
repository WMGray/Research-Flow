"""Job API routes."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.papers import envelope
from app.schemas.papers import APIEnvelope, JobResponse
from core.services.papers import (
    JobCancelNotAllowedError,
    JobListInput,
    JobNotFoundError,
)
from core.services.papers.models import JobRecord
from core.services.papers.service import PaperService


router = APIRouter(prefix="/api/v1", tags=["jobs"])


def get_paper_service() -> PaperService:
    return PaperService()


def to_job_response(record: JobRecord) -> JobResponse:
    return JobResponse.model_validate(asdict(record))


def raise_http_error(exc: Exception) -> None:
    if isinstance(exc, JobNotFoundError):
        raise HTTPException(
            status_code=404,
            detail={"code": exc.code, "message": str(exc)},
        )
    if isinstance(exc, JobCancelNotAllowedError):
        raise HTTPException(
            status_code=409,
            detail={"code": exc.code, "message": str(exc)},
        )
    raise exc


@router.get("/jobs", response_model=APIEnvelope)
def list_jobs(
    page: int = 1,
    page_size: int = 20,
    resource_type: str | None = None,
    resource_id: int | None = None,
    job_status: str | None = Query(default=None, alias="status"),
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    jobs, total = service.list_jobs(
        JobListInput(
            page=page,
            page_size=page_size,
            resource_type=resource_type,
            resource_id=resource_id,
            status=job_status,
        )
    )
    return envelope(
        [JobResponse.model_validate(asdict(job)) for job in jobs],
        meta={"page": page, "page_size": page_size, "total": total},
    )


@router.get("/jobs/{job_id}", response_model=APIEnvelope)
def get_job(
    job_id: str,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        return envelope(to_job_response(service.get_job(job_id)))
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.post("/jobs/{job_id}/cancel", response_model=APIEnvelope)
def cancel_job(
    job_id: str,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        return envelope(to_job_response(service.cancel_job(job_id)))
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise
