"""Project API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.papers import envelope
from app.schemas.papers import APIEnvelope
from app.schemas.projects import (
    ProjectCreateRequest,
    ProjectDocumentRole,
    ProjectDocumentUpdateRequest,
    ProjectListQuery,
    ProjectPaperLinkRequest,
    ProjectStatus,
    ProjectUpdateRequest,
)
from core.services.projects import (
    LinkedPaperNotFoundError,
    ProjectDocumentNotFoundError,
    ProjectDocumentVersionConflictError,
    ProjectNotFoundError,
    ProjectRepository,
    document_to_dict,
    record_to_dict,
    records_to_dicts,
)


router = APIRouter(prefix="/api/v1", tags=["projects"])


def get_project_repository() -> ProjectRepository:
    return ProjectRepository()


def raise_http_error(exc: Exception) -> None:
    if isinstance(exc, ProjectDocumentVersionConflictError):
        raise HTTPException(
            status_code=409,
            detail={"code": exc.code, "message": str(exc)},
        )
    if isinstance(
        exc,
        (ProjectNotFoundError, ProjectDocumentNotFoundError, LinkedPaperNotFoundError),
    ):
        raise HTTPException(
            status_code=404,
            detail={"code": exc.code, "message": str(exc)},
        )
    raise exc


@router.post("/projects", status_code=status.HTTP_201_CREATED, response_model=APIEnvelope)
def create_project(
    request: ProjectCreateRequest,
    repository: ProjectRepository = Depends(get_project_repository),
) -> APIEnvelope:
    return envelope(record_to_dict(repository.create_project(request.model_dump())))


@router.get("/projects", response_model=APIEnvelope)
def list_projects(
    q: str = "",
    project_status: ProjectStatus | None = Query(default=None, alias="status"),
    page: int = 1,
    page_size: int = 20,
    repository: ProjectRepository = Depends(get_project_repository),
) -> APIEnvelope:
    query = ProjectListQuery(
        q=q,
        status=project_status,
        page=page,
        page_size=page_size,
    )
    projects, total = repository.list_projects(query.model_dump())
    return envelope(
        [record_to_dict(project) for project in projects],
        meta={"page": query.page, "page_size": query.page_size, "total": total},
    )


@router.get("/projects/{project_id}", response_model=APIEnvelope)
def get_project(
    project_id: int,
    repository: ProjectRepository = Depends(get_project_repository),
) -> APIEnvelope:
    try:
        return envelope(record_to_dict(repository.get_project(project_id)))
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.patch("/projects/{project_id}", response_model=APIEnvelope)
def update_project(
    project_id: int,
    request: ProjectUpdateRequest,
    repository: ProjectRepository = Depends(get_project_repository),
) -> APIEnvelope:
    try:
        return envelope(
            record_to_dict(
                repository.update_project(
                    project_id,
                    request.model_dump(exclude_unset=True),
                )
            )
        )
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.post("/projects/{project_id}/papers:link", response_model=APIEnvelope)
def link_project_paper(
    project_id: int,
    request: ProjectPaperLinkRequest,
    repository: ProjectRepository = Depends(get_project_repository),
) -> APIEnvelope:
    try:
        papers = repository.link_paper(
            project_id=project_id,
            paper_id=request.paper_id,
            relation_type=request.relation_type,
        )
        return envelope(records_to_dicts(papers))
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.delete("/projects/{project_id}/papers/{paper_id}", response_model=APIEnvelope)
def unlink_project_paper(
    project_id: int,
    paper_id: int,
    repository: ProjectRepository = Depends(get_project_repository),
) -> APIEnvelope:
    try:
        repository.unlink_paper(project_id, paper_id)
        return envelope({"project_id": project_id, "paper_id": paper_id})
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.get("/projects/{project_id}/papers", response_model=APIEnvelope)
def list_project_papers(
    project_id: int,
    repository: ProjectRepository = Depends(get_project_repository),
) -> APIEnvelope:
    try:
        return envelope(records_to_dicts(repository.list_linked_papers(project_id)))
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.get("/projects/{project_id}/documents/{doc_role}", response_model=APIEnvelope)
def get_project_document(
    project_id: int,
    doc_role: ProjectDocumentRole,
    repository: ProjectRepository = Depends(get_project_repository),
) -> APIEnvelope:
    try:
        return envelope(document_to_dict(repository.get_document(project_id, doc_role)))
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.put("/projects/{project_id}/documents/{doc_role}", response_model=APIEnvelope)
def update_project_document(
    project_id: int,
    doc_role: ProjectDocumentRole,
    request: ProjectDocumentUpdateRequest,
    repository: ProjectRepository = Depends(get_project_repository),
) -> APIEnvelope:
    try:
        document = repository.update_document(
            project_id=project_id,
            doc_role=doc_role,
            content=request.content,
            base_version=request.base_version,
        )
        return envelope(document_to_dict(document))
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise
