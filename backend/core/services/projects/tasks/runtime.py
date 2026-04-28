"""Deterministic project task rendering.

The runtime writes useful local Markdown blocks first. LLM-backed generation can
replace these renderers later without changing the API or merge semantics.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from core.services.documents import render_managed_block
from core.services.projects.jobs import ProjectJobRecord
from core.services.projects.models import LinkedPaperRecord, ProjectRecord
from core.services.projects.tasks.models import ProjectTaskInput, ProjectTaskResult


@dataclass(frozen=True, slots=True)
class ProjectTaskSpec:
    job_type: str
    doc_role: str
    message: str
    blocks: tuple[tuple[str, str], ...]


PROJECT_TASK_SPECS: dict[str, ProjectTaskSpec] = {
    "project_refresh_overview": ProjectTaskSpec(
        job_type="project_refresh_overview",
        doc_role="overview",
        message="Refreshed project overview statistics.",
        blocks=(("overview_stats", "Overview Statistics"),),
    ),
    "project_generate_related_work": ProjectTaskSpec(
        job_type="project_generate_related_work",
        doc_role="related_work",
        message="Generated related work synthesis.",
        blocks=(
            ("related_work_summary", "Related Work Summary"),
            ("paper_grouping", "Paper Grouping"),
            ("method_comparison", "Method Comparison"),
        ),
    ),
    "project_generate_method": ProjectTaskSpec(
        job_type="project_generate_method",
        doc_role="method",
        message="Generated method draft.",
        blocks=(
            ("method_draft", "Method Draft"),
            ("innovation_points", "Innovation Points"),
            ("design_risks", "Design Risks"),
        ),
    ),
    "project_generate_experiment": ProjectTaskSpec(
        job_type="project_generate_experiment",
        doc_role="experiment",
        message="Generated experiment plan.",
        blocks=(
            ("experiment_plan", "Experiment Plan"),
            ("baseline_comparison", "Baseline Comparison"),
            ("metric_suggestions", "Metric Suggestions"),
        ),
    ),
    "project_generate_conclusion": ProjectTaskSpec(
        job_type="project_generate_conclusion",
        doc_role="conclusion",
        message="Generated project conclusion summary.",
        blocks=(
            ("conclusion_summary", "Conclusion Summary"),
            ("open_problems", "Open Problems"),
            ("next_steps", "Next Steps"),
        ),
    ),
    "project_generate_manuscript": ProjectTaskSpec(
        job_type="project_generate_manuscript",
        doc_role="manuscript",
        message="Compiled manuscript draft.",
        blocks=(
            ("manuscript_abstract", "Abstract"),
            ("manuscript_introduction", "Introduction"),
            ("manuscript_related_work", "Related Work"),
            ("manuscript_method", "Method"),
            ("manuscript_experiment", "Experiment"),
            ("manuscript_conclusion", "Conclusion"),
        ),
    ),
}


def render_project_task(
    *,
    task_type: str,
    project: ProjectRecord,
    linked_papers: list[LinkedPaperRecord],
    documents: dict[str, str],
    recent_jobs: list[ProjectJobRecord],
    task_input: ProjectTaskInput,
) -> ProjectTaskResult:
    spec = PROJECT_TASK_SPECS[task_type]
    renderer = _BLOCK_RENDERERS.get(task_type, _render_generic_blocks)
    block_content = renderer(project, linked_papers, documents, recent_jobs, task_input)
    rendered_blocks = [
        render_managed_block(
            block_id=block_id,
            title=title,
            content=block_content.get(block_id, ""),
        )
        for block_id, title in spec.blocks
    ]
    return ProjectTaskResult(
        job_type=spec.job_type,
        doc_role=spec.doc_role,
        content="\n\n".join(rendered_blocks) + "\n",
        block_ids=tuple(block_id for block_id, _ in spec.blocks),
        message=spec.message,
        result={
            "doc_role": spec.doc_role,
            "managed_blocks": [block_id for block_id, _ in spec.blocks],
            "linked_paper_count": len(linked_papers),
            "focus_instructions": task_input.focus_instructions,
        },
    )


BlockRenderer = Callable[
    [ProjectRecord, list[LinkedPaperRecord], dict[str, str], list[ProjectJobRecord], ProjectTaskInput],
    dict[str, str],
]


def _render_overview_blocks(
    project: ProjectRecord,
    linked_papers: list[LinkedPaperRecord],
    documents: dict[str, str],
    recent_jobs: list[ProjectJobRecord],
    task_input: ProjectTaskInput,
) -> dict[str, str]:
    rows = [
        ("Project", project.name),
        ("Status", project.status),
        ("Owner", project.owner or "Unassigned"),
        ("Linked papers", str(len(linked_papers))),
        ("Recent project jobs", str(len(recent_jobs))),
    ]
    if task_input.focus_instructions:
        rows.append(("Focus", task_input.focus_instructions))
    table = ["| Item | Value |", "|---|---|"]
    table.extend(f"| {left} | {right} |" for left, right in rows)
    return {"overview_stats": "\n".join(table)}


def _render_related_work_blocks(
    project: ProjectRecord,
    linked_papers: list[LinkedPaperRecord],
    documents: dict[str, str],
    recent_jobs: list[ProjectJobRecord],
    task_input: ProjectTaskInput,
) -> dict[str, str]:
    paper_lines = _paper_lines(linked_papers)
    return {
        "related_work_summary": (
            f"{project.name} currently links {len(linked_papers)} papers for synthesis.\n\n"
            + paper_lines
            + _focus_suffix(task_input)
        ),
        "paper_grouping": _group_papers_by_relation(linked_papers),
        "method_comparison": (
            "Use the linked papers as candidates for method comparison. "
            "Promote baseline and method_reference papers before broader related_work items."
        ),
    }


def _render_method_blocks(
    project: ProjectRecord,
    linked_papers: list[LinkedPaperRecord],
    documents: dict[str, str],
    recent_jobs: list[ProjectJobRecord],
    task_input: ProjectTaskInput,
) -> dict[str, str]:
    related_excerpt = _excerpt(documents.get("related_work", ""))
    return {
        "method_draft": (
            f"Draft the method for {project.name} from the confirmed research scope.\n\n"
            f"Related-work context: {related_excerpt}"
            + _focus_suffix(task_input)
        ),
        "innovation_points": (
            "- Identify the core limitation shared by baseline papers.\n"
            "- State the proposed mechanism and expected advantage.\n"
            "- Keep each claimed contribution traceable to project evidence."
        ),
        "design_risks": (
            "- Insufficient evidence from linked papers.\n"
            "- Missing baseline coverage.\n"
            "- Method scope drifting beyond the project summary."
        ),
    }


def _render_experiment_blocks(
    project: ProjectRecord,
    linked_papers: list[LinkedPaperRecord],
    documents: dict[str, str],
    recent_jobs: list[ProjectJobRecord],
    task_input: ProjectTaskInput,
) -> dict[str, str]:
    baseline_count = sum(1 for paper in linked_papers if paper.relation_type == "baseline")
    return {
        "experiment_plan": (
            f"Plan experiments for {project.name} around the current method draft.\n\n"
            f"Baseline candidates: {baseline_count}."
            + _focus_suffix(task_input)
        ),
        "baseline_comparison": _group_papers_by_relation(linked_papers),
        "metric_suggestions": (
            "- Reuse metrics reported by baseline papers when available.\n"
            "- Add ablations for each claimed method component.\n"
            "- Track failure cases separately from aggregate scores."
        ),
    }


def _render_conclusion_blocks(
    project: ProjectRecord,
    linked_papers: list[LinkedPaperRecord],
    documents: dict[str, str],
    recent_jobs: list[ProjectJobRecord],
    task_input: ProjectTaskInput,
) -> dict[str, str]:
    return {
        "conclusion_summary": (
            f"Summarize the current state of {project.name} from overview, related work, "
            "method, and experiment modules."
            + _focus_suffix(task_input)
        ),
        "open_problems": (
            "- Confirm whether linked papers cover all required baselines.\n"
            "- Validate that method claims are supported by experiment evidence.\n"
            "- Record unresolved dataset or metric gaps."
        ),
        "next_steps": (
            "- Review generated module blocks.\n"
            "- Lock accepted content with managed=\"false\" if it should not be overwritten.\n"
            "- Trigger manuscript compilation after module content stabilizes."
        ),
    }


def _render_manuscript_blocks(
    project: ProjectRecord,
    linked_papers: list[LinkedPaperRecord],
    documents: dict[str, str],
    recent_jobs: list[ProjectJobRecord],
    task_input: ProjectTaskInput,
) -> dict[str, str]:
    return {
        "manuscript_abstract": f"Draft abstract for {project.name}.",
        "manuscript_introduction": _section_seed(project, documents, "overview"),
        "manuscript_related_work": _section_seed(project, documents, "related_work"),
        "manuscript_method": _section_seed(project, documents, "method"),
        "manuscript_experiment": _section_seed(project, documents, "experiment"),
        "manuscript_conclusion": _section_seed(project, documents, "conclusion"),
    }


def _render_generic_blocks(
    project: ProjectRecord,
    linked_papers: list[LinkedPaperRecord],
    documents: dict[str, str],
    recent_jobs: list[ProjectJobRecord],
    task_input: ProjectTaskInput,
) -> dict[str, str]:
    return {"summary": f"Generated project task output for {project.name}."}


_BLOCK_RENDERERS: dict[str, BlockRenderer] = {
    "project_refresh_overview": _render_overview_blocks,
    "project_generate_related_work": _render_related_work_blocks,
    "project_generate_method": _render_method_blocks,
    "project_generate_experiment": _render_experiment_blocks,
    "project_generate_conclusion": _render_conclusion_blocks,
    "project_generate_manuscript": _render_manuscript_blocks,
}


def _paper_lines(linked_papers: list[LinkedPaperRecord]) -> str:
    if not linked_papers:
        return "No linked papers yet."
    return "\n".join(
        f"- [{paper.relation_type}] {paper.title} (paper_id={paper.paper_id})"
        for paper in linked_papers
    )


def _group_papers_by_relation(linked_papers: list[LinkedPaperRecord]) -> str:
    if not linked_papers:
        return "No linked papers to group."
    grouped: dict[str, list[str]] = {}
    for paper in linked_papers:
        grouped.setdefault(paper.relation_type, []).append(paper.title)
    return "\n".join(
        f"- {relation}: {', '.join(titles)}"
        for relation, titles in sorted(grouped.items())
    )


def _focus_suffix(task_input: ProjectTaskInput) -> str:
    if not task_input.focus_instructions:
        return ""
    return f"\n\nFocus instruction: {task_input.focus_instructions}"


def _excerpt(content: str, limit: int = 500) -> str:
    compact = " ".join(content.split())
    if not compact:
        return "No prior module content."
    return compact[:limit]


def _section_seed(
    project: ProjectRecord,
    documents: dict[str, str],
    doc_role: str,
) -> str:
    excerpt = _excerpt(documents.get(doc_role, ""), limit=700)
    return f"Use the {doc_role} module as the source for {project.name}: {excerpt}"
