from __future__ import annotations

import pytest

from core import task_names


def test_worker_registers_all_shared_task_names() -> None:
    pytest.importorskip("celery")
    from worker.app import celery

    registered = set(celery.tasks)

    assert set(task_names.ALL_TASK_NAMES) <= registered
