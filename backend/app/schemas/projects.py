"""Project API request/response schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


ProjectStatus = Literal[
    "planning",
    "researching",
    "experimenting",
    "writing",
    "archived",
]
ProjectDocumentRole = Literal[
    "overview",
    "related_work",
    "method",
    "experiment",
    "conclusion",
    "manuscript",
]
ProjectPaperRelationType = Literal[
    "related_work",
    "baseline",
    "inspiration",
    "method_reference",
    "experiment_reference",
]


class ProjectCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    summary: str = ""
    owner: str = ""
    status: ProjectStatus = "planning"


class ProjectUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1)
    summary: str | None = None
    owner: str | None = None
    status: ProjectStatus | None = None

    @model_validator(mode="after")
    def validate_has_update(self) -> "ProjectUpdateRequest":
        if not self.model_dump(exclude_unset=True):
            raise ValueError("At least one field must be provided.")
        return self


class ProjectListQuery(BaseModel):
    q: str = ""
    status: ProjectStatus | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class ProjectResponse(BaseModel):
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
    project_id: int
    doc_id: int
    doc_role: ProjectDocumentRole
    content: str
    version: int
    updated_at: str


class ProjectDocumentUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str
    base_version: int | None = None


class ProjectPaperLinkRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paper_id: int
    relation_type: ProjectPaperRelationType = "related_work"


class ProjectTaskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    focus_instructions: str = ""
    included_paper_ids: list[int] = Field(default_factory=list)
    included_knowledge_ids: list[int] = Field(default_factory=list)
    skip_locked_blocks: bool = True


class LinkedPaperResponse(BaseModel):
    paper_id: int
    title: str
    status: str
    relation_type: ProjectPaperRelationType
