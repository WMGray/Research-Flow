"""Celery Beat schedule.

Task names are imported from core.task_names to avoid string drift.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

try:
    from celery.schedules import crontab
except ModuleNotFoundError:  # pragma: no cover - exercised in minimal local envs

    @dataclass(frozen=True)
    class LocalCrontab:
        kwargs: dict[str, Any]

    def crontab(**kwargs: Any) -> LocalCrontab:
        return LocalCrontab(kwargs=kwargs)

from core.task_names import CONFERENCE_REFRESH_ALL, FEED_FETCH_AND_SCORE

# Beat only describes when to dispatch tasks; implementations live in worker/tasks.
beat_schedule = {
    "daily-paper-push": {
        "task": FEED_FETCH_AND_SCORE,
        "schedule": crontab(hour=8, minute=0),
    },
    "conference-refresh": {
        "task": CONFERENCE_REFRESH_ALL,
        "schedule": crontab(day_of_week=1, hour=0),
    },
}
