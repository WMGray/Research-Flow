from __future__ import annotations

from dataclasses import asdict

from core.services.projects import ProjectTaskInput, ProjectTaskService
from core.task_names import (
    PROJECT_GENERATE_CONCLUSION,
    PROJECT_GENERATE_EXPERIMENT,
    PROJECT_GENERATE_MANUSCRIPT,
    PROJECT_GENERATE_METHOD,
    PROJECT_GENERATE_RELATED_WORK,
    PROJECT_REFRESH_OVERVIEW,
)
from worker.app import celery


def _task_input(payload: dict[str, object] | None = None) -> ProjectTaskInput:
    values = payload or {}
    return ProjectTaskInput(
        focus_instructions=str(values.get("focus_instructions", "")),
        included_paper_ids=tuple(int(item) for item in values.get("included_paper_ids", [])),
        included_knowledge_ids=tuple(
            int(item) for item in values.get("included_knowledge_ids", [])
        ),
        included_dataset_ids=tuple(
            int(item) for item in values.get("included_dataset_ids", [])
        ),
        skip_locked_blocks=bool(values.get("skip_locked_blocks", True)),
    )


@celery.task(name=PROJECT_REFRESH_OVERVIEW)
def refresh_overview(
    project_id: int,
    payload: dict[str, object] | None = None,
) -> dict[str, object]:
    return asdict(ProjectTaskService().run_refresh_overview(project_id, _task_input(payload)))


@celery.task(name=PROJECT_GENERATE_RELATED_WORK)
def generate_related_work(
    project_id: int,
    payload: dict[str, object] | None = None,
) -> dict[str, object]:
    return asdict(ProjectTaskService().run_generate_related_work(project_id, _task_input(payload)))


@celery.task(name=PROJECT_GENERATE_METHOD)
def generate_method(
    project_id: int,
    payload: dict[str, object] | None = None,
) -> dict[str, object]:
    return asdict(ProjectTaskService().run_generate_method(project_id, _task_input(payload)))


@celery.task(name=PROJECT_GENERATE_EXPERIMENT)
def generate_experiment(
    project_id: int,
    payload: dict[str, object] | None = None,
) -> dict[str, object]:
    return asdict(ProjectTaskService().run_generate_experiment(project_id, _task_input(payload)))


@celery.task(name=PROJECT_GENERATE_CONCLUSION)
def generate_conclusion(
    project_id: int,
    payload: dict[str, object] | None = None,
) -> dict[str, object]:
    return asdict(ProjectTaskService().run_generate_conclusion(project_id, _task_input(payload)))


@celery.task(name=PROJECT_GENERATE_MANUSCRIPT)
def generate_manuscript(
    project_id: int,
    payload: dict[str, object] | None = None,
) -> dict[str, object]:
    return asdict(ProjectTaskService().run_generate_manuscript(project_id, _task_input(payload)))
