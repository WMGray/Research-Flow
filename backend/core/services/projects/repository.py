"""Project repository used by the API layer."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any
from uuid import uuid4

from core.assets import create_asset, create_asset_link, update_asset_from_path
from core.schema import PROJECT_SCHEMA_SQL
from core.storage import configured_data_root, configured_db_path

from core.services.projects.models import (
    DEFAULT_PAPER_RELATION_TYPE,
    DEFAULT_PROJECT_STATUS,
    PROJECT_DOCUMENTS,
    LinkedPaperNotFoundError,
    LinkedPaperRecord,
    ProjectDocumentNotFoundError,
    ProjectDocumentRecord,
    ProjectDocumentVersionConflictError,
    ProjectNotFoundError,
    ProjectRecord,
)


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    base = slug or "project"
    return f"{base}-{uuid4().hex[:8]}"


def utc_now() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat()


class ProjectRepository:
    def __init__(
        self,
        db_path: Path | None = None,
        data_root: Path | None = None,
    ) -> None:
        self.db_path = db_path or configured_db_path()
        self.data_root = data_root or configured_data_root()
        self.project_root = self.data_root / "projects_api"
        self.initialize()

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.project_root.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript(PROJECT_SCHEMA_SQL)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def create_project(self, values: dict[str, Any]) -> ProjectRecord:
        now = utc_now()
        name = str(values["name"])
        project_slug = str(values.get("project_slug") or slugify(name))
        project_status = str(values.get("status", DEFAULT_PROJECT_STATUS))
        project_dir = self.project_root / project_slug

        with self.connect() as conn:
            project_dir.mkdir(parents=True, exist_ok=True)
            asset_id = create_asset(
                conn,
                storage_path=project_dir,
                display_name=name,
                asset_type="Project",
                now=now,
            )
            conn.execute(
                """
                INSERT INTO biz_project (
                    asset_id, name, project_slug, status, summary, owner,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    asset_id,
                    name,
                    project_slug,
                    project_status,
                    values.get("summary", ""),
                    values.get("owner", ""),
                    now,
                    now,
                ),
            )
            self._create_default_documents(conn, asset_id, project_dir, now)
            conn.commit()
        return self.get_project(asset_id)

    def get_project(self, project_id: int) -> ProjectRecord:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT bp.*, ar.created_at AS asset_created_at,
                    ar.updated_at AS asset_updated_at, ar.is_deleted
                FROM biz_project bp
                JOIN asset_registry ar ON ar.asset_id = bp.asset_id
                WHERE bp.asset_id = ? AND ar.is_deleted = 0
                """,
                (project_id,),
            ).fetchone()
        if row is None:
            raise ProjectNotFoundError(f"Project not found: {project_id}")
        return self._project_from_row(row)

    def list_projects(self, query: dict[str, Any]) -> tuple[list[ProjectRecord], int]:
        where = ["ar.is_deleted = 0"]
        params: list[Any] = []
        if query.get("q"):
            where.append("(bp.name LIKE ? OR bp.summary LIKE ?)")
            pattern = f"%{query['q']}%"
            params.extend([pattern, pattern])
        if query.get("status"):
            where.append("bp.status = ?")
            params.append(query["status"])

        where_sql = " AND ".join(where)
        page = int(query.get("page", 1))
        page_size = int(query.get("page_size", 20))
        offset = (page - 1) * page_size

        with self.connect() as conn:
            total = int(
                conn.execute(
                    f"""
                    SELECT COUNT(*)
                    FROM biz_project bp
                    JOIN asset_registry ar ON ar.asset_id = bp.asset_id
                    WHERE {where_sql}
                    """,
                    params,
                ).fetchone()[0]
            )
            rows = conn.execute(
                f"""
                SELECT bp.*, ar.created_at AS asset_created_at,
                    ar.updated_at AS asset_updated_at, ar.is_deleted
                FROM biz_project bp
                JOIN asset_registry ar ON ar.asset_id = bp.asset_id
                WHERE {where_sql}
                ORDER BY ar.updated_at DESC
                LIMIT ? OFFSET ?
                """,
                [*params, page_size, offset],
            ).fetchall()
        return [self._project_from_row(row) for row in rows], total

    def update_project(self, project_id: int, values: dict[str, Any]) -> ProjectRecord:
        self.get_project(project_id)
        allowed = {"name", "status", "summary", "owner"}
        mapped = {key: value for key, value in values.items() if key in allowed}
        now = utc_now()

        with self.connect() as conn:
            if mapped:
                columns = [f"{key} = ?" for key in mapped]
                params = [*mapped.values(), now, project_id]
                conn.execute(
                    f"""
                    UPDATE biz_project
                    SET {', '.join(columns)}, updated_at = ?
                    WHERE asset_id = ?
                    """,
                    params,
                )
            conn.execute(
                "UPDATE asset_registry SET updated_at = ? WHERE asset_id = ?",
                (now, project_id),
            )
            if "name" in mapped:
                conn.execute(
                    "UPDATE asset_registry SET display_name = ? WHERE asset_id = ?",
                    (mapped["name"], project_id),
                )
            conn.commit()
        return self.get_project(project_id)

    def delete_project(self, project_id: int) -> None:
        self.get_project(project_id)
        now = utc_now()
        with self.connect() as conn:
            conn.execute(
                "UPDATE asset_registry SET is_deleted = 1, updated_at = ? WHERE asset_id = ?",
                (now, project_id),
            )
            conn.execute(
                "UPDATE biz_project SET updated_at = ? WHERE asset_id = ?",
                (now, project_id),
            )
            conn.commit()

    def link_paper(
        self,
        project_id: int,
        paper_id: int,
        relation_type: str = DEFAULT_PAPER_RELATION_TYPE,
    ) -> list[LinkedPaperRecord]:
        self.get_project(project_id)
        self._ensure_paper_exists(paper_id)
        normalized_relation_type = str(relation_type or DEFAULT_PAPER_RELATION_TYPE)
        with self.connect() as conn:
            conn.execute(
                "DELETE FROM asset_link WHERE source_id = ? AND target_id = ?",
                (project_id, paper_id),
            )
            create_asset_link(
                conn,
                source_id=project_id,
                target_id=paper_id,
                relation_type=normalized_relation_type,
            )
            conn.commit()
        return self.list_linked_papers(project_id)

    def unlink_paper(self, project_id: int, paper_id: int) -> None:
        self.get_project(project_id)
        self._ensure_paper_exists(paper_id)
        with self.connect() as conn:
            conn.execute(
                "DELETE FROM asset_link WHERE source_id = ? AND target_id = ?",
                (project_id, paper_id),
            )
            conn.commit()

    def list_linked_papers(self, project_id: int) -> list[LinkedPaperRecord]:
        self.get_project(project_id)
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT bp.asset_id, bp.title, bp.paper_stage AS status, al.relation_type
                FROM asset_link al
                JOIN biz_paper bp ON bp.asset_id = al.target_id
                JOIN asset_registry ar ON ar.asset_id = bp.asset_id
                WHERE al.source_id = ? AND ar.is_deleted = 0
                ORDER BY bp.title ASC
                """,
                (project_id,),
            ).fetchall()
        return [
            LinkedPaperRecord(
                paper_id=int(row["asset_id"]),
                title=str(row["title"]),
                status=str(row["status"]),
                relation_type=str(row["relation_type"]),
            )
            for row in rows
        ]

    def get_document(self, project_id: int, doc_role: str) -> ProjectDocumentRecord:
        self.get_project(project_id)
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM biz_doc_layout
                WHERE parent_id = ? AND doc_role = ?
                """,
                (project_id, doc_role),
            ).fetchone()
        if row is None:
            raise ProjectDocumentNotFoundError(
                f"Project document not found: {project_id}/{doc_role}"
            )

        path = Path(row["doc_path"])
        content = path.read_text(encoding="utf-8") if path.exists() else ""
        return ProjectDocumentRecord(
            project_id=project_id,
            doc_id=int(row["doc_id"]),
            doc_role=str(row["doc_role"]),
            path=path,
            content=content,
            version=int(row["version"]),
            updated_at=str(row["updated_at"]),
        )

    def update_document(
        self,
        project_id: int,
        doc_role: str,
        content: str,
        base_version: int | None,
    ) -> ProjectDocumentRecord:
        document = self.get_document(project_id, doc_role)
        if base_version is not None and base_version != document.version:
            raise ProjectDocumentVersionConflictError("Project document conflict.")

        now = utc_now()
        document.path.parent.mkdir(parents=True, exist_ok=True)
        document.path.write_text(content.rstrip() + "\n", encoding="utf-8")
        with self.connect() as conn:
            update_asset_from_path(
                conn,
                asset_id=document.doc_id,
                storage_path=document.path,
                now=now,
            )
            conn.execute(
                """
                UPDATE biz_doc_layout
                SET version = version + 1, updated_at = ?
                WHERE parent_id = ? AND doc_role = ?
                """,
                (now, project_id, doc_role),
            )
            conn.execute(
                "UPDATE asset_registry SET updated_at = ? WHERE asset_id = ?",
                (now, project_id),
            )
            conn.commit()
        return self.get_document(project_id, doc_role)

    def _ensure_paper_exists(self, paper_id: int) -> None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT 1
                FROM biz_paper bp
                JOIN asset_registry ar ON ar.asset_id = bp.asset_id
                WHERE bp.asset_id = ? AND ar.is_deleted = 0
                """,
                (paper_id,),
            ).fetchone()
        if row is None:
            raise LinkedPaperNotFoundError(f"Paper not found: {paper_id}")

    def _create_default_documents(
        self,
        conn: sqlite3.Connection,
        project_id: int,
        project_dir: Path,
        now: str,
    ) -> None:
        for role, file_name, content in PROJECT_DOCUMENTS:
            path = project_dir / file_name
            path.write_text(content, encoding="utf-8")
            doc_id = create_asset(
                conn,
                storage_path=path,
                display_name=file_name,
                asset_type="Markdown",
                now=now,
            )
            create_asset_link(
                conn,
                source_id=project_id,
                target_id=doc_id,
                relation_type="CONTAINS",
            )
            conn.execute(
                """
                INSERT INTO biz_doc_layout (
                    parent_id, doc_id, doc_name, doc_path, doc_role,
                    version, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (project_id, doc_id, file_name, str(path), role, 1, now, now),
            )

    def _project_from_row(self, row: sqlite3.Row) -> ProjectRecord:
        asset_id = int(row["asset_id"])
        return ProjectRecord(
            project_id=asset_id,
            asset_id=asset_id,
            name=str(row["name"]),
            project_slug=str(row["project_slug"]),
            status=str(row["status"]),
            summary=str(row["summary"]),
            owner=str(row["owner"]),
            assets=self._asset_map(asset_id),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    def _asset_map(self, project_id: int) -> dict[str, int]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT doc_id, doc_role
                FROM biz_doc_layout
                WHERE parent_id = ?
                """,
                (project_id,),
            ).fetchall()
        return {str(row["doc_role"]): int(row["doc_id"]) for row in rows}
