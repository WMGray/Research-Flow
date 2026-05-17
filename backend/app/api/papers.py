from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from backend.app.dependencies import get_paper_service
from backend.app.schemas.common import APIEnvelope
from backend.app.schemas.papers import (
    BindAssetsRequest,
    CreateLibraryFolderRequest,
    GenerateNoteRequest,
    GeneratePaperNoteRequest,
    ImportPaperRequest,
    IngestRequest,
    ParsePdfRequest,
    RefreshMetadataRequest,
    ResearchLogRequest,
    ReviewDecisionRequest,
    UpdateClassificationRequest,
    UpdateMetadataRequest,
    UpdateStarRequest,
)
from backend.core.services.papers.models import GenerateNoteInput, ImportPaperInput, IngestPaperInput, ParsePdfInput, ReviewDecisionInput, UpdateClassificationInput
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


@router.post("/import", response_model=APIEnvelope)
def import_paper(
    request: ImportPaperRequest,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        record = service.import_paper(
            ImportPaperInput(
                title=request.title,
                source=Path(request.source) if request.source else None,
                domain=request.domain,
                area=request.area,
                topic=request.topic,
                authors=request.authors,
                year=request.year,
                venue=request.venue,
                doi=request.doi,
                arxiv_id=request.arxiv_id,
                url=request.url,
                abstract=request.abstract,
                summary=request.summary,
                tags=request.tags,
            )
        )
        if request.refresh_metadata:
            record = service.refresh_metadata(record.paper_id, {"title": request.title, "doi": request.doi, "arxiv_id": request.arxiv_id, "url": request.url})
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=f"Source not found: {error}") from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return envelope(record.to_dict())


@router.get("/{paper_id}", response_model=APIEnvelope)
def paper_detail(
    paper_id: str,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    paper = service.get_paper(paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found")
    return envelope(paper.to_dict())


@router.patch("/{paper_id}/metadata", response_model=APIEnvelope)
def update_paper_metadata(
    paper_id: str,
    request: UpdateMetadataRequest,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        record = service.update_metadata(paper_id, request.model_dump(exclude_unset=True))
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Paper not found") from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return envelope(record.to_dict())


@router.post("/{paper_id}/refresh-metadata", response_model=APIEnvelope)
def refresh_paper_metadata(
    paper_id: str,
    request: RefreshMetadataRequest | None = None,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        record = service.refresh_metadata(paper_id, request.model_dump(exclude_unset=True) if request else {})
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Paper not found") from error
    return envelope(record.to_dict())


@router.get("/{paper_id}/metadata/sources", response_model=APIEnvelope)
def paper_metadata_sources(
    paper_id: str,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        data = service.metadata_sources(paper_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Paper not found") from error
    return envelope(data)


@router.get("/{paper_id}/content", response_model=APIEnvelope)
def paper_content(
    paper_id: str,
    max_chars: int = 4000,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        data = service.paper_content(paper_id, max_chars=max_chars)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Paper not found") from error
    return envelope(data)


@router.patch("/{paper_id}/star", response_model=APIEnvelope)
def update_paper_star(
    paper_id: str,
    request: UpdateStarRequest,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        record = service.set_starred(paper_id, request.starred)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Paper not found") from error
    return envelope(record.to_dict())


@router.patch("/{paper_id}/assets", response_model=APIEnvelope)
def bind_paper_assets(
    paper_id: str,
    request: BindAssetsRequest,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        record = service.bind_assets(paper_id, Path(request.source), move=request.move)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=f"Source or paper not found: {error}") from error
    return envelope(record.to_dict())


@router.get("/{paper_id}/research-logs", response_model=APIEnvelope)
def list_research_logs(
    paper_id: str,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        logs = service.list_research_logs(paper_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Paper not found") from error
    return envelope({"items": logs, "total": len(logs)})


@router.post("/{paper_id}/research-logs", response_model=APIEnvelope)
def create_research_log(
    paper_id: str,
    request: ResearchLogRequest,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        log = service.create_research_log(paper_id, request.model_dump())
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Paper not found") from error
    return envelope(log)


@router.patch("/{paper_id}/research-logs/{log_id}", response_model=APIEnvelope)
def update_research_log(
    paper_id: str,
    log_id: str,
    request: ResearchLogRequest,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        log = service.update_research_log(paper_id, log_id, request.model_dump())
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Paper or log not found") from error
    return envelope(log)


@router.delete("/{paper_id}/research-logs/{log_id}", response_model=APIEnvelope)
def delete_research_log(
    paper_id: str,
    log_id: str,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        service.delete_research_log(paper_id, log_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Paper or log not found") from error
    return envelope({"deleted": True, "log_id": log_id})


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


@router.get("/{paper_id}/events", response_model=APIEnvelope)
def paper_events(
    paper_id: str,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        events = [event.to_dict() for event in service.list_paper_events(paper_id)]
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Paper not found") from error
    return envelope({"items": events, "total": len(events)})


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
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return envelope(record.to_dict())


@router.post("/{paper_id}/review-refined", response_model=APIEnvelope)
def review_paper_refined(
    paper_id: str,
    request: ReviewDecisionRequest,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        record = service.review_refined(ReviewDecisionInput(paper_id=paper_id, decision=request.decision, comment=request.comment))
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Paper not found") from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return envelope(record.to_dict())


@router.post("/{paper_id}/review-note", response_model=APIEnvelope)
def review_paper_note(
    paper_id: str,
    request: ReviewDecisionRequest,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        record = service.review_note(ReviewDecisionInput(paper_id=paper_id, decision=request.decision, comment=request.comment))
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Paper not found") from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return envelope(record.to_dict())


@router.patch("/{paper_id}/classification", response_model=APIEnvelope)
def update_paper_classification(
    paper_id: str,
    request: UpdateClassificationRequest,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        record = service.update_classification(
            UpdateClassificationInput(
                paper_id=paper_id,
                domain=request.domain,
                area=request.area,
                topic=request.topic,
                title=request.title,
                venue=request.venue,
                year=request.year,
                tags=request.tags,
                status=request.status,
                paper_path=request.paper_path,
                note_path=request.note_path,
                refined_path=request.refined_path,
            )
        )
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Paper not found") from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return envelope(record.to_dict())


@router.post("/library-folders", response_model=APIEnvelope)
def create_library_folder(
    request: CreateLibraryFolderRequest,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        folder = service.create_library_folder(request.path)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return envelope(folder)


@router.post("/{paper_id}/mark-review", response_model=APIEnvelope)
def mark_paper_review(
    paper_id: str,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    """Deprecated compatibility endpoint. Workflow UI no longer uses this shortcut."""
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
    """Deprecated compatibility endpoint. Workflow UI no longer uses this shortcut."""
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
    """Deprecated compatibility endpoint for manual/internal ingest flows."""
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
    """Deprecated compatibility endpoint for manual/internal migrate flows."""
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
