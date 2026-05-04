from __future__ import annotations

from dataclasses import asdict

from core.services.papers import ParsePaperInput, RefineParseInput
from core.services.papers.service import PaperService
from core.task_names import (
    PAPER_DOWNLOAD,
    PAPER_EXTRACT_DATASETS,
    PAPER_EXTRACT_KNOWLEDGE,
    PAPER_GENERATE_NOTE,
    PAPER_CONFIRM_PIPELINE,
    PAPER_IMPORT_PIPELINE,
    PAPER_PARSE,
    PAPER_REFINE,
    PAPER_RETRY_PIPELINE,
    PAPER_SPLIT,
)
from worker.app import celery


@celery.task(name=PAPER_DOWNLOAD)
def paper_download(paper_id: int) -> dict[str, object]:
    return asdict(PaperService().run_download(paper_id))


@celery.task(name=PAPER_PARSE)
def parse(paper_id: int, parser: str = "mineru", force: bool = False) -> dict[str, object]:
    request = ParsePaperInput(parser=parser, force=force)
    return asdict(PaperService().run_parse(paper_id, request))


@celery.task(name=PAPER_REFINE)
def refine(
    paper_id: int,
    skill_key: str = "paper_refine_parse",
    instruction: str = "",
) -> dict[str, object]:
    request = RefineParseInput(skill_key=skill_key, instruction=instruction)
    return asdict(PaperService().run_refine_parse(paper_id, request))


@celery.task(name=PAPER_SPLIT)
def split(paper_id: int) -> dict[str, object]:
    return asdict(PaperService().run_split_sections(paper_id))


@celery.task(name=PAPER_GENERATE_NOTE)
def generate_note(paper_id: int) -> dict[str, object]:
    return asdict(PaperService().run_generate_note(paper_id))


@celery.task(name=PAPER_EXTRACT_KNOWLEDGE)
def extract_knowledge(paper_id: int) -> dict[str, object]:
    return asdict(PaperService().run_extract_knowledge(paper_id))


@celery.task(name=PAPER_EXTRACT_DATASETS)
def extract_datasets(paper_id: int) -> dict[str, object]:
    return asdict(PaperService().run_extract_datasets(paper_id))


@celery.task(name=PAPER_CONFIRM_PIPELINE)
def confirm_pipeline(paper_id: int, parent_job_id: str | None = None) -> dict[str, object]:
    return asdict(PaperService().run_confirm_pipeline(paper_id, parent_job_id))


@celery.task(name=PAPER_IMPORT_PIPELINE)
def import_pipeline(paper_id: int, parent_job_id: str | None = None) -> dict[str, object]:
    return asdict(PaperService().run_import_pipeline(paper_id, parent_job_id))


@celery.task(name=PAPER_RETRY_PIPELINE)
def retry_pipeline(paper_id: int, parent_job_id: str | None = None) -> dict[str, object]:
    return asdict(PaperService().run_retry_pipeline(paper_id, parent_job_id))
