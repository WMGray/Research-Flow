from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from backend.app.dependencies import get_paper_service
from backend.app.schemas.common import APIEnvelope
from backend.app.schemas.papers import GenerateNoteRequest, GeneratePaperNoteRequest, IngestRequest, ParsePdfRequest
from backend.core.services.papers.models import GenerateNoteInput, IngestPaperInput, ParsePdfInput
from backend.core.services.papers.service import PaperService

router = APIRouter(prefix="/api/papers", tags=["papers"])


def envelope(data: Any) -> APIEnvelope:
    return APIEnvelope(ok=True, data=data, error=None)


@router.get("", response_model=APIEnvelope)
def list_papers(
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    papers = [paper.to_dict() for paper in service.list_papers()]
    return envelope({"items": papers, "total": len(papers)})


@router.get("/{paper_id}", response_model=APIEnvelope)
def paper_detail(
    paper_id: str,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    paper = service.get_paper(paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found")
    return envelope(paper.to_dict())


@router.post("/{paper_id}/parse-pdf", response_model=APIEnvelope)
def parse_paper_pdf(
    paper_id: str,
    request: ParsePdfRequest,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        record = service.parse_pdf(ParsePdfInput(paper_id=paper_id, force=request.force, parser=request.parser))
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Paper not found") from error
    return envelope(record.to_dict())


@router.get("/{paper_id}/parser-runs", response_model=APIEnvelope)
def parser_runs(
    paper_id: str,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        runs = [run.to_dict() for run in service.list_parser_runs(paper_id)]
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Paper not found") from error
    return envelope({"items": runs, "total": len(runs)})


@router.post("/{paper_id}/generate-note", response_model=APIEnvelope)
def generate_paper_note(
    paper_id: str,
    request: GeneratePaperNoteRequest | None = None,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        record = service.generate_note_for_paper(paper_id, overwrite=request.overwrite if request else False)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Paper not found") from error
    return envelope(record.to_dict())


@router.post("/{paper_id}/mark-review", response_model=APIEnvelope)
def mark_paper_review(
    paper_id: str,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        record = service.mark_review(paper_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Paper not found") from error
    return envelope(record.to_dict())


@router.post("/{paper_id}/mark-processed", response_model=APIEnvelope)
def mark_paper_processed(
    paper_id: str,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        record = service.mark_processed(paper_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Paper not found") from error
    return envelope(record.to_dict())


@router.post("/{paper_id}/reject", response_model=APIEnvelope)
def reject_paper(
    paper_id: str,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        record = service.reject_paper(paper_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Paper not found") from error
    return envelope(record.to_dict())


@router.post("/ingest", response_model=APIEnvelope)
def ingest_paper(
    request: IngestRequest,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    record = service.ingest(
        IngestPaperInput(
            source=Path(request.source),
            domain=request.domain,
            area=request.area,
            topic=request.topic,
            target_path=request.target_path,
            move=request.move,
        )
    )
    return envelope(record.to_dict())


@router.post("/migrate", response_model=APIEnvelope)
def migrate_paper(
    request: IngestRequest,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    record = service.migrate(
        IngestPaperInput(
            source=Path(request.source),
            domain=request.domain,
            area=request.area,
            topic=request.topic,
            target_path=request.target_path,
            move=True,
        )
    )
    return envelope(record.to_dict())


@router.post("/generate-note", response_model=APIEnvelope)
def generate_note(
    request: GenerateNoteRequest,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    content = service.generate_note_template(
        GenerateNoteInput(
            title=request.title or "",
            year=request.year,
            venue=request.venue or "",
            doi=request.doi or "",
            domain=request.domain or "",
            area=request.area or "",
            topic=request.topic or "",
            tags=request.tags or ["paper"],
        )
    )
    return envelope({"content": content})
