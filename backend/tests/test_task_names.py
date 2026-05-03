from __future__ import annotations

from core import task_names
from core.services.projects.tasks.runtime import PROJECT_TASK_SPECS


def test_all_task_names_are_unique() -> None:
    assert len(task_names.ALL_TASK_NAMES) == len(set(task_names.ALL_TASK_NAMES))


def test_paper_task_names_cover_current_job_types() -> None:
    expected_task_names = {
        task_names.PAPER_DOWNLOAD,
        task_names.PAPER_PARSE,
        task_names.PAPER_REFINE,
        task_names.PAPER_SPLIT,
        task_names.PAPER_GENERATE_NOTE,
        task_names.PAPER_EXTRACT_KNOWLEDGE,
        task_names.PAPER_EXTRACT_DATASETS,
        task_names.PAPER_CONFIRM_PIPELINE,
        task_names.PAPER_IMPORT_PIPELINE,
    }

    assert expected_task_names.issubset(set(task_names.ALL_TASK_NAMES))


def test_project_task_names_cover_current_runtime_specs() -> None:
    expected_by_job_type = {
        "project_refresh_overview": task_names.PROJECT_REFRESH_OVERVIEW,
        "project_generate_related_work": task_names.PROJECT_GENERATE_RELATED_WORK,
        "project_generate_method": task_names.PROJECT_GENERATE_METHOD,
        "project_generate_experiment": task_names.PROJECT_GENERATE_EXPERIMENT,
        "project_generate_conclusion": task_names.PROJECT_GENERATE_CONCLUSION,
        "project_generate_manuscript": task_names.PROJECT_GENERATE_MANUSCRIPT,
    }

    runtime_job_types = {
        spec.job_type
        for spec in PROJECT_TASK_SPECS.values()
    }

    assert runtime_job_types == set(expected_by_job_type)
    assert set(expected_by_job_type.values()).issubset(set(task_names.ALL_TASK_NAMES))
