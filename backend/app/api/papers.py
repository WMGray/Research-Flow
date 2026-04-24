from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.schemas.papers import (
    APIEnvelope,
    DocumentResponse,
    DocumentRole,
    DocumentUpdateRequest,
    JobResponse,
    PaperCreateRequest,
    PaperListQuery,
    PaperResponse,
    PaperUpdateRequest,
    ParsedContentResponse,
    ParsePaperRequest,
)
from core.services.papers import (
    DocumentUpdateInput,
    DocumentNotFoundError,
    DocumentVersionConflictError,
    DuplicatePaperError,
    PaperCreateInput,
    PaperListInput,
    PaperNotFoundError,
    PaperUpdateInput,
    ParsePaperInput,
)
from core.services.papers.models import (
    DocumentRecord,
    JobRecord,
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


def to_document_update_input(request: DocumentUpdateRequest) -> DocumentUpdateInput:
    return DocumentUpdateInput(**request.model_dump())


def to_paper_response(record: PaperRecord) -> object:
    return PaperResponse.model_validate(asdict(record))


def to_document_response(record: DocumentRecord) -> object:
    return DocumentResponse.model_validate(asdict(record))


def to_job_response(record: JobRecord) -> object:
    return JobResponse.model_validate(asdict(record))


def to_parsed_content_response(record: ParsedContentRecord) -> object:
    return ParsedContentResponse.model_validate(asdict(record))


def raise_http_error(exc: Exception) -> None:
    if isinstance(exc, DuplicatePaperError):
        raise HTTPException(
            status_code=409, detail={"code": exc.code, "message": str(exc)}
        )
    if isinstance(exc, DocumentVersionConflictError):
        raise HTTPException(
            status_code=409, detail={"code": exc.code, "message": str(exc)}
        )
    if isinstance(exc, (PaperNotFoundError, DocumentNotFoundError)):
        raise HTTPException(
            status_code=404, detail={"code": exc.code, "message": str(exc)}
        )
    raise exc


@router.post("/papers", status_code=status.HTTP_201_CREATED, response_model=APIEnvelope)
def create_paper(
    request: PaperCreateRequest,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        return envelope(to_paper_response(service.create_paper(to_paper_input(request))))
    except Exception as exc:
        raise_http_error(exc)
        raise


@router.get("/papers", response_model=APIEnvelope)
def list_papers(
    q: str = "",
    category_id: int | None = None,
    paper_status: str | None = Query(default=None, alias="status"),
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
        status=paper_status,
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
    except Exception as exc:
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
    except Exception as exc:
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
    except Exception as exc:
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
        return envelope(to_job_response(service.queue_parse(paper_id, to_parse_input(request))))
    except Exception as exc:
        raise_http_error(exc)
        raise


@router.get("/papers/{paper_id}/parsed-content", response_model=APIEnvelope)
def get_parsed_content(
    paper_id: int,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        return envelope(to_parsed_content_response(service.get_parsed_content(paper_id)))
    except Exception as exc:
        raise_http_error(exc)
        raise


@router.get("/papers/{paper_id}/documents/{doc_role}", response_model=APIEnvelope)
def get_document(
    paper_id: int,
    doc_role: DocumentRole,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        return envelope(to_document_response(service.get_document(paper_id, doc_role)))
    except Exception as exc:
        raise_http_error(exc)
        raise


@router.put("/papers/{paper_id}/documents/human", response_model=APIEnvelope)
def update_human_document(
    paper_id: int,
    request: DocumentUpdateRequest,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        return envelope(
            to_document_response(
                service.update_human_document(
                    paper_id, to_document_update_input(request)
                )
            )
        )
    except Exception as exc:
        raise_http_error(exc)
        raise
