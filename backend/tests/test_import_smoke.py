from __future__ import annotations

import importlib


def test_core_import_smoke() -> None:
    modules = [
        "app.main",
        "worker.app",
        "core.services.papers.knowledge",
    ]
    for module_name in modules:
        importlib.import_module(module_name)
