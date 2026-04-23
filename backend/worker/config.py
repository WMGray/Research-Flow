from __future__ import annotations

import os

from worker.schedules import beat_schedule as configured_beat_schedule


class CeleryConfig:
    # -----------------------------------------------------------------
    # Broker & Backend（从环境变量读取，默认指向本地 Redis）
    # -----------------------------------------------------------------
    broker_url: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    result_backend: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

    # -----------------------------------------------------------------
    # 序列化
    # -----------------------------------------------------------------
    task_serializer: str = "json"
    result_serializer: str = "json"
    accept_content: list[str] = ["json"]

    # -----------------------------------------------------------------
    # 时区
    # -----------------------------------------------------------------
    timezone: str = "Asia/Shanghai"
    enable_utc: bool = True

    # -----------------------------------------------------------------
    # 任务行为
    # -----------------------------------------------------------------
    task_track_started: bool = True  # 任务开始时记录状态
    task_acks_late: bool = True  # Worker 崩溃时任务重新入队
    task_reject_on_worker_lost: bool = True
    worker_prefetch_multiplier: int = 1  # 每次只预取 1 个任务，避免长任务饥饿

    # -----------------------------------------------------------------
    # 结果过期时间（秒）
    # -----------------------------------------------------------------
    result_expires: int = 60 * 60 * 24  # 24 小时

    # -----------------------------------------------------------------
    # Beat 调度表（从 schedules 模块引入）
    # -----------------------------------------------------------------
    beat_schedule = configured_beat_schedule
    beat_schedule_filename: str = "./logs/celerybeat-schedule"
