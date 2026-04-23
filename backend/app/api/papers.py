from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.schemas.papers import (
    APIEnvelope,
    DocumentRole,
    DocumentUpdateRequest,
    PaperCreateRequest,
    PaperListQuery,
    PaperUpdateRequest,
    ParsePaperRequest,
)
from app.services.papers.models import (
    DocumentNotFoundError,
    DocumentVersionConflictError,
    DuplicatePaperError,
    PaperNotFoundError,
)
from app.services.papers.service import PaperService


router = APIRouter(prefix="/api/v1", tags=["papers"])


def envelope(data: object = None, meta: dict[str, object] | None = None) -> APIEnvelope:
    return APIEnvelope(data=data, meta=meta or {}, error=None)


def get_paper_service() -> PaperService:
    return PaperService()


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
        return envelope(service.create_paper(request))
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
    papers, total = service.list_papers(query)
    return envelope(
        papers,
        meta={"page": query.page, "page_size": query.page_size, "total": total},
    )


@router.get("/papers/{paper_id}", response_model=APIEnvelope)
def get_paper(
    paper_id: int,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        return envelope(service.get_paper(paper_id))
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
        return envelope(service.update_paper(paper_id, request))
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
        return envelope(service.queue_parse(paper_id, request))
    except Exception as exc:
        raise_http_error(exc)
        raise


@router.get("/papers/{paper_id}/parsed-content", response_model=APIEnvelope)
def get_parsed_content(
    paper_id: int,
    service: PaperService = Depends(get_paper_service),
) -> APIEnvelope:
    try:
        return envelope(service.get_parsed_content(paper_id))
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
        return envelope(service.get_document(paper_id, doc_role))
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
        return envelope(service.update_human_document(paper_id, request))
    except Exception as exc:
        raise_http_error(exc)
        raise
