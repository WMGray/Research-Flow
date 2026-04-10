from celery.schedules import crontab

beat_schedule = {
    "daily-paper-push": {
        "task": "worker.tasks.push.fetch_and_score",
        "schedule": crontab(hour=8, minute=0),  # 每天早 8 点
    },
    "conference-refresh": {
        "task": "worker.tasks.conference.refresh_all",
        "schedule": crontab(day_of_week=1, hour=0),  # 每周一凌晨
    },
}
