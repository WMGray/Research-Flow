"""共享资产 helper。

本模块负责物理文件、目录和逻辑资产之间的基础登记逻辑，供 Paper 与
Project 等资源复用。
"""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path
from uuid import uuid4


def hash_text(value: str) -> str:
    """计算普通字符串的 SHA-256 哈希。"""

    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def path_hash(path: Path) -> str:
    """计算文件内容哈希；目录则使用路径字符串作为稳定指纹。"""

    if path.is_file():
        digest = hashlib.sha256()
        # 分块读取避免大文件一次性载入内存。
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)
        return digest.hexdigest()
    return hash_text(str(path))


def path_size(path: Path) -> int:
    """返回文件大小；目录类资产统一记为 0。"""

    return path.stat().st_size if path.is_file() else 0


def create_asset(
    conn: sqlite3.Connection,
    *,
    storage_path: Path,
    display_name: str,
    asset_type: str,
    now: str,
) -> int:
    """同时创建 physical_item 与 asset_registry 记录。"""

    item_id = str(uuid4())
    # physical_item 表示真实落盘位置，asset_registry 表示平台逻辑资产。
    conn.execute(
        """
        INSERT INTO physical_item (item_id, storage_path, storage_type, ref_count)
        VALUES (?, ?, ?, ?)
        """,
        (item_id, str(storage_path), "LOCAL", 1),
    )
    cursor = conn.execute(
        """
        INSERT INTO asset_registry (
            item_id, display_name, file_ext, file_size, content_hash,
            asset_type, is_deleted, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            item_id,
            display_name,
            storage_path.suffix.lower(),
            path_size(storage_path),
            path_hash(storage_path),
            asset_type,
            0,
            now,
            now,
        ),
    )
    return int(cursor.lastrowid)


def update_asset_from_path(
    conn: sqlite3.Connection,
    *,
    asset_id: int,
    storage_path: Path,
    now: str,
    display_name: str | None = None,
) -> None:
    """根据当前文件状态刷新资产元信息。"""

    assignments = [
        "file_ext = ?",
        "file_size = ?",
        "content_hash = ?",
        "updated_at = ?",
    ]
    params: list[object] = [
        storage_path.suffix.lower(),
        path_size(storage_path),
        path_hash(storage_path),
        now,
    ]
    if display_name is not None:
        # display_name 只有调用方显式传入时才更新，避免误改展示名。
        assignments.insert(0, "display_name = ?")
        params.insert(0, display_name)
    params.append(asset_id)
    conn.execute(
        f"UPDATE asset_registry SET {', '.join(assignments)} WHERE asset_id = ?",
        params,
    )


def create_asset_link(
    conn: sqlite3.Connection,
    *,
    source_id: int,
    target_id: int,
    relation_type: str,
) -> None:
    """创建两个资产之间的显式关系。"""

    conn.execute(
        """
        INSERT INTO asset_link (source_id, target_id, relation_type)
        VALUES (?, ?, ?)
        """,
        (source_id, target_id, relation_type),
    )
