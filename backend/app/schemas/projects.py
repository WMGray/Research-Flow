"""Project API 的请求与响应 Schema。

这里只描述 HTTP 层契约，不承载 Project 业务逻辑。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


ProjectStatus = Literal["active", "paused", "archived"]
ProjectDocumentRole = Literal[
    "overview",
    "related-work",
    "method",
    "experiment",
    "conclusion",
    "manuscript",
]


class ProjectCreateRequest(BaseModel):
    """创建 Project 的请求体。"""

    name: str = Field(min_length=1)
    summary: str = ""
    owner: str = ""
    status: ProjectStatus = "active"


class ProjectUpdateRequest(BaseModel):
    """更新 Project 基础字段的请求体。"""

    name: str | None = Field(default=None, min_length=1)
    summary: str | None = None
    owner: str | None = None
    status: ProjectStatus | None = None

    @model_validator(mode="after")
    def validate_has_update(self) -> "ProjectUpdateRequest":
        """确保 PATCH 请求至少携带一个有效更新字段。"""

        if not self.model_dump(exclude_unset=True):
            raise ValueError("At least one field must be provided.")
        return self


class ProjectListQuery(BaseModel):
    """Project 列表查询参数。"""

    q: str = ""
    status: ProjectStatus | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class ProjectResponse(BaseModel):
    """Project 详情响应结构。"""

    project_id: int
    asset_id: int
    name: str
    project_slug: str
    status: ProjectStatus
    summary: str
    owner: str
    assets: dict[str, int] = Field(default_factory=dict)
    created_at: str
    updated_at: str


class ProjectDocumentResponse(BaseModel):
    """Project 模块文档响应结构。"""

    project_id: int
    doc_id: int
    doc_role: ProjectDocumentRole
    content: str
    version: int
    updated_at: str


class ProjectDocumentUpdateRequest(BaseModel):
    """更新 Project 模块文档的请求体。"""

    content: str
    base_version: int | None = None


class LinkedPaperResponse(BaseModel):
    """Project 已关联 Paper 的响应结构。"""

    paper_id: int
    title: str
    status: str
    relation_type: str
