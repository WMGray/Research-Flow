from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.api.paper_download import get_paper_download_service
from app.schemas.paper_download import PaperResolveRequest, PaperResolveResponse
from app.schemas.papers import (
    APIEnvelope,
    DocumentResponse,
    DocumentUpdateRequest,
    JobResponse,
    PaperArtifactResponse,
    PaperCreateRequest,
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
from core.services.paper_download.service import PaperDownloadService
from core.services.papers import (
    DocumentNotFoundError,
    DocumentUpdateInput,
    DocumentVersionConflictError,
    DuplicatePaperError,
    PaperCreateInput,
    PaperListInput,
    PaperNotFoundError,
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
from core.services.papers.service import PaperService


router = APIRouter(prefix="/api/v1", tags=["papers"])


def envelope(data: object = None, meta: dict[str, object] | None = None) -> APIEnvelope:
    return APIEnvelope(data=data, meta=meta or {}, error=None)


def get_paper_service() -> PaperService:
    return PaperService()


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


def to_parsed_content_response(record: ParsedContentRecord) -> ParsedContentResponse:
    return ParsedContentResponse.model_validate(asdict(record))


def raise_http_error(exc: Exception) -> None:
    if isinstance(exc, DuplicatePaperError):
        raise HTTPException(
            status_code=409,
            detail={"code": exc.code, "message": str(exc)},
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
    raise exc


@router.post("/papers/resolve", response_model=APIEnvelope)
def resolve_paper(
    request: PaperResolveRequest,
    service: PaperDownloadService = Depends(get_paper_download_service),
) -> APIEnvelope:
    row = service.resolve(request)
    return envelope(PaperResolveResponse.model_validate(asdict(row)))


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


@router.post("/papers/{paper_id}/confirm-review", response_model=APIEnvelope)
def confirm_review(
    paper_id: int,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        return envelope(to_paper_response(service.confirm_review(paper_id)))
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
