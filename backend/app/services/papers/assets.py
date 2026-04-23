from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path
from uuid import uuid4


def hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def path_hash(path: Path) -> str:
    if path.is_file():
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)
        return digest.hexdigest()
    return hash_text(str(path))


def path_size(path: Path) -> int:
    return path.stat().st_size if path.is_file() else 0


def create_asset(
    conn: sqlite3.Connection,
    *,
    storage_path: Path,
    display_name: str,
    asset_type: str,
    now: str,
) -> int:
    item_id = str(uuid4())
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
    conn.execute(
        """
        INSERT INTO asset_link (source_id, target_id, relation_type)
        VALUES (?, ?, ?)
        """,
        (source_id, target_id, relation_type),
    )
