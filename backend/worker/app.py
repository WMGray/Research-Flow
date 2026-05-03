from __future__ import annotations

from collections.abc import Callable
from importlib import import_module
from typing import Any

try:
    from celery import Celery
except ModuleNotFoundError:  # pragma: no cover - exercised in minimal local envs
    Celery = None  # type: ignore[assignment]

from worker.config import CeleryConfig


class LocalCelery:
    """Tiny import-time fallback when the optional worker package is absent."""

    def __init__(self, app_name: str) -> None:
        self.app_name = app_name
        self.tasks: dict[str, Callable[..., Any]] = {}

    def config_from_object(self, config: type[object]) -> None:
        self.config = config

    def autodiscover_tasks(self, packages: list[str]) -> None:
        for package in packages:
            import_module(package)

    def task(self, *, name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.tasks[name] = func
            setattr(func, "name", name)
            return func

        return decorator


if Celery is None:
    celery = LocalCelery("research-flow")
else:
    celery = Celery("research-flow")

celery.config_from_object(CeleryConfig)
celery.autodiscover_tasks(["worker.tasks"])
