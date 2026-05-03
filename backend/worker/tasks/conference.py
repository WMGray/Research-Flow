from __future__ import annotations

from core.task_names import CONFERENCE_CHECK_DEADLINES, CONFERENCE_REFRESH_ALL
from worker.app import celery


@celery.task(name=CONFERENCE_REFRESH_ALL)
def refresh_all() -> dict[str, object]:
    return {
        "status": "not_implemented",
        "message": "Conference refresh worker task is reserved.",
    }


@celery.task(name=CONFERENCE_CHECK_DEADLINES)
def check_deadlines() -> dict[str, object]:
    return {
        "status": "not_implemented",
        "message": "Conference deadline worker task is reserved.",
    }
