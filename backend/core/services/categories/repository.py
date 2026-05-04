from __future__ import annotations

import sqlite3
from pathlib import Path

from core.schema import PROJECT_SCHEMA_SQL
from core.services.categories.models import (
    CategoryConflictError,
    CategoryInUseError,
    CategoryInvalidParentError,
    CategoryNotFoundError,
    CategoryRecord,
)
from core.storage import configured_db_path


class CategoryRepository:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or configured_db_path()
        self.initialize()

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript(PROJECT_SCHEMA_SQL)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def create_category(
        self,
        *,
        name: str,
        parent_id: int | None = None,
        sort_order: int = 0,
    ) -> CategoryRecord:
        clean_name = self._clean_name(name)
        parent = self.get_category(parent_id) if parent_id is not None else None
        path = self._build_path(clean_name, parent)
        with self.connect() as conn:
            try:
                cursor = conn.execute(
                    """
                    INSERT INTO biz_category (name, parent_id, path, sort_order)
                    VALUES (?, ?, ?, ?)
                    """,
                    (clean_name, parent_id, path, sort_order),
                )
            except sqlite3.IntegrityError as exc:
                raise CategoryConflictError(f"Category path already exists: {path}") from exc
            conn.commit()
        return self.get_category(int(cursor.lastrowid))

    def list_categories(self) -> list[CategoryRecord]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT bc.id, bc.name, bc.parent_id, bc.path, bc.sort_order,
                    COUNT(ar.asset_id) AS paper_count
                FROM biz_category bc
                LEFT JOIN biz_paper bp ON bp.category_id = bc.id
                LEFT JOIN asset_registry ar
                    ON ar.asset_id = bp.asset_id AND ar.is_deleted = 0
                GROUP BY bc.id, bc.name, bc.parent_id, bc.path, bc.sort_order
                ORDER BY bc.parent_id IS NOT NULL, bc.sort_order ASC, bc.name ASC
                """
            ).fetchall()
        return [self._category_from_row(row) for row in rows]

    def get_category(self, category_id: int) -> CategoryRecord:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT bc.id, bc.name, bc.parent_id, bc.path, bc.sort_order,
                    COUNT(ar.asset_id) AS paper_count
                FROM biz_category bc
                LEFT JOIN biz_paper bp ON bp.category_id = bc.id
                LEFT JOIN asset_registry ar
                    ON ar.asset_id = bp.asset_id AND ar.is_deleted = 0
                WHERE bc.id = ?
                GROUP BY bc.id, bc.name, bc.parent_id, bc.path, bc.sort_order
                """,
                (category_id,),
            ).fetchone()
        if row is None:
            raise CategoryNotFoundError(f"Category not found: {category_id}")
        return self._category_from_row(row)

    def update_category(
        self,
        category_id: int,
        *,
        name: str | None = None,
        parent_id: int | None = None,
        parent_id_provided: bool = False,
        sort_order: int | None = None,
    ) -> CategoryRecord:
        current = self.get_category(category_id)
        next_name = self._clean_name(name) if name is not None else current.name
        next_parent_id = parent_id if parent_id_provided else current.parent_id
        if next_parent_id == category_id:
            raise CategoryInvalidParentError("A category cannot be its own parent.")
        parent = self.get_category(next_parent_id) if next_parent_id is not None else None
        if parent is not None and self._is_descendant_path(parent.path, current.path):
            raise CategoryInvalidParentError("A category cannot move under its descendant.")
        next_path = self._build_path(next_name, parent)
        next_sort_order = current.sort_order if sort_order is None else sort_order
        with self.connect() as conn:
            try:
                conn.execute(
                    """
                    UPDATE biz_category
                    SET name = ?, parent_id = ?, path = ?, sort_order = ?
                    WHERE id = ?
                    """,
                    (next_name, next_parent_id, next_path, next_sort_order, category_id),
                )
                self._rewrite_descendant_paths(conn, current.path, next_path)
            except sqlite3.IntegrityError as exc:
                raise CategoryConflictError(
                    f"Category path already exists: {next_path}"
                ) from exc
            conn.commit()
        return self.get_category(category_id)

    def delete_category(self, category_id: int) -> None:
        category = self.get_category(category_id)
        with self.connect() as conn:
            child_count = int(
                conn.execute(
                    "SELECT COUNT(*) FROM biz_category WHERE parent_id = ?",
                    (category_id,),
                ).fetchone()[0]
            )
            paper_count = int(
                conn.execute(
                    """
                    SELECT COUNT(*)
                    FROM biz_paper bp
                    JOIN asset_registry ar ON ar.asset_id = bp.asset_id
                    WHERE bp.category_id = ? AND ar.is_deleted = 0
                    """,
                    (category_id,),
                ).fetchone()[0]
            )
            if child_count or paper_count:
                raise CategoryInUseError(f"Category is in use: {category.path}")
            conn.execute("DELETE FROM biz_category WHERE id = ?", (category_id,))
            conn.commit()

    def _rewrite_descendant_paths(
        self,
        conn: sqlite3.Connection,
        old_path: str,
        new_path: str,
    ) -> None:
        old_prefix = f"{old_path}/"
        rows = conn.execute(
            """
            SELECT id, path
            FROM biz_category
            WHERE path LIKE ?
            """,
            (f"{old_prefix}%",),
        ).fetchall()
        for row in rows:
            child_path = str(row["path"])
            rewritten = f"{new_path}/{child_path.removeprefix(old_prefix)}"
            conn.execute(
                "UPDATE biz_category SET path = ? WHERE id = ?",
                (rewritten, int(row["id"])),
            )

    def _clean_name(self, name: str | None) -> str:
        clean_name = (name or "").strip()
        if not clean_name:
            raise CategoryConflictError("Category name cannot be empty.")
        if "/" in clean_name:
            raise CategoryConflictError("Category name cannot contain '/'.")
        return clean_name

    def _build_path(
        self,
        name: str,
        parent: CategoryRecord | None,
    ) -> str:
        return name if parent is None else f"{parent.path}/{name}"

    def _is_descendant_path(self, path: str, parent_path: str) -> bool:
        return path.startswith(f"{parent_path}/")

    def _category_from_row(self, row: sqlite3.Row) -> CategoryRecord:
        return CategoryRecord(
            category_id=int(row["id"]),
            name=str(row["name"]),
            parent_id=row["parent_id"],
            path=str(row["path"]),
            sort_order=int(row["sort_order"]),
            paper_count=int(row["paper_count"] or 0) if "paper_count" in row.keys() else 0,
        )
