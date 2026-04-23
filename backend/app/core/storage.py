from __future__ import annotations

import os
from pathlib import Path

from app.core.config import backend_root


def configured_data_root() -> Path:
    raw_path = os.getenv("RFLOW_STORAGE_DIR")
    path = Path(raw_path).expanduser() if raw_path else backend_root() / "data"
    return path.resolve()


def configured_db_path() -> Path:
    raw_path = os.getenv("RFLOW_DB_PATH")
    path = (
        Path(raw_path).expanduser()
        if raw_path
        else configured_data_root() / "db" / "research_flow.sqlite"
    )
    if not path.is_absolute():
        path = backend_root() / path
    return path.resolve()
