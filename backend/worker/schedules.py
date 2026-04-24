"""Celery Beat 定时任务表。

所有定时任务统一引用 core.task_names，避免 schedule 中写死字符串。
"""

from celery.schedules import crontab

from core.task_names import CONFERENCE_REFRESH_ALL, FEED_FETCH_AND_SCORE

# Beat schedule 只描述“何时投递什么任务”，任务实现放在 worker/tasks。
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
