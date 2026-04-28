"""API schemas for Dataset, Knowledge, and Presentation resources."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


PresentationSceneType = Literal["group_meeting", "proposal", "defense"]
PresentationStatus = Literal["draft", "generating", "ready", "exported", "archived"]
PresentationDocumentRole = Literal["outline", "slides", "speaker_notes"]
KnowledgeType = Literal["view", "definition"]
KnowledgeReviewStatus = Literal["pending_review", "accepted", "rejected"]


class DatasetCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    normalized_name: str = ""
    aliases: list[str] = Field(default_factory=list)
    task_type: str = ""
    data_domain: str = ""
    scale: str = ""
    source: str = ""
    description: str = ""
    access_url: str = ""
    benchmark_summary: str = ""


class DatasetUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1)
    normalized_name: str | None = None
    aliases: list[str] | None = None
    task_type: str | None = None
    data_domain: str | None = None
    scale: str | None = None
    source: str | None = None
    description: str | None = None
    access_url: str | None = None
    benchmark_summary: str | None = None

    @model_validator(mode="after")
    def validate_has_update(self) -> "DatasetUpdateRequest":
        if not self.model_dump(exclude_unset=True):
            raise ValueError("At least one field must be provided.")
        return self


class DatasetResponse(DatasetCreateRequest):
    dataset_id: int
    asset_id: int
    created_at: str
    updated_at: str


class KnowledgeCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    knowledge_type: KnowledgeType = "view"
    title: str = Field(min_length=1)
    summary_zh: str = ""
    original_text_en: str = ""
    citation_marker: str = ""
    category_label: str = ""
    research_field: str = ""
    source_paper_asset_id: int | None = None
    source_section: str = ""
    source_locator: str = ""
    evidence_text: str = ""
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    review_status: KnowledgeReviewStatus = "pending_review"
    llm_run_id: str = ""


class KnowledgeUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    knowledge_type: KnowledgeType | None = None
    title: str | None = Field(default=None, min_length=1)
    summary_zh: str | None = None
    original_text_en: str | None = None
    citation_marker: str | None = None
    category_label: str | None = None
    research_field: str | None = None
    source_paper_asset_id: int | None = None
    source_section: str | None = None
    source_locator: str | None = None
    evidence_text: str | None = None
    confidence_score: float | None = Field(default=None, ge=0.0, le=1.0)
    review_status: KnowledgeReviewStatus | None = None
    llm_run_id: str | None = None

    @model_validator(mode="after")
    def validate_has_update(self) -> "KnowledgeUpdateRequest":
        if not self.model_dump(exclude_unset=True):
            raise ValueError("At least one field must be provided.")
        return self


class KnowledgeResponse(KnowledgeCreateRequest):
    knowledge_id: int
    asset_id: int
    created_at: str
    updated_at: str


class PresentationCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    project_asset_id: int | None = None
    scene_type: PresentationSceneType = "group_meeting"
    status: PresentationStatus = "draft"
    export_format: str = ""


class PresentationUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1)
    project_asset_id: int | None = None
    scene_type: PresentationSceneType | None = None
    status: PresentationStatus | None = None
    export_format: str | None = None

    @model_validator(mode="after")
    def validate_has_update(self) -> "PresentationUpdateRequest":
        if not self.model_dump(exclude_unset=True):
            raise ValueError("At least one field must be provided.")
        return self


class PresentationResponse(BaseModel):
    presentation_id: int
    asset_id: int
    project_asset_id: int | None = None
    title: str
    scene_type: PresentationSceneType
    status: PresentationStatus
    export_format: str = ""
    assets: dict[str, int] = Field(default_factory=dict)
    created_at: str
    updated_at: str


class PresentationDocumentResponse(BaseModel):
    presentation_id: int
    doc_id: int
    doc_role: PresentationDocumentRole
    content: str
    version: int
    updated_at: str


class PresentationDocumentUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str
    base_version: int | None = None


class ResourceLinkRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resource_id: int
    relation_type: str = Field(default="USES", min_length=1)


class ProjectKnowledgeLinkRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    knowledge_id: int
    relation_type: str = Field(default="USES_KNOWLEDGE", min_length=1)


class ProjectDatasetLinkRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_id: int
    relation_type: str = Field(default="USES_DATASET", min_length=1)


class ProjectPresentationLinkRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    presentation_id: int
    relation_type: str = Field(default="HAS_PRESENTATION", min_length=1)


class ResourceLinkResponse(BaseModel):
    resource_id: int
    asset_id: int
    resource_type: Literal["Dataset", "Knowledge", "Presentation"]
    display_name: str
    relation_type: str
    created_at: str
    updated_at: str
