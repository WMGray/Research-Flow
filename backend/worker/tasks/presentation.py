from __future__ import annotations

from dataclasses import asdict

from core.services.resources import ResourceRepository
from core.task_names import (
    PRESENTATION_EXPORT,
    PRESENTATION_GENERATE_OUTLINE,
    PRESENTATION_GENERATE_SLIDES,
)
from worker.app import celery


@celery.task(name=PRESENTATION_GENERATE_OUTLINE)
def generate_outline(presentation_id: int) -> dict[str, object]:
    job = ResourceRepository().run_presentation_task(
        presentation_id,
        "presentation_generate_outline",
    )
    return asdict(job)


@celery.task(name=PRESENTATION_GENERATE_SLIDES)
def generate_slides(presentation_id: int) -> dict[str, object]:
    job = ResourceRepository().run_presentation_task(
        presentation_id,
        "presentation_generate_slides",
    )
    return asdict(job)


@celery.task(name=PRESENTATION_EXPORT)
def export(presentation_id: int) -> dict[str, object]:
    job = ResourceRepository().run_presentation_task(
        presentation_id,
        "presentation_export",
    )
    return asdict(job)
