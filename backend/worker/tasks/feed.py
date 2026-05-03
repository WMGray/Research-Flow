from __future__ import annotations

from core.task_names import FEED_DAILY_PUSH, FEED_FETCH_AND_SCORE
from worker.app import celery


@celery.task(name=FEED_FETCH_AND_SCORE)
def fetch_and_score() -> dict[str, object]:
    return {"status": "not_implemented", "message": "Daily feed worker task is reserved."}


@celery.task(name=FEED_DAILY_PUSH)
def daily_push() -> dict[str, object]:
    return {"status": "not_implemented", "message": "Daily push worker task is reserved."}
