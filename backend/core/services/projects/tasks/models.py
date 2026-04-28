"""DTOs for project task execution."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ProjectTaskInput:
    focus_instructions: str = ""
    included_paper_ids: tuple[int, ...] = field(default_factory=tuple)
    included_knowledge_ids: tuple[int, ...] = field(default_factory=tuple)
    included_dataset_ids: tuple[int, ...] = field(default_factory=tuple)
    skip_locked_blocks: bool = True


@dataclass(frozen=True, slots=True)
class ProjectTaskResult:
    job_type: str
    doc_role: str
    content: str
    block_ids: tuple[str, ...]
    message: str
    result: dict[str, object]
