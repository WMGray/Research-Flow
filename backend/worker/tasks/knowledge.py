from __future__ import annotations

from core.task_names import KNOWLEDGE_NORMALIZE
from worker.app import celery


@celery.task(name=KNOWLEDGE_NORMALIZE)
def normalize(knowledge_id: int) -> dict[str, object]:
    return {
        "knowledge_id": knowledge_id,
        "status": "not_implemented",
        "message": "Knowledge normalization worker task is reserved.",
    }
