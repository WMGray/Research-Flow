"""SQLite-backed Dataset, Knowledge, and Presentation repository."""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any
from uuid import uuid4

from core.assets import create_asset, create_asset_link, update_asset_from_path
from core.schema import PROJECT_SCHEMA_SQL
from core.services.papers.models import JobRecord, utc_now
from core.services.resources.models import (
    DatasetRecord,
    KnowledgeRecord,
    PresentationDocumentRecord,
    PresentationRecord,
    ResourceLinkRecord,
    ResourceNotFoundError,
    ResourceVersionConflictError,
)
from core.storage import configured_data_root, configured_db_path


PRESENTATION_DOCUMENTS: tuple[tuple[str, str, str], ...] = (
    ("outline", "outline.md", "# Outline\n\n"),
    ("slides", "slides.md", "# Slides\n\n"),
    ("speaker_notes", "speaker-notes.md", "# Speaker Notes\n\n"),
)


def _slugify(value: str, fallback: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return f"{slug or fallback}-{uuid4().hex[:8]}"


class ResourceRepository:
    def __init__(
        self,
        db_path: Path | None = None,
        data_root: Path | None = None,
    ) -> None:
        self.db_path = db_path or configured_db_path()
        self.data_root = data_root or configured_data_root()
        self.resource_root = self.data_root / "resources_api"
        self.initialize()

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.resource_root.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript(PROJECT_SCHEMA_SQL)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # Dataset
    def create_dataset(self, values: dict[str, Any]) -> DatasetRecord:
        now = utc_now()
        name = str(values["name"])
        dataset_dir = self.resource_root / "datasets" / _slugify(name, "dataset")
        dataset_dir.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            asset_id = create_asset(
                conn,
                storage_path=dataset_dir,
                display_name=name,
                asset_type="Dataset",
                now=now,
            )
            conn.execute(
                """
                INSERT INTO biz_dataset (
                    asset_id, name, normalized_name, aliases_json, task_type,
                    data_domain, scale, source, description, access_url,
                    benchmark_summary, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    asset_id,
                    name,
                    values.get("normalized_name", ""),
                    json.dumps(values.get("aliases", []), ensure_ascii=False),
                    values.get("task_type", ""),
                    values.get("data_domain", ""),
                    values.get("scale", ""),
                    values.get("source", ""),
                    values.get("description", ""),
                    values.get("access_url", ""),
                    values.get("benchmark_summary", ""),
                    now,
                    now,
                ),
            )
            conn.commit()
        return self.get_dataset(asset_id)

    def list_datasets(self, query: dict[str, Any]) -> tuple[list[DatasetRecord], int]:
        where = ["ar.is_deleted = 0"]
        params: list[Any] = []
        if query.get("q"):
            where.append("(bd.name LIKE ? OR bd.description LIKE ?)")
            pattern = f"%{query['q']}%"
            params.extend([pattern, pattern])
        if query.get("task_type"):
            where.append("bd.task_type = ?")
            params.append(query["task_type"])
        where_sql = " AND ".join(where)
        page, page_size, offset = self._page(query)
        with self.connect() as conn:
            total = self._count(conn, "biz_dataset bd", where_sql, params)
            rows = conn.execute(
                f"""
                SELECT bd.*, ar.created_at AS asset_created_at,
                    ar.updated_at AS asset_updated_at
                FROM biz_dataset bd
                JOIN asset_registry ar ON ar.asset_id = bd.asset_id
                WHERE {where_sql}
                ORDER BY ar.updated_at DESC
                LIMIT ? OFFSET ?
                """,
                [*params, page_size, offset],
            ).fetchall()
        return [self._dataset_from_row(row) for row in rows], total

    def get_dataset(self, dataset_id: int) -> DatasetRecord:
        row = self._get_row("biz_dataset", "bd", dataset_id)
        return self._dataset_from_row(row)

    def update_dataset(self, dataset_id: int, values: dict[str, Any]) -> DatasetRecord:
        allowed = {
            "name",
            "normalized_name",
            "aliases",
            "task_type",
            "data_domain",
            "scale",
            "source",
            "description",
            "access_url",
            "benchmark_summary",
        }
        mapped = {key: value for key, value in values.items() if key in allowed}
        if "aliases" in mapped:
            mapped["aliases_json"] = json.dumps(mapped.pop("aliases"), ensure_ascii=False)
        self._update_table("biz_dataset", dataset_id, mapped, display_name_key="name")
        return self.get_dataset(dataset_id)

    def delete_dataset(self, dataset_id: int) -> None:
        self._delete_asset(dataset_id, "Dataset")

    # Knowledge
    def create_knowledge(self, values: dict[str, Any]) -> KnowledgeRecord:
        now = utc_now()
        title = str(values["title"])
        knowledge_dir = self.resource_root / "knowledge" / _slugify(title, "knowledge")
        knowledge_dir.mkdir(parents=True, exist_ok=True)
        source_paper_id = values.get("source_paper_asset_id")
        if source_paper_id is not None:
            self._ensure_asset(int(source_paper_id), "Paper")
        with self.connect() as conn:
            asset_id = create_asset(
                conn,
                storage_path=knowledge_dir,
                display_name=title,
                asset_type="Knowledge",
                now=now,
            )
            conn.execute(
                """
                INSERT INTO biz_knowledge (
                    asset_id, knowledge_type, title, summary_zh, original_text_en,
                    citation_marker, category_label, research_field,
                    source_paper_asset_id, source_section, source_locator,
                    evidence_text, confidence_score, review_status, llm_run_id,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    asset_id,
                    values.get("knowledge_type", "view"),
                    title,
                    values.get("summary_zh", ""),
                    values.get("original_text_en", ""),
                    values.get("citation_marker", ""),
                    values.get("category_label", ""),
                    values.get("research_field", ""),
                    source_paper_id,
                    values.get("source_section", ""),
                    values.get("source_locator", ""),
                    values.get("evidence_text", ""),
                    values.get("confidence_score", 0.0),
                    values.get("review_status", "pending_review"),
                    values.get("llm_run_id", ""),
                    now,
                    now,
                ),
            )
            if source_paper_id is not None:
                create_asset_link(
                    conn,
                    source_id=asset_id,
                    target_id=int(source_paper_id),
                    relation_type="EXTRACTED_FROM",
                )
            conn.commit()
        return self.get_knowledge(asset_id)

    def list_knowledge(self, query: dict[str, Any]) -> tuple[list[KnowledgeRecord], int]:
        where = ["ar.is_deleted = 0"]
        params: list[Any] = []
        if query.get("q"):
            where.append("(bk.title LIKE ? OR bk.summary_zh LIKE ? OR bk.evidence_text LIKE ?)")
            pattern = f"%{query['q']}%"
            params.extend([pattern, pattern, pattern])
        for key in ("knowledge_type", "review_status", "source_paper_asset_id"):
            if query.get(key) is not None and query.get(key) != "":
                where.append(f"bk.{key} = ?")
                params.append(query[key])
        where_sql = " AND ".join(where)
        page, page_size, offset = self._page(query)
        with self.connect() as conn:
            total = self._count(conn, "biz_knowledge bk", where_sql, params)
            rows = conn.execute(
                f"""
                SELECT bk.*, ar.created_at AS asset_created_at,
                    ar.updated_at AS asset_updated_at
                FROM biz_knowledge bk
                JOIN asset_registry ar ON ar.asset_id = bk.asset_id
                WHERE {where_sql}
                ORDER BY ar.updated_at DESC
                LIMIT ? OFFSET ?
                """,
                [*params, page_size, offset],
            ).fetchall()
        return [self._knowledge_from_row(row) for row in rows], total

    def get_knowledge(self, knowledge_id: int) -> KnowledgeRecord:
        row = self._get_row("biz_knowledge", "bk", knowledge_id)
        return self._knowledge_from_row(row)

    def update_knowledge(self, knowledge_id: int, values: dict[str, Any]) -> KnowledgeRecord:
        allowed = {
            "knowledge_type",
            "title",
            "summary_zh",
            "original_text_en",
            "citation_marker",
            "category_label",
            "research_field",
            "source_paper_asset_id",
            "source_section",
            "source_locator",
            "evidence_text",
            "confidence_score",
            "review_status",
            "llm_run_id",
        }
        mapped = {key: value for key, value in values.items() if key in allowed}
        if "source_paper_asset_id" in mapped and mapped["source_paper_asset_id"] is not None:
            self._ensure_asset(int(mapped["source_paper_asset_id"]), "Paper")
        self._update_table("biz_knowledge", knowledge_id, mapped, display_name_key="title")
        return self.get_knowledge(knowledge_id)

    def delete_knowledge(self, knowledge_id: int) -> None:
        self._delete_asset(knowledge_id, "Knowledge")

    # Presentation
    def create_presentation(self, values: dict[str, Any]) -> PresentationRecord:
        now = utc_now()
        title = str(values["title"])
        project_id = values.get("project_asset_id")
        if project_id is not None:
            self._ensure_asset(int(project_id), "Project")
        presentation_dir = self.resource_root / "presentations" / _slugify(
            title, "presentation"
        )
        presentation_dir.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            asset_id = create_asset(
                conn,
                storage_path=presentation_dir,
                display_name=title,
                asset_type="Presentation",
                now=now,
            )
            conn.execute(
                """
                INSERT INTO biz_presentation (
                    asset_id, project_asset_id, title, scene_type, status,
                    export_format, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    asset_id,
                    project_id,
                    title,
                    values.get("scene_type", "group_meeting"),
                    values.get("status", "draft"),
                    values.get("export_format", ""),
                    now,
                    now,
                ),
            )
            self._create_presentation_documents(conn, asset_id, presentation_dir, now)
            if project_id is not None:
                create_asset_link(
                    conn,
                    source_id=int(project_id),
                    target_id=asset_id,
                    relation_type="HAS_PRESENTATION",
                )
            conn.commit()
        return self.get_presentation(asset_id)

    def list_presentations(
        self, query: dict[str, Any]
    ) -> tuple[list[PresentationRecord], int]:
        where = ["ar.is_deleted = 0"]
        params: list[Any] = []
        if query.get("q"):
            where.append("(bp.title LIKE ? OR bp.scene_type LIKE ?)")
            pattern = f"%{query['q']}%"
            params.extend([pattern, pattern])
        for key in ("project_asset_id", "status", "scene_type"):
            if query.get(key) is not None and query.get(key) != "":
                where.append(f"bp.{key} = ?")
                params.append(query[key])
        where_sql = " AND ".join(where)
        page, page_size, offset = self._page(query)
        with self.connect() as conn:
            total = self._count(conn, "biz_presentation bp", where_sql, params)
            rows = conn.execute(
                f"""
                SELECT bp.*, ar.created_at AS asset_created_at,
                    ar.updated_at AS asset_updated_at
                FROM biz_presentation bp
                JOIN asset_registry ar ON ar.asset_id = bp.asset_id
                WHERE {where_sql}
                ORDER BY ar.updated_at DESC
                LIMIT ? OFFSET ?
                """,
                [*params, page_size, offset],
            ).fetchall()
        return [self._presentation_from_row(row) for row in rows], total

    def get_presentation(self, presentation_id: int) -> PresentationRecord:
        row = self._get_row("biz_presentation", "bp", presentation_id)
        return self._presentation_from_row(row)

    def update_presentation(
        self, presentation_id: int, values: dict[str, Any]
    ) -> PresentationRecord:
        allowed = {"project_asset_id", "title", "scene_type", "status", "export_format"}
        mapped = {key: value for key, value in values.items() if key in allowed}
        if "project_asset_id" in mapped and mapped["project_asset_id"] is not None:
            self._ensure_asset(int(mapped["project_asset_id"]), "Project")
        self._update_table("biz_presentation", presentation_id, mapped, display_name_key="title")
        if "project_asset_id" in mapped:
            self._set_presentation_project_link(
                presentation_id,
                mapped["project_asset_id"],
            )
        return self.get_presentation(presentation_id)

    def delete_presentation(self, presentation_id: int) -> None:
        self._delete_asset(presentation_id, "Presentation")

    def get_presentation_document(
        self, presentation_id: int, doc_role: str
    ) -> PresentationDocumentRecord:
        self.get_presentation(presentation_id)
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT *
                FROM biz_doc_layout
                WHERE parent_id = ? AND doc_role = ?
                """,
                (presentation_id, doc_role),
            ).fetchone()
        if row is None:
            raise ResourceNotFoundError(
                f"Presentation document not found: {presentation_id}/{doc_role}"
            )
        path = Path(row["doc_path"])
        content = path.read_text(encoding="utf-8") if path.exists() else ""
        return PresentationDocumentRecord(
            presentation_id=presentation_id,
            doc_id=int(row["doc_id"]),
            doc_role=str(row["doc_role"]),
            content=content,
            version=int(row["version"]),
            updated_at=str(row["updated_at"]),
        )

    def update_presentation_document(
        self,
        presentation_id: int,
        doc_role: str,
        content: str,
        base_version: int | None,
    ) -> PresentationDocumentRecord:
        document = self.get_presentation_document(presentation_id, doc_role)
        if base_version is not None and base_version != document.version:
            raise ResourceVersionConflictError("Presentation document conflict.")
        now = utc_now()
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT doc_path, doc_id
                FROM biz_doc_layout
                WHERE parent_id = ? AND doc_role = ?
                """,
                (presentation_id, doc_role),
            ).fetchone()
            path = Path(row["doc_path"])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content.rstrip() + "\n", encoding="utf-8")
            update_asset_from_path(conn, asset_id=int(row["doc_id"]), storage_path=path, now=now)
            conn.execute(
                """
                UPDATE biz_doc_layout
                SET version = version + 1, updated_at = ?
                WHERE parent_id = ? AND doc_role = ?
                """,
                (now, presentation_id, doc_role),
            )
            conn.execute(
                "UPDATE asset_registry SET updated_at = ? WHERE asset_id = ?",
                (now, presentation_id),
            )
            conn.commit()
        return self.get_presentation_document(presentation_id, doc_role)

    def run_presentation_task(self, presentation_id: int, task_type: str) -> JobRecord:
        presentation = self.get_presentation(presentation_id)
        if task_type == "presentation_generate_outline":
            doc_role = "outline"
            message = "Generated presentation outline placeholder."
            content = "\n".join(
                [
                    "# Outline",
                    "",
                    f"- Presentation: {presentation.title}",
                    f"- Scene: {presentation.scene_type}",
                    "",
                ]
            )
            result = {"output_doc_role": doc_role}
        elif task_type == "presentation_generate_slides":
            doc_role = "slides"
            message = "Generated presentation slides placeholder."
            content = f"# Slides\n\n## {presentation.title}\n\n- Placeholder slide draft.\n"
            result = {"output_doc_role": doc_role}
        else:
            message = "Prepared presentation export placeholder."
            result = {"export_format": presentation.export_format or "pptx"}
            return self._create_job(
                resource_type="Presentation",
                resource_id=presentation_id,
                job_type=task_type,
                status="succeeded",
                progress=1.0,
                message=message,
                result=result,
            )
        self.update_presentation_document(presentation_id, doc_role, content, None)
        return self._create_job(
            resource_type="Presentation",
            resource_id=presentation_id,
            job_type=task_type,
            status="succeeded",
            progress=1.0,
            message=message,
            result=result,
        )

    # Asset links
    def link_asset(
        self,
        *,
        source_id: int,
        target_id: int,
        target_type: str,
        relation_type: str,
    ) -> list[ResourceLinkRecord]:
        self._ensure_asset(source_id, "Project")
        self._ensure_asset(target_id, target_type)
        with self.connect() as conn:
            if target_type == "Presentation":
                conn.execute(
                    """
                    DELETE FROM asset_link
                    WHERE target_id = ?
                        AND source_id IN (
                            SELECT asset_id FROM biz_project
                        )
                    """,
                    (target_id,),
                )
            else:
                conn.execute(
                    "DELETE FROM asset_link WHERE source_id = ? AND target_id = ?",
                    (source_id, target_id),
                )
            create_asset_link(
                conn,
                source_id=source_id,
                target_id=target_id,
                relation_type=relation_type,
            )
            if target_type == "Presentation":
                conn.execute(
                    """
                    UPDATE biz_presentation
                    SET project_asset_id = ?, updated_at = ?
                    WHERE asset_id = ?
                    """,
                    (source_id, utc_now(), target_id),
                )
            conn.commit()
        return self.list_links(source_id=source_id, target_type=target_type)

    def unlink_asset(self, *, source_id: int, target_id: int, target_type: str) -> None:
        self._ensure_asset(source_id, "Project")
        self._ensure_asset(target_id, target_type)
        with self.connect() as conn:
            conn.execute(
                "DELETE FROM asset_link WHERE source_id = ? AND target_id = ?",
                (source_id, target_id),
            )
            if target_type == "Presentation":
                conn.execute(
                    """
                    UPDATE biz_presentation
                    SET project_asset_id = NULL, updated_at = ?
                    WHERE asset_id = ? AND project_asset_id = ?
                    """,
                    (utc_now(), target_id, source_id),
                )
            conn.commit()

    def list_links(self, *, source_id: int, target_type: str) -> list[ResourceLinkRecord]:
        self._ensure_asset(source_id, "Project")
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT ar.asset_id, ar.asset_type, ar.display_name, al.relation_type,
                    ar.created_at, ar.updated_at
                FROM asset_link al
                JOIN asset_registry ar ON ar.asset_id = al.target_id
                WHERE al.source_id = ? AND ar.asset_type = ? AND ar.is_deleted = 0
                ORDER BY ar.display_name ASC
                """,
                (source_id, target_type),
            ).fetchall()
        return [self._link_from_row(row) for row in rows]

    def list_links_from_source(
        self, *, source_id: int, target_type: str
    ) -> list[ResourceLinkRecord]:
        self._ensure_asset(source_id, "Paper")
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT ar.asset_id, ar.asset_type, ar.display_name, al.relation_type,
                    ar.created_at, ar.updated_at
                FROM asset_link al
                JOIN asset_registry ar ON ar.asset_id = al.target_id
                WHERE al.source_id = ? AND ar.asset_type = ? AND ar.is_deleted = 0
                ORDER BY ar.display_name ASC
                """,
                (source_id, target_type),
            ).fetchall()
        return [self._link_from_row(row) for row in rows]

    def link_dataset_to_paper(
        self,
        *,
        paper_id: int,
        dataset_id: int,
        relation_type: str = "MENTIONS_DATASET",
    ) -> list[ResourceLinkRecord]:
        self._ensure_asset(paper_id, "Paper")
        self._ensure_asset(dataset_id, "Dataset")
        with self.connect() as conn:
            conn.execute(
                "DELETE FROM asset_link WHERE source_id = ? AND target_id = ?",
                (paper_id, dataset_id),
            )
            create_asset_link(
                conn,
                source_id=paper_id,
                target_id=dataset_id,
                relation_type=relation_type,
            )
            conn.commit()
        return self.list_links_from_source(source_id=paper_id, target_type="Dataset")

    def list_knowledge_for_paper(self, paper_id: int) -> list[ResourceLinkRecord]:
        self._ensure_asset(paper_id, "Paper")
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT ar.asset_id, ar.asset_type, ar.display_name, al.relation_type,
                    ar.created_at, ar.updated_at
                FROM asset_link al
                JOIN asset_registry ar ON ar.asset_id = al.source_id
                WHERE al.target_id = ? AND ar.asset_type = 'Knowledge' AND ar.is_deleted = 0
                ORDER BY ar.display_name ASC
                """,
                (paper_id,),
            ).fetchall()
        return [self._link_from_row(row) for row in rows]

    # Internal helpers
    def _get_row(self, table: str, alias: str, asset_id: int) -> sqlite3.Row:
        with self.connect() as conn:
            row = conn.execute(
                f"""
                SELECT {alias}.*, ar.created_at AS asset_created_at,
                    ar.updated_at AS asset_updated_at
                FROM {table} {alias}
                JOIN asset_registry ar ON ar.asset_id = {alias}.asset_id
                WHERE {alias}.asset_id = ? AND ar.is_deleted = 0
                """,
                (asset_id,),
            ).fetchone()
        if row is None:
            raise ResourceNotFoundError(f"Resource not found: {asset_id}")
        return row

    def _count(
        self,
        conn: sqlite3.Connection,
        table_expr: str,
        where_sql: str,
        params: list[Any],
    ) -> int:
        return int(
            conn.execute(
                f"""
                SELECT COUNT(*)
                FROM {table_expr}
                JOIN asset_registry ar ON ar.asset_id = {table_expr.split()[1]}.asset_id
                WHERE {where_sql}
                """,
                params,
            ).fetchone()[0]
        )

    def _update_table(
        self,
        table: str,
        asset_id: int,
        values: dict[str, Any],
        *,
        display_name_key: str,
    ) -> None:
        self._ensure_asset(asset_id, self._asset_type_for_table(table))
        now = utc_now()
        with self.connect() as conn:
            if values:
                columns = [f"{key} = ?" for key in values]
                conn.execute(
                    f"""
                    UPDATE {table}
                    SET {', '.join(columns)}, updated_at = ?
                    WHERE asset_id = ?
                    """,
                    [*values.values(), now, asset_id],
                )
            display_name = values.get(display_name_key)
            if display_name is not None:
                conn.execute(
                    """
                    UPDATE asset_registry
                    SET display_name = ?, updated_at = ?
                    WHERE asset_id = ?
                    """,
                    (display_name, now, asset_id),
                )
            else:
                conn.execute(
                    "UPDATE asset_registry SET updated_at = ? WHERE asset_id = ?",
                    (now, asset_id),
                )
            conn.commit()

    def _delete_asset(self, asset_id: int, asset_type: str) -> None:
        self._ensure_asset(asset_id, asset_type)
        now = utc_now()
        with self.connect() as conn:
            conn.execute(
                "UPDATE asset_registry SET is_deleted = 1, updated_at = ? WHERE asset_id = ?",
                (now, asset_id),
            )
            conn.commit()

    def _ensure_asset(self, asset_id: int, asset_type: str) -> None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT 1
                FROM asset_registry
                WHERE asset_id = ? AND asset_type = ? AND is_deleted = 0
                """,
                (asset_id, asset_type),
            ).fetchone()
        if row is None:
            raise ResourceNotFoundError(f"{asset_type} not found: {asset_id}")

    def _create_presentation_documents(
        self,
        conn: sqlite3.Connection,
        presentation_id: int,
        presentation_dir: Path,
        now: str,
    ) -> None:
        for role, file_name, content in PRESENTATION_DOCUMENTS:
            path = presentation_dir / file_name
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
                source_id=presentation_id,
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
                (presentation_id, doc_id, file_name, str(path), role, 1, now, now),
            )

    def _set_presentation_project_link(
        self,
        presentation_id: int,
        project_id: int | None,
    ) -> None:
        now = utc_now()
        with self.connect() as conn:
            conn.execute(
                """
                DELETE FROM asset_link
                WHERE target_id = ?
                    AND source_id IN (
                        SELECT asset_id FROM biz_project
                    )
                """,
                (presentation_id,),
            )
            if project_id is not None:
                create_asset_link(
                    conn,
                    source_id=int(project_id),
                    target_id=presentation_id,
                    relation_type="HAS_PRESENTATION",
                )
            conn.execute(
                "UPDATE asset_registry SET updated_at = ? WHERE asset_id = ?",
                (now, presentation_id),
            )
            conn.commit()

    def _create_job(
        self,
        *,
        resource_type: str,
        resource_id: int,
        job_type: str,
        status: str,
        progress: float,
        message: str,
        result: dict[str, Any] | None = None,
    ) -> JobRecord:
        job_id = f"job_{uuid4().hex}"
        now = utc_now()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO jobs (
                    job_id, type, status, progress, message, resource_type,
                    resource_id, result, error, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    job_type,
                    status,
                    progress,
                    message,
                    resource_type,
                    resource_id,
                    json.dumps(result, ensure_ascii=False) if result is not None else None,
                    None,
                    now,
                    now,
                ),
            )
            conn.commit()
        return JobRecord(
            job_id=job_id,
            type=job_type,
            status=status,
            progress=progress,
            message=message,
            resource_type=resource_type,
            resource_id=resource_id,
            created_at=now,
            updated_at=now,
            result=result,
            error=None,
        )

    def _asset_map(self, parent_id: int) -> dict[str, int]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT doc_id, doc_role
                FROM biz_doc_layout
                WHERE parent_id = ?
                """,
                (parent_id,),
            ).fetchall()
        return {str(row["doc_role"]): int(row["doc_id"]) for row in rows}

    def _page(self, query: dict[str, Any]) -> tuple[int, int, int]:
        page = int(query.get("page", 1))
        page_size = int(query.get("page_size", 20))
        return page, page_size, (page - 1) * page_size

    def _asset_type_for_table(self, table: str) -> str:
        return {
            "biz_dataset": "Dataset",
            "biz_knowledge": "Knowledge",
            "biz_presentation": "Presentation",
        }[table]

    def _dataset_from_row(self, row: sqlite3.Row) -> DatasetRecord:
        asset_id = int(row["asset_id"])
        return DatasetRecord(
            dataset_id=asset_id,
            asset_id=asset_id,
            name=str(row["name"]),
            normalized_name=str(row["normalized_name"] or ""),
            aliases=json.loads(row["aliases_json"] or "[]"),
            task_type=str(row["task_type"] or ""),
            data_domain=str(row["data_domain"] or ""),
            scale=str(row["scale"] or ""),
            source=str(row["source"] or ""),
            description=str(row["description"] or ""),
            access_url=str(row["access_url"] or ""),
            benchmark_summary=str(row["benchmark_summary"] or ""),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    def _knowledge_from_row(self, row: sqlite3.Row) -> KnowledgeRecord:
        asset_id = int(row["asset_id"])
        return KnowledgeRecord(
            knowledge_id=asset_id,
            asset_id=asset_id,
            knowledge_type=str(row["knowledge_type"]),
            title=str(row["title"]),
            summary_zh=str(row["summary_zh"] or ""),
            original_text_en=str(row["original_text_en"] or ""),
            citation_marker=str(row["citation_marker"] or ""),
            category_label=str(row["category_label"] or ""),
            research_field=str(row["research_field"] or ""),
            source_paper_asset_id=row["source_paper_asset_id"],
            source_section=str(row["source_section"] or ""),
            source_locator=str(row["source_locator"] or ""),
            evidence_text=str(row["evidence_text"] or ""),
            confidence_score=float(row["confidence_score"] or 0.0),
            review_status=str(row["review_status"]),
            llm_run_id=str(row["llm_run_id"] or ""),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    def _presentation_from_row(self, row: sqlite3.Row) -> PresentationRecord:
        asset_id = int(row["asset_id"])
        return PresentationRecord(
            presentation_id=asset_id,
            asset_id=asset_id,
            project_asset_id=row["project_asset_id"],
            title=str(row["title"]),
            scene_type=str(row["scene_type"]),
            status=str(row["status"]),
            export_format=str(row["export_format"] or ""),
            assets=self._asset_map(asset_id),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    def _link_from_row(self, row: sqlite3.Row) -> ResourceLinkRecord:
        asset_id = int(row["asset_id"])
        return ResourceLinkRecord(
            resource_id=asset_id,
            asset_id=asset_id,
            resource_type=str(row["asset_type"]),
            display_name=str(row["display_name"]),
            relation_type=str(row["relation_type"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )
