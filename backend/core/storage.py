"""共享存储路径解析。

这里不依赖 FastAPI app 包，因此可以同时被 API 进程与 Worker 进程使用。
"""

from __future__ import annotations

import os
from pathlib import Path


def backend_root() -> Path:
    """返回 backend 包根目录。"""

    return Path(__file__).resolve().parents[1]


def configured_data_root() -> Path:
    """解析运行时数据根目录。"""

    raw_path = os.getenv("RFLOW_STORAGE_DIR")
    path = Path(raw_path).expanduser() if raw_path else backend_root() / "data"
    return path.resolve()


def configured_db_path() -> Path:
    """解析 SQLite 数据库文件路径。"""

    raw_path = os.getenv("RFLOW_DB_PATH")
    path = (
        Path(raw_path).expanduser()
        if raw_path
        else configured_data_root() / "db" / "research_flow.sqlite"
    )
    if not path.is_absolute():
        # 相对路径统一锚定到 backend 根目录，避免启动目录变化导致漂移。
        path = backend_root() / path
    return path.resolve()
