"""Project P0 的 FastAPI 路由层。

本文件只负责 HTTP 请求/响应、依赖注入和异常到 HTTP 状态码的转换；
具体 Project 业务逻辑由 core.services.projects 承担。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.papers import envelope
from app.schemas.papers import APIEnvelope
from app.schemas.projects import (
    ProjectCreateRequest,
    ProjectDocumentRole,
    ProjectDocumentUpdateRequest,
    ProjectListQuery,
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
    """创建 ProjectRepository 依赖实例。"""

    return ProjectRepository()


def raise_http_error(exc: Exception) -> None:
    """将 core 层异常转换为稳定的 HTTP 错误响应。"""

    if isinstance(exc, ProjectDocumentVersionConflictError):
        raise HTTPException(
            status_code=409, detail={"code": exc.code, "message": str(exc)}
        )
    if isinstance(
        exc,
        (ProjectNotFoundError, ProjectDocumentNotFoundError, LinkedPaperNotFoundError),
    ):
        raise HTTPException(
            status_code=404, detail={"code": exc.code, "message": str(exc)}
        )
    raise exc


@router.post("/projects", status_code=status.HTTP_201_CREATED, response_model=APIEnvelope)
def create_project(
    request: ProjectCreateRequest,
    repository: ProjectRepository = Depends(get_project_repository),
) -> APIEnvelope:
    """创建 Project，并自动初始化六个模块文档。"""

    return envelope(record_to_dict(repository.create_project(request.model_dump())))


@router.get("/projects", response_model=APIEnvelope)
def list_projects(
    q: str = "",
    project_status: ProjectStatus | None = Query(default=None, alias="status"),
    page: int = 1,
    page_size: int = 20,
    repository: ProjectRepository = Depends(get_project_repository),
) -> APIEnvelope:
    """分页查询 Project 列表。"""

    query = ProjectListQuery(
        q=q,
        status=project_status,
        page=page,
        page_size=page_size,
    )
    projects, total = repository.list_projects(query.model_dump())
    # meta 保存分页信息，data 只保存业务记录列表。
    return envelope(
        [record_to_dict(project) for project in projects],
        meta={"page": query.page, "page_size": query.page_size, "total": total},
    )


@router.get("/projects/{project_id}", response_model=APIEnvelope)
def get_project(
    project_id: int,
    repository: ProjectRepository = Depends(get_project_repository),
) -> APIEnvelope:
    """查询单个 Project 详情。"""

    try:
        return envelope(record_to_dict(repository.get_project(project_id)))
    except Exception as exc:
        raise_http_error(exc)
        raise


@router.patch("/projects/{project_id}", response_model=APIEnvelope)
def update_project(
    project_id: int,
    request: ProjectUpdateRequest,
    repository: ProjectRepository = Depends(get_project_repository),
) -> APIEnvelope:
    """更新 Project 的基础元数据和状态。"""

    try:
        return envelope(
            record_to_dict(
                repository.update_project(
                    project_id,
                    request.model_dump(exclude_unset=True),
                )
            )
        )
    except Exception as exc:
        raise_http_error(exc)
        raise


@router.post("/projects/{project_id}/papers/{paper_id}", response_model=APIEnvelope)
def link_project_paper(
    project_id: int,
    paper_id: int,
    repository: ProjectRepository = Depends(get_project_repository),
) -> APIEnvelope:
    """将已有 Paper 关联到 Project。"""

    try:
        papers = repository.link_paper(project_id, paper_id)
        return envelope(records_to_dicts(papers))
    except Exception as exc:
        raise_http_error(exc)
        raise


@router.get("/projects/{project_id}/papers", response_model=APIEnvelope)
def list_project_papers(
    project_id: int,
    repository: ProjectRepository = Depends(get_project_repository),
) -> APIEnvelope:
    """查询 Project 已关联的 Paper 列表。"""

    try:
        return envelope(records_to_dicts(repository.list_linked_papers(project_id)))
    except Exception as exc:
        raise_http_error(exc)
        raise


@router.get("/projects/{project_id}/documents/{doc_role}", response_model=APIEnvelope)
def get_project_document(
    project_id: int,
    doc_role: ProjectDocumentRole,
    repository: ProjectRepository = Depends(get_project_repository),
) -> APIEnvelope:
    """读取 Project 指定模块文档。"""

    try:
        return envelope(document_to_dict(repository.get_document(project_id, doc_role)))
    except Exception as exc:
        raise_http_error(exc)
        raise


@router.put("/projects/{project_id}/documents/{doc_role}", response_model=APIEnvelope)
def update_project_document(
    project_id: int,
    doc_role: ProjectDocumentRole,
    request: ProjectDocumentUpdateRequest,
    repository: ProjectRepository = Depends(get_project_repository),
) -> APIEnvelope:
    """更新 Project 指定模块文档，并校验 base_version。"""

    try:
        document = repository.update_document(
            project_id=project_id,
            doc_role=doc_role,
            content=request.content,
            base_version=request.base_version,
        )
        return envelope(document_to_dict(document))
    except Exception as exc:
        raise_http_error(exc)
        raise
