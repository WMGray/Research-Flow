"""DTOs and errors for shared Research-Flow resources."""

from __future__ import annotations

from dataclasses import dataclass


class ResourceRepositoryError(RuntimeError):
    code = "RESOURCE_REPOSITORY_ERROR"


class ResourceNotFoundError(ResourceRepositoryError):
    code = "RESOURCE_NOT_FOUND"


class ResourceVersionConflictError(ResourceRepositoryError):
    code = "RESOURCE_VERSION_CONFLICT"


@dataclass(frozen=True, slots=True)
class DatasetRecord:
    dataset_id: int
    asset_id: int
    name: str
    normalized_name: str
    aliases: list[str]
    task_type: str
    data_domain: str
    scale: str
    source: str
    description: str
    access_url: str
    benchmark_summary: str
    created_at: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class KnowledgeRecord:
    knowledge_id: int
    asset_id: int
    knowledge_type: str
    title: str
    summary_zh: str
    original_text_en: str
    citation_marker: str
    category_label: str
    research_field: str
    source_paper_asset_id: int | None
    source_section: str
    source_locator: str
    evidence_text: str
    confidence_score: float
    review_status: str
    llm_run_id: str
    created_at: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class PresentationRecord:
    presentation_id: int
    asset_id: int
    project_asset_id: int | None
    title: str
    scene_type: str
    status: str
    export_format: str
    assets: dict[str, int]
    created_at: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class PresentationDocumentRecord:
    presentation_id: int
    doc_id: int
    doc_role: str
    content: str
    version: int
    updated_at: str


@dataclass(frozen=True, slots=True)
class ResourceLinkRecord:
    resource_id: int
    asset_id: int
    resource_type: str
    display_name: str
    relation_type: str
    created_at: str
    updated_at: str
