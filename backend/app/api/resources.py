"""Dataset, Knowledge, and Presentation API routes."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.api.papers import envelope
from app.schemas.papers import APIEnvelope, JobResponse
from app.schemas.resources import (
    DatasetCreateRequest,
    DatasetResponse,
    DatasetUpdateRequest,
    KnowledgeCreateRequest,
    KnowledgeResponse,
    KnowledgeUpdateRequest,
    PresentationCreateRequest,
    PresentationDocumentResponse,
    PresentationDocumentRole,
    PresentationDocumentUpdateRequest,
    PresentationResponse,
    PresentationUpdateRequest,
    ResourceLinkResponse,
)
from core.services.resources import ResourceNotFoundError, ResourceRepository
from core.services.resources.models import ResourceVersionConflictError


router = APIRouter(prefix="/api/v1", tags=["resources"])


def get_resource_repository() -> ResourceRepository:
    return ResourceRepository()


def raise_http_error(exc: Exception) -> None:
    if isinstance(exc, ResourceVersionConflictError):
        raise HTTPException(
            status_code=409,
            detail={"code": exc.code, "message": str(exc)},
        )
    if isinstance(exc, ResourceNotFoundError):
        raise HTTPException(
            status_code=404,
            detail={"code": exc.code, "message": str(exc)},
        )
    raise exc


@router.post("/datasets", status_code=status.HTTP_201_CREATED, response_model=APIEnvelope)
def create_dataset(
    request: DatasetCreateRequest,
    repository: ResourceRepository = Depends(get_resource_repository),
) -> APIEnvelope:
    record = repository.create_dataset(request.model_dump())
    return envelope(DatasetResponse.model_validate(asdict(record)))


@router.get("/datasets", response_model=APIEnvelope)
def list_datasets(
    q: str = "",
    task_type: str = "",
    page: int = 1,
    page_size: int = 20,
    repository: ResourceRepository = Depends(get_resource_repository),
) -> APIEnvelope:
    records, total = repository.list_datasets(
        {"q": q, "task_type": task_type, "page": page, "page_size": page_size}
    )
    return envelope(
        [DatasetResponse.model_validate(asdict(record)) for record in records],
        meta={"page": page, "page_size": page_size, "total": total},
    )


@router.get("/datasets/{dataset_id}", response_model=APIEnvelope)
def get_dataset(
    dataset_id: int,
    repository: ResourceRepository = Depends(get_resource_repository),
) -> APIEnvelope:
    try:
        return envelope(DatasetResponse.model_validate(asdict(repository.get_dataset(dataset_id))))
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.patch("/datasets/{dataset_id}", response_model=APIEnvelope)
def update_dataset(
    dataset_id: int,
    request: DatasetUpdateRequest,
    repository: ResourceRepository = Depends(get_resource_repository),
) -> APIEnvelope:
    try:
        record = repository.update_dataset(
            dataset_id,
            request.model_dump(exclude_unset=True),
        )
        return envelope(DatasetResponse.model_validate(asdict(record)))
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.delete("/datasets/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dataset(
    dataset_id: int,
    repository: ResourceRepository = Depends(get_resource_repository),
) -> Response:
    try:
        repository.delete_dataset(dataset_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.post("/knowledge", status_code=status.HTTP_201_CREATED, response_model=APIEnvelope)
def create_knowledge(
    request: KnowledgeCreateRequest,
    repository: ResourceRepository = Depends(get_resource_repository),
) -> APIEnvelope:
    try:
        record = repository.create_knowledge(request.model_dump())
        return envelope(KnowledgeResponse.model_validate(asdict(record)))
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.get("/knowledge/search", response_model=APIEnvelope)
def search_knowledge(
    q: str = "",
    page: int = 1,
    page_size: int = 20,
    repository: ResourceRepository = Depends(get_resource_repository),
) -> APIEnvelope:
    return list_knowledge(q=q, page=page, page_size=page_size, repository=repository)


@router.get("/knowledge", response_model=APIEnvelope)
def list_knowledge(
    q: str = "",
    knowledge_type: str = "",
    review_status: str = "",
    source_paper_asset_id: int | None = None,
    page: int = 1,
    page_size: int = 20,
    repository: ResourceRepository = Depends(get_resource_repository),
) -> APIEnvelope:
    records, total = repository.list_knowledge(
        {
            "q": q,
            "knowledge_type": knowledge_type,
            "review_status": review_status,
            "source_paper_asset_id": source_paper_asset_id,
            "page": page,
            "page_size": page_size,
        }
    )
    return envelope(
        [KnowledgeResponse.model_validate(asdict(record)) for record in records],
        meta={"page": page, "page_size": page_size, "total": total},
    )


@router.get("/knowledge/{knowledge_id}", response_model=APIEnvelope)
def get_knowledge(
    knowledge_id: int,
    repository: ResourceRepository = Depends(get_resource_repository),
) -> APIEnvelope:
    try:
        record = repository.get_knowledge(knowledge_id)
        return envelope(KnowledgeResponse.model_validate(asdict(record)))
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.patch("/knowledge/{knowledge_id}", response_model=APIEnvelope)
def update_knowledge(
    knowledge_id: int,
    request: KnowledgeUpdateRequest,
    repository: ResourceRepository = Depends(get_resource_repository),
) -> APIEnvelope:
    try:
        record = repository.update_knowledge(
            knowledge_id,
            request.model_dump(exclude_unset=True),
        )
        return envelope(KnowledgeResponse.model_validate(asdict(record)))
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.delete("/knowledge/{knowledge_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_knowledge(
    knowledge_id: int,
    repository: ResourceRepository = Depends(get_resource_repository),
) -> Response:
    try:
        repository.delete_knowledge(knowledge_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.post("/presentations", status_code=status.HTTP_201_CREATED, response_model=APIEnvelope)
def create_presentation(
    request: PresentationCreateRequest,
    repository: ResourceRepository = Depends(get_resource_repository),
) -> APIEnvelope:
    try:
        record = repository.create_presentation(request.model_dump())
        return envelope(PresentationResponse.model_validate(asdict(record)))
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.get("/presentations", response_model=APIEnvelope)
def list_presentations(
    q: str = "",
    project_asset_id: int | None = None,
    status_filter: str = Query(default="", alias="status"),
    scene_type: str = "",
    page: int = 1,
    page_size: int = 20,
    repository: ResourceRepository = Depends(get_resource_repository),
) -> APIEnvelope:
    records, total = repository.list_presentations(
        {
            "q": q,
            "project_asset_id": project_asset_id,
            "status": status_filter,
            "scene_type": scene_type,
            "page": page,
            "page_size": page_size,
        }
    )
    return envelope(
        [PresentationResponse.model_validate(asdict(record)) for record in records],
        meta={"page": page, "page_size": page_size, "total": total},
    )


@router.get("/presentations/{presentation_id}", response_model=APIEnvelope)
def get_presentation(
    presentation_id: int,
    repository: ResourceRepository = Depends(get_resource_repository),
) -> APIEnvelope:
    try:
        record = repository.get_presentation(presentation_id)
        return envelope(PresentationResponse.model_validate(asdict(record)))
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.patch("/presentations/{presentation_id}", response_model=APIEnvelope)
def update_presentation(
    presentation_id: int,
    request: PresentationUpdateRequest,
    repository: ResourceRepository = Depends(get_resource_repository),
) -> APIEnvelope:
    try:
        record = repository.update_presentation(
            presentation_id,
            request.model_dump(exclude_unset=True),
        )
        return envelope(PresentationResponse.model_validate(asdict(record)))
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.delete("/presentations/{presentation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_presentation(
    presentation_id: int,
    repository: ResourceRepository = Depends(get_resource_repository),
) -> Response:
    try:
        repository.delete_presentation(presentation_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.get(
    "/presentations/{presentation_id}/documents/{doc_role}",
    response_model=APIEnvelope,
)
def get_presentation_document(
    presentation_id: int,
    doc_role: PresentationDocumentRole,
    repository: ResourceRepository = Depends(get_resource_repository),
) -> APIEnvelope:
    try:
        record = repository.get_presentation_document(presentation_id, doc_role)
        return envelope(PresentationDocumentResponse.model_validate(asdict(record)))
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.put(
    "/presentations/{presentation_id}/documents/{doc_role}",
    response_model=APIEnvelope,
)
def update_presentation_document(
    presentation_id: int,
    doc_role: PresentationDocumentRole,
    request: PresentationDocumentUpdateRequest,
    repository: ResourceRepository = Depends(get_resource_repository),
) -> APIEnvelope:
    try:
        record = repository.update_presentation_document(
            presentation_id=presentation_id,
            doc_role=doc_role,
            content=request.content,
            base_version=request.base_version,
        )
        return envelope(PresentationDocumentResponse.model_validate(asdict(record)))
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.post(
    "/presentations/{presentation_id}/generate-outline",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=APIEnvelope,
)
def generate_presentation_outline(
    presentation_id: int,
    repository: ResourceRepository = Depends(get_resource_repository),
) -> APIEnvelope:
    try:
        job = repository.run_presentation_task(
            presentation_id,
            "presentation_generate_outline",
        )
        return envelope(JobResponse.model_validate(asdict(job)))
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.post(
    "/presentations/{presentation_id}/generate-slides",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=APIEnvelope,
)
def generate_presentation_slides(
    presentation_id: int,
    repository: ResourceRepository = Depends(get_resource_repository),
) -> APIEnvelope:
    try:
        job = repository.run_presentation_task(
            presentation_id,
            "presentation_generate_slides",
        )
        return envelope(JobResponse.model_validate(asdict(job)))
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.post(
    "/presentations/{presentation_id}/export",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=APIEnvelope,
)
def export_presentation(
    presentation_id: int,
    repository: ResourceRepository = Depends(get_resource_repository),
) -> APIEnvelope:
    try:
        job = repository.run_presentation_task(
            presentation_id,
            "presentation_export",
        )
        return envelope(JobResponse.model_validate(asdict(job)))
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


def resource_link_payload(records: list[object]) -> list[ResourceLinkResponse]:
    return [ResourceLinkResponse.model_validate(asdict(record)) for record in records]
