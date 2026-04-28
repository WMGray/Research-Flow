"""LLM-backed Project task block generation."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import json
from typing import Any, Protocol
from uuid import uuid4

from core.services.llm import LLMMessage, LLMRequest, LLMResponse, llm_registry
from core.services.papers.refine.parsing import extract_json_object
from core.services.projects.jobs import ProjectJobRecord
from core.services.projects.models import LinkedPaperRecord, ProjectRecord
from core.services.projects.tasks.models import ProjectTaskInput


class LLMGenerateClient(Protocol):
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate content for a configured LLM feature."""


@dataclass(frozen=True, slots=True)
class ProjectLLMBlockResult:
    blocks: dict[str, str]
    llm_run_id: str


def project_llm_available(feature: str | None, llm_client: LLMGenerateClient) -> bool:
    if feature is None:
        return False
    if llm_client is not llm_registry:
        return True
    try:
        feature_config = llm_registry.list_features().get(feature)
        if feature_config is None:
            return False
        model_config = llm_registry.list_models(enabled_only=True).get(
            feature_config.model_key
        )
        if model_config is None:
            return False
        platform = llm_registry.list_platforms().get(model_config.platform)
        return platform is not None and bool(platform.resolve_api_key())
    except Exception:  # noqa: BLE001 - config lookup failure means fallback locally
        return False


async def generate_project_task_blocks(
    *,
    feature: str,
    project: ProjectRecord,
    linked_papers: list[LinkedPaperRecord],
    documents: dict[str, str],
    recent_jobs: list[ProjectJobRecord],
    task_input: ProjectTaskInput,
    block_specs: tuple[tuple[str, str], ...],
    llm_client: LLMGenerateClient,
) -> ProjectLLMBlockResult:
    prompt = _render_project_prompt(
        project=project,
        linked_papers=linked_papers,
        documents=documents,
        recent_jobs=recent_jobs,
        task_input=task_input,
        block_specs=block_specs,
    )
    response = await llm_client.generate(
        LLMRequest(
            feature=feature,
            messages=[LLMMessage(role="user", content=prompt)],
            max_tokens=6000,
            max_completion_tokens=6000,
            extra={"response_format": {"type": "json_object"}},
        )
    )
    payload = extract_json_object(response.message.content)
    blocks_payload = payload.get("blocks", payload)
    if not isinstance(blocks_payload, dict):
        raise ValueError("Project task LLM response must contain a blocks object.")

    blocks: dict[str, str] = {}
    for block_id, _ in block_specs:
        content = _markdown_text(blocks_payload.get(block_id))
        if content:
            blocks[block_id] = content
    if not blocks:
        raise ValueError("Project task LLM response did not contain usable blocks.")
    return ProjectLLMBlockResult(blocks=blocks, llm_run_id=f"llm_{uuid4().hex}")


def _render_project_prompt(
    *,
    project: ProjectRecord,
    linked_papers: list[LinkedPaperRecord],
    documents: dict[str, str],
    recent_jobs: list[ProjectJobRecord],
    task_input: ProjectTaskInput,
    block_specs: tuple[tuple[str, str], ...],
) -> str:
    schema = {
        "blocks": {
            block_id: f"Markdown content for {title}."
            for block_id, title in block_specs
        }
    }
    return "\n\n".join(
        [
            "# Project Task",
            "Return only valid JSON matching this shape:",
            json.dumps(schema, ensure_ascii=False, indent=2),
            "# Rules",
            "- Use Markdown inside each block value.",
            "- Use only the supplied project context; mark missing evidence explicitly.",
            "- Preserve method names, datasets, metrics, paper titles, and citations.",
            "- Do not wrap output in Markdown fences.",
            "# Project Metadata",
            _project_metadata(project),
            "# Focus Instructions",
            task_input.focus_instructions.strip() or "No extra focus instructions.",
            "# Linked Papers",
            _linked_paper_context(linked_papers),
            "# Existing Project Modules",
            _document_context(documents),
            "# Recent Project Jobs",
            _recent_job_context(recent_jobs),
        ]
    )


def _project_metadata(project: ProjectRecord) -> str:
    return "\n".join(
        [
            f"- project_id: {project.project_id}",
            f"- name: {project.name}",
            f"- status: {project.status}",
            f"- owner: {project.owner or 'Unassigned'}",
            f"- summary: {project.summary or 'No summary provided.'}",
        ]
    )


def _linked_paper_context(linked_papers: list[LinkedPaperRecord]) -> str:
    if not linked_papers:
        return "No linked papers."
    return "\n".join(
        f"- paper_id={paper.paper_id}; relation={paper.relation_type}; "
        f"status={paper.status}; title={paper.title}"
        for paper in linked_papers
    )


def _document_context(documents: dict[str, str]) -> str:
    if not documents:
        return "No project module documents."
    chunks = []
    for role in sorted(documents):
        chunks.append(f"## {role}\n{_excerpt(documents[role], limit=1200)}")
    return "\n\n".join(chunks)


def _recent_job_context(recent_jobs: list[ProjectJobRecord]) -> str:
    if not recent_jobs:
        return "No recent project jobs."
    return "\n".join(
        f"- {job.type}: {job.status}; {job.message}"
        for job in recent_jobs[:5]
    )


def _markdown_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return "\n".join(
            f"- {item_text}"
            for item in value
            if (item_text := _inline_text(item))
        )
    if isinstance(value, dict):
        return "\n".join(
            f"- {str(key).replace('_', ' ').title()}: {item_text}"
            for key, item in value.items()
            if (item_text := _inline_text(item))
        )
    return str(value).strip()


def _inline_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        return "; ".join(
            f"{str(key).replace('_', ' ')}: {item_text}"
            for key, item in value.items()
            if (item_text := _inline_text(item))
        )
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        return "; ".join(
            item_text
            for item in value
            if (item_text := _inline_text(item))
        )
    return str(value).strip()


def _excerpt(content: str, *, limit: int) -> str:
    compact = " ".join(content.split())
    if not compact:
        return "No content yet."
    if len(compact) <= limit:
        return compact
    return compact[:limit].rstrip() + " ... [truncated]"


__all__ = [
    "LLMGenerateClient",
    "ProjectLLMBlockResult",
    "generate_project_task_blocks",
    "project_llm_available",
]
