"""Project API routes."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.api.papers import envelope
from app.api.resources import resource_link_payload
from app.schemas.papers import APIEnvelope, JobResponse
from app.schemas.projects import (
    ProjectCreateRequest,
    ProjectDocumentRole,
    ProjectDocumentUpdateRequest,
    ProjectListQuery,
    ProjectPaperLinkRequest,
    ProjectStatus,
    ProjectTaskRequest,
    ProjectUpdateRequest,
)
from app.schemas.resources import (
    ProjectDatasetLinkRequest,
    ProjectKnowledgeLinkRequest,
    ProjectPresentationLinkRequest,
)
from core.services.projects import (
    LinkedPaperNotFoundError,
    ProjectDocumentNotFoundError,
    ProjectDocumentVersionConflictError,
    ProjectNotFoundError,
    ProjectRepository,
    ProjectTaskInput,
    ProjectTaskService,
    document_to_dict,
    record_to_dict,
    records_to_dicts,
)
from core.services.resources import ResourceNotFoundError, ResourceRepository


router = APIRouter(prefix="/api/v1", tags=["projects"])


def get_project_repository() -> ProjectRepository:
    return ProjectRepository()


def get_project_task_service() -> ProjectTaskService:
    return ProjectTaskService()


def get_resource_repository() -> ResourceRepository:
    return ResourceRepository()


def to_task_input(request: ProjectTaskRequest | None) -> ProjectTaskInput:
    payload = request or ProjectTaskRequest()
    return ProjectTaskInput(
        focus_instructions=payload.focus_instructions,
        included_paper_ids=tuple(payload.included_paper_ids),
        included_knowledge_ids=tuple(payload.included_knowledge_ids),
        included_dataset_ids=tuple(payload.included_dataset_ids),
        skip_locked_blocks=payload.skip_locked_blocks,
    )


def to_job_response(record: object) -> JobResponse:
    return JobResponse.model_validate(asdict(record))


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
    if isinstance(exc, ResourceNotFoundError):
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


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    repository: ProjectRepository = Depends(get_project_repository),
) -> Response:
    try:
        repository.delete_project(project_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
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


@router.post("/projects/{project_id}/knowledge:link", response_model=APIEnvelope)
def link_project_knowledge(
    project_id: int,
    request: ProjectKnowledgeLinkRequest,
    repository: ResourceRepository = Depends(get_resource_repository),
) -> APIEnvelope:
    try:
        records = repository.link_asset(
            source_id=project_id,
            target_id=request.knowledge_id,
            target_type="Knowledge",
            relation_type=request.relation_type,
        )
        return envelope(resource_link_payload(records))
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.get("/projects/{project_id}/knowledge", response_model=APIEnvelope)
def list_project_knowledge(
    project_id: int,
    repository: ResourceRepository = Depends(get_resource_repository),
) -> APIEnvelope:
    try:
        return envelope(
            resource_link_payload(
                repository.list_links(source_id=project_id, target_type="Knowledge")
            )
        )
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.delete("/projects/{project_id}/knowledge/{knowledge_id}", response_model=APIEnvelope)
def unlink_project_knowledge(
    project_id: int,
    knowledge_id: int,
    repository: ResourceRepository = Depends(get_resource_repository),
) -> APIEnvelope:
    try:
        repository.unlink_asset(
            source_id=project_id,
            target_id=knowledge_id,
            target_type="Knowledge",
        )
        return envelope({"project_id": project_id, "knowledge_id": knowledge_id})
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.post("/projects/{project_id}/datasets:link", response_model=APIEnvelope)
def link_project_dataset(
    project_id: int,
    request: ProjectDatasetLinkRequest,
    repository: ResourceRepository = Depends(get_resource_repository),
) -> APIEnvelope:
    try:
        records = repository.link_asset(
            source_id=project_id,
            target_id=request.dataset_id,
            target_type="Dataset",
            relation_type=request.relation_type,
        )
        return envelope(resource_link_payload(records))
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.get("/projects/{project_id}/datasets", response_model=APIEnvelope)
def list_project_datasets(
    project_id: int,
    repository: ResourceRepository = Depends(get_resource_repository),
) -> APIEnvelope:
    try:
        return envelope(
            resource_link_payload(
                repository.list_links(source_id=project_id, target_type="Dataset")
            )
        )
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.delete("/projects/{project_id}/datasets/{dataset_id}", response_model=APIEnvelope)
def unlink_project_dataset(
    project_id: int,
    dataset_id: int,
    repository: ResourceRepository = Depends(get_resource_repository),
) -> APIEnvelope:
    try:
        repository.unlink_asset(
            source_id=project_id,
            target_id=dataset_id,
            target_type="Dataset",
        )
        return envelope({"project_id": project_id, "dataset_id": dataset_id})
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.post("/projects/{project_id}/presentations:link", response_model=APIEnvelope)
def link_project_presentation(
    project_id: int,
    request: ProjectPresentationLinkRequest,
    repository: ResourceRepository = Depends(get_resource_repository),
) -> APIEnvelope:
    try:
        records = repository.link_asset(
            source_id=project_id,
            target_id=request.presentation_id,
            target_type="Presentation",
            relation_type=request.relation_type,
        )
        return envelope(resource_link_payload(records))
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.get("/projects/{project_id}/presentations", response_model=APIEnvelope)
def list_project_presentations(
    project_id: int,
    repository: ResourceRepository = Depends(get_resource_repository),
) -> APIEnvelope:
    try:
        return envelope(
            resource_link_payload(
                repository.list_links(source_id=project_id, target_type="Presentation")
            )
        )
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.delete(
    "/projects/{project_id}/presentations/{presentation_id}",
    response_model=APIEnvelope,
)
def unlink_project_presentation(
    project_id: int,
    presentation_id: int,
    repository: ResourceRepository = Depends(get_resource_repository),
) -> APIEnvelope:
    try:
        repository.unlink_asset(
            source_id=project_id,
            target_id=presentation_id,
            target_type="Presentation",
        )
        return envelope({"project_id": project_id, "presentation_id": presentation_id})
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.post(
    "/projects/{project_id}/refresh-overview",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=APIEnvelope,
)
def refresh_project_overview(
    project_id: int,
    request: ProjectTaskRequest | None = None,
    service: ProjectTaskService = Depends(get_project_task_service),
) -> APIEnvelope:
    try:
        return envelope(
            to_job_response(service.run_refresh_overview(project_id, to_task_input(request)))
        )
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.post(
    "/projects/{project_id}/generate-related-work",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=APIEnvelope,
)
def generate_project_related_work(
    project_id: int,
    request: ProjectTaskRequest | None = None,
    service: ProjectTaskService = Depends(get_project_task_service),
) -> APIEnvelope:
    try:
        return envelope(
            to_job_response(
                service.run_generate_related_work(project_id, to_task_input(request))
            )
        )
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.post(
    "/projects/{project_id}/generate-method",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=APIEnvelope,
)
def generate_project_method(
    project_id: int,
    request: ProjectTaskRequest | None = None,
    service: ProjectTaskService = Depends(get_project_task_service),
) -> APIEnvelope:
    try:
        return envelope(
            to_job_response(service.run_generate_method(project_id, to_task_input(request)))
        )
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.post(
    "/projects/{project_id}/generate-experiment",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=APIEnvelope,
)
def generate_project_experiment(
    project_id: int,
    request: ProjectTaskRequest | None = None,
    service: ProjectTaskService = Depends(get_project_task_service),
) -> APIEnvelope:
    try:
        return envelope(
            to_job_response(
                service.run_generate_experiment(project_id, to_task_input(request))
            )
        )
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.post(
    "/projects/{project_id}/generate-conclusion",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=APIEnvelope,
)
def generate_project_conclusion(
    project_id: int,
    request: ProjectTaskRequest | None = None,
    service: ProjectTaskService = Depends(get_project_task_service),
) -> APIEnvelope:
    try:
        return envelope(
            to_job_response(
                service.run_generate_conclusion(project_id, to_task_input(request))
            )
        )
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.post(
    "/projects/{project_id}/generate-manuscript",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=APIEnvelope,
)
def generate_project_manuscript(
    project_id: int,
    request: ProjectTaskRequest | None = None,
    service: ProjectTaskService = Depends(get_project_task_service),
) -> APIEnvelope:
    try:
        return envelope(
            to_job_response(
                service.run_generate_manuscript(project_id, to_task_input(request))
            )
        )
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
