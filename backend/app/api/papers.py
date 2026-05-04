from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response, status
from fastapi.responses import FileResponse

from app.api.paper_download import get_paper_download_service
from app.schemas.paper_download import PaperResolveRequest, PaperResolveResponse
from app.schemas.papers import (
    APIEnvelope,
    DocumentResponse,
    DocumentUpdateRequest,
    JobResponse,
    PaperArtifactResponse,
    PaperConfirmPipelineResponse,
    PaperCreateRequest,
    PaperImportPipelineResponse,
    PaperListQuery,
    PaperPipelineRequest,
    PaperPipelineResponse,
    PaperPipelineRunResponse,
    PaperResponse,
    RefineParseRequest,
    PaperUpdateRequest,
    ParsedContentResponse,
    ParsePaperRequest,
    SectionDocumentResponse,
)
from app.schemas.resources import ResourceLinkResponse
from core.services.papers.download import PaperDownloadService
from core.services.papers import (
    DocumentNotFoundError,
    DocumentUpdateInput,
    DocumentVersionConflictError,
    DuplicatePaperError,
    PaperCreateInput,
    PaperListInput,
    PaperNotFoundError,
    PaperRetryNotAllowedError,
    PaperPipelineInput,
    PaperUpdateInput,
    ParsePaperInput,
    RefineParseInput,
)
from core.services.papers.models import (
    DocumentRecord,
    JobRecord,
    PaperArtifactRecord,
    PaperPipelineRecord,
    PaperPipelineRunRecord,
    PaperRecord,
    ParsedContentRecord,
)
from core.services.papers.metadata import (
    authors_from_resolution,
    infer_ccf_rank,
    infer_sci_quartile,
)
from core.services.papers.service import PaperService
from core.services.resources import ResourceNotFoundError, ResourceRepository
from worker.tasks.papers import (
    confirm_pipeline as confirm_pipeline_task,
    import_pipeline as import_pipeline_task,
    retry_pipeline as retry_pipeline_task,
)


router = APIRouter(prefix="/api/v1", tags=["papers"])


def envelope(data: object = None, meta: dict[str, object] | None = None) -> APIEnvelope:
    return APIEnvelope(data=data, meta=meta or {}, error=None)


def get_paper_service() -> PaperService:
    return PaperService()


def get_resource_repository() -> ResourceRepository:
    return ResourceRepository()


def to_paper_input(request: PaperCreateRequest) -> PaperCreateInput:
    return PaperCreateInput(**request.model_dump())


def to_paper_update_input(request: PaperUpdateRequest) -> PaperUpdateInput:
    return PaperUpdateInput(values=request.model_dump(exclude_unset=True))


def to_parse_input(request: ParsePaperRequest) -> ParsePaperInput:
    return ParsePaperInput(**request.model_dump())


def to_refine_input(request: RefineParseRequest) -> RefineParseInput:
    return RefineParseInput(**request.model_dump())


def to_pipeline_input(request: PaperPipelineRequest) -> PaperPipelineInput:
    return PaperPipelineInput(**request.model_dump())


def to_document_update_input(request: DocumentUpdateRequest) -> DocumentUpdateInput:
    return DocumentUpdateInput(**request.model_dump())


def to_paper_response(record: PaperRecord) -> PaperResponse:
    return PaperResponse.model_validate(asdict(record))


def to_document_response(record: DocumentRecord) -> DocumentResponse:
    return DocumentResponse.model_validate(asdict(record))


def to_job_response(record: JobRecord) -> JobResponse:
    return JobResponse.model_validate(asdict(record))


def to_artifact_response(record: PaperArtifactRecord) -> PaperArtifactResponse:
    return PaperArtifactResponse.model_validate(asdict(record))


def to_pipeline_run_response(
    record: PaperPipelineRunRecord,
) -> PaperPipelineRunResponse:
    return PaperPipelineRunResponse.model_validate(asdict(record))


def to_pipeline_response(record: PaperPipelineRecord) -> PaperPipelineResponse:
    return PaperPipelineResponse.model_validate(asdict(record))


def to_confirm_pipeline_response(
    *,
    paper: PaperRecord,
    job: JobRecord,
) -> PaperConfirmPipelineResponse:
    return PaperConfirmPipelineResponse(
        paper=to_paper_response(paper),
        job=to_job_response(job),
    )


def to_import_pipeline_response(
    *,
    paper: PaperRecord,
    job: JobRecord,
) -> PaperImportPipelineResponse:
    return PaperImportPipelineResponse(
        paper=to_paper_response(paper),
        job=to_job_response(job),
    )


def to_parsed_content_response(record: ParsedContentRecord) -> ParsedContentResponse:
    return ParsedContentResponse.model_validate(asdict(record))


def to_resource_link_responses(records: list[object]) -> list[ResourceLinkResponse]:
    return [ResourceLinkResponse.model_validate(asdict(record)) for record in records]


def to_paper_resolve_response(record: object) -> PaperResolveResponse:
    payload = asdict(record)
    payload["authors"] = authors_from_resolution(record)
    venue = str(payload.get("venue") or "")
    payload["ccf_rank"] = infer_ccf_rank(venue)
    payload["sci_quartile"] = infer_sci_quartile(venue)
    return PaperResolveResponse.model_validate(payload)


def inline_file_response(path: Path, *, media_type: str, filename: str) -> FileResponse:
    headers = {"Content-Disposition": f'inline; filename="{filename}"'}
    return FileResponse(path, media_type=media_type, filename=filename, headers=headers)


def raise_http_error(exc: Exception) -> None:
    if isinstance(exc, DuplicatePaperError):
        detail: dict[str, object] = {"code": exc.code, "message": str(exc)}
        if exc.paper_id is not None:
            detail["details"] = {"paper_id": exc.paper_id}
        raise HTTPException(
            status_code=409,
            detail=detail,
        )
    if isinstance(exc, PaperRetryNotAllowedError):
        raise HTTPException(
            status_code=409,
            detail={
                "code": exc.code,
                "message": str(exc),
                "details": {
                    "paper_id": exc.paper_id,
                    "status": exc.status,
                },
            },
        )
    if isinstance(exc, DocumentVersionConflictError):
        raise HTTPException(
            status_code=409,
            detail={"code": exc.code, "message": str(exc)},
        )
    if isinstance(exc, (PaperNotFoundError, DocumentNotFoundError)):
        raise HTTPException(
            status_code=404,
            detail={"code": exc.code, "message": str(exc)},
        )
    if isinstance(exc, ResourceNotFoundError):
        raise HTTPException(
            status_code=404,
            detail={"code": exc.code, "message": str(exc)},
        )
    raise exc


@router.post("/papers/resolve", response_model=APIEnvelope)
def resolve_paper(
    request: PaperResolveRequest,
    service: PaperDownloadService = Depends(get_paper_download_service),
) -> APIEnvelope:
    row = service.resolve(request)
    return envelope(to_paper_resolve_response(row))


@router.post("/papers", status_code=status.HTTP_201_CREATED, response_model=APIEnvelope)
def create_paper(
    request: PaperCreateRequest,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        return envelope(to_paper_response(service.create_paper(to_paper_input(request))))
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.post(
    "/papers/{paper_id}/import-pipeline",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=APIEnvelope,
)
def start_import_pipeline(
    paper_id: int,
    background_tasks: BackgroundTasks,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        queued_job = service.create_import_pipeline_job(paper_id)
        if hasattr(import_pipeline_task, "delay"):
            import_pipeline_task.delay(paper_id, queued_job.job_id)
        else:
            background_tasks.add_task(import_pipeline_task, paper_id, queued_job.job_id)
        paper = service.get_paper(paper_id)
        return envelope(to_import_pipeline_response(paper=paper, job=queued_job))
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.post(
    "/papers/{paper_id}/retry-pipeline",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=APIEnvelope,
)
def retry_paper_pipeline(
    paper_id: int,
    background_tasks: BackgroundTasks,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        queued_job = service.create_retry_pipeline_job(paper_id)
        if hasattr(retry_pipeline_task, "delay"):
            retry_pipeline_task.delay(paper_id, queued_job.job_id)
        else:
            background_tasks.add_task(retry_pipeline_task, paper_id, queued_job.job_id)
        paper = service.get_paper(paper_id)
        return envelope(to_import_pipeline_response(paper=paper, job=queued_job))
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.get("/papers", response_model=APIEnvelope)
def list_papers(
    q: str = "",
    category_id: int | None = None,
    paper_stage: str | None = Query(default=None, alias="paper_stage"),
    year_from: int | None = None,
    year_to: int | None = None,
    page: int = 1,
    page_size: int = 20,
    sort: str = "updated_at",
    order: str = "desc",
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    query = PaperListQuery(
        q=q,
        category_id=category_id,
        paper_stage=paper_stage,
        year_from=year_from,
        year_to=year_to,
        page=page,
        page_size=page_size,
        sort=sort,
        order=order,
    )
    service_query = PaperListInput(**query.model_dump())
    papers, total = service.list_papers(service_query)
    return envelope(
        [to_paper_response(paper) for paper in papers],
        meta={"page": query.page, "page_size": query.page_size, "total": total},
    )


@router.get("/papers/{paper_id}", response_model=APIEnvelope)
def get_paper(
    paper_id: int,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        return envelope(to_paper_response(service.get_paper(paper_id)))
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.patch("/papers/{paper_id}", response_model=APIEnvelope)
def update_paper(
    paper_id: int,
    request: PaperUpdateRequest,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        return envelope(
            to_paper_response(
                service.update_paper(paper_id, to_paper_update_input(request))
            )
        )
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.delete("/papers/{paper_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_paper(
    paper_id: int,
    service: PaperService = Depends(get_paper_service),
) -> Response:
    try:
        service.delete_paper(paper_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.post(
    "/papers/{paper_id}/download",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=APIEnvelope,
)
def download_paper(
    paper_id: int,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        return envelope(to_job_response(service.run_download(paper_id)))
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.post(
    "/papers/{paper_id}/parse",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=APIEnvelope,
)
def parse_paper(
    paper_id: int,
    request: ParsePaperRequest,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        return envelope(to_job_response(service.run_parse(paper_id, to_parse_input(request))))
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.get("/papers/{paper_id}/parsed", response_model=APIEnvelope)
def get_parsed_content(
    paper_id: int,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        return envelope(to_parsed_content_response(service.get_parsed_content(paper_id)))
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.get("/papers/{paper_id}/note", response_model=APIEnvelope)
def get_note(
    paper_id: int,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        return envelope(to_document_response(service.get_document(paper_id, "note")))
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.get("/papers/{paper_id}/note/raw")
def get_note_raw(
    paper_id: int,
    service: PaperService = Depends(get_paper_service),
) -> FileResponse:
    try:
        document = service.get_document(paper_id, "note")
        if not document.path.exists():
            raise DocumentNotFoundError(f"Document file not found: {paper_id}/note")
        return inline_file_response(
            document.path,
            media_type="text/markdown; charset=utf-8",
            filename=document.path.name,
        )
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.put("/papers/{paper_id}/note", response_model=APIEnvelope)
def update_note(
    paper_id: int,
    request: DocumentUpdateRequest,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        return envelope(
            to_document_response(
                service.update_document(
                    paper_id,
                    "note",
                    to_document_update_input(request),
                )
            )
        )
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.get("/papers/{paper_id}/pdf")
def get_pdf_file(
    paper_id: int,
    service: PaperService = Depends(get_paper_service),
) -> FileResponse:
    try:
        path = service.get_pdf_file_path(paper_id)
        if not path.exists():
            raise DocumentNotFoundError(f"PDF file not found: {paper_id}")
        return inline_file_response(
            path,
            media_type="application/pdf",
            filename=path.name,
        )
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.get("/papers/{paper_id}/parsed/refined", response_model=APIEnvelope)
def get_refined_document(
    paper_id: int,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        return envelope(to_document_response(service.get_document(paper_id, "refined")))
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.get("/papers/{paper_id}/parsed/refined/raw")
def get_refined_document_raw(
    paper_id: int,
    service: PaperService = Depends(get_paper_service),
) -> FileResponse:
    try:
        document = service.get_document(paper_id, "refined")
        if not document.path.exists():
            raise DocumentNotFoundError(f"Document file not found: {paper_id}/refined")
        return inline_file_response(
            document.path,
            media_type="text/markdown; charset=utf-8",
            filename=document.path.name,
        )
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.put("/papers/{paper_id}/parsed/refined", response_model=APIEnvelope)
def update_refined_document(
    paper_id: int,
    request: DocumentUpdateRequest,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        return envelope(
            to_document_response(
                service.update_document(
                    paper_id,
                    "refined",
                    to_document_update_input(request),
                )
            )
        )
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.get("/papers/{paper_id}/parsed/sections", response_model=APIEnvelope)
def get_sections(
    paper_id: int,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        sections = [
            SectionDocumentResponse.model_validate(section)
            for section in service.list_sections(paper_id)
        ]
        return envelope(sections)
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.post(
    "/papers/{paper_id}/refine-parse",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=APIEnvelope,
)
def refine_parse(
    paper_id: int,
    request: RefineParseRequest,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        return envelope(to_job_response(service.run_refine_parse(paper_id, to_refine_input(request))))
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.post("/papers/{paper_id}/submit-review", response_model=APIEnvelope)
def submit_review(
    paper_id: int,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        return envelope(to_paper_response(service.submit_review(paper_id)))
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.post(
    "/papers/{paper_id}/confirm-review",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=APIEnvelope,
)
def confirm_review(
    paper_id: int,
    background_tasks: BackgroundTasks,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        queued_job = service.create_confirm_pipeline_job(paper_id)
        if hasattr(confirm_pipeline_task, "delay"):
            confirm_pipeline_task.delay(paper_id, queued_job.job_id)
        else:
            background_tasks.add_task(confirm_pipeline_task, paper_id, queued_job.job_id)
        paper = service.get_paper(paper_id)
        return envelope(to_confirm_pipeline_response(paper=paper, job=queued_job))
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.post(
    "/papers/{paper_id}/split-sections",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=APIEnvelope,
)
def split_sections(
    paper_id: int,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        return envelope(to_job_response(service.run_split_sections(paper_id)))
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.post(
    "/papers/{paper_id}/generate-note",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=APIEnvelope,
)
def generate_note(
    paper_id: int,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        return envelope(to_job_response(service.run_generate_note(paper_id)))
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.post(
    "/papers/{paper_id}/pipeline",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=APIEnvelope,
)
def run_paper_pipeline(
    paper_id: int,
    request: PaperPipelineRequest,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        return envelope(
            to_pipeline_response(
                service.run_pipeline(paper_id, to_pipeline_input(request))
            )
        )
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.post(
    "/papers/{paper_id}/extract-knowledge",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=APIEnvelope,
)
def extract_knowledge(
    paper_id: int,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        return envelope(to_job_response(service.run_extract_knowledge(paper_id)))
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.post(
    "/papers/{paper_id}/extract-datasets",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=APIEnvelope,
)
def extract_datasets(
    paper_id: int,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        return envelope(to_job_response(service.run_extract_datasets(paper_id)))
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.get("/papers/{paper_id}/assets", response_model=APIEnvelope)
def get_assets(
    paper_id: int,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        return envelope(service.get_paper(paper_id).assets)
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.get("/papers/{paper_id}/knowledge", response_model=APIEnvelope)
def get_paper_knowledge(
    paper_id: int,
    repository: ResourceRepository = Depends(get_resource_repository),
) -> APIEnvelope:
    try:
        return envelope(
            to_resource_link_responses(repository.list_knowledge_for_paper(paper_id))
        )
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.get("/papers/{paper_id}/datasets", response_model=APIEnvelope)
def get_paper_datasets(
    paper_id: int,
    repository: ResourceRepository = Depends(get_resource_repository),
) -> APIEnvelope:
    try:
        return envelope(
            to_resource_link_responses(
                repository.list_links_from_source(
                    source_id=paper_id,
                    target_type="Dataset",
                )
            )
        )
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.get("/papers/{paper_id}/artifacts", response_model=APIEnvelope)
def get_artifacts(
    paper_id: int,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        return envelope(
            [to_artifact_response(record) for record in service.list_artifacts(paper_id)]
        )
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.get("/papers/{paper_id}/pipeline-runs", response_model=APIEnvelope)
def get_pipeline_runs(
    paper_id: int,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        return envelope(
            [
                to_pipeline_run_response(record)
                for record in service.list_pipeline_runs(paper_id)
            ]
        )
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise
