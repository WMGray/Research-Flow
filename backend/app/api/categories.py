from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.papers import envelope
from app.schemas.categories import (
    CategoryCreateRequest,
    CategoryResponse,
    CategoryTreeResponse,
    CategoryUpdateRequest,
)
from app.schemas.papers import APIEnvelope
from core.services.categories import (
    CategoryConflictError,
    CategoryInUseError,
    CategoryInvalidParentError,
    CategoryNotFoundError,
    CategoryRecord,
    CategoryRepository,
)


router = APIRouter(prefix="/api/v1", tags=["categories"])


def get_category_repository() -> CategoryRepository:
    return CategoryRepository()


def raise_http_error(exc: Exception) -> None:
    if isinstance(exc, CategoryNotFoundError):
        raise HTTPException(
            status_code=404,
            detail={"code": exc.code, "message": str(exc)},
        )
    if isinstance(exc, (CategoryConflictError, CategoryInvalidParentError)):
        raise HTTPException(
            status_code=400,
            detail={"code": exc.code, "message": str(exc)},
        )
    if isinstance(exc, CategoryInUseError):
        raise HTTPException(
            status_code=409,
            detail={"code": exc.code, "message": str(exc)},
        )
    raise exc


def to_category_response(record: CategoryRecord) -> CategoryResponse:
    return CategoryResponse.model_validate(asdict(record))


def to_tree(records: list[CategoryRecord]) -> list[CategoryTreeResponse]:
    nodes = {
        record.category_id: CategoryTreeResponse.model_validate(
            {**asdict(record), "children": []}
        )
        for record in records
    }
    roots: list[CategoryTreeResponse] = []
    for record in records:
        node = nodes[record.category_id]
        if record.parent_id is None or record.parent_id not in nodes:
            roots.append(node)
        else:
            nodes[record.parent_id].children.append(node)
    return roots


@router.get("/categories", response_model=APIEnvelope)
def list_categories(
    repository: CategoryRepository = Depends(get_category_repository),
) -> APIEnvelope:
    return envelope(to_tree(repository.list_categories()))


@router.post(
    "/categories",
    status_code=status.HTTP_201_CREATED,
    response_model=APIEnvelope,
)
def create_category(
    request: CategoryCreateRequest,
    repository: CategoryRepository = Depends(get_category_repository),
) -> APIEnvelope:
    try:
        record = repository.create_category(**request.model_dump())
        return envelope(to_category_response(record))
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.patch("/categories/{category_id}", response_model=APIEnvelope)
def update_category(
    category_id: int,
    request: CategoryUpdateRequest,
    repository: CategoryRepository = Depends(get_category_repository),
) -> APIEnvelope:
    try:
        values = request.model_dump(exclude_unset=True)
        record = repository.update_category(
            category_id,
            **values,
            parent_id_provided="parent_id" in values,
        )
        return envelope(to_category_response(record))
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int,
    repository: CategoryRepository = Depends(get_category_repository),
) -> Response:
    try:
        repository.delete_category(category_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise
