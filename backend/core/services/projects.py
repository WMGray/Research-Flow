"""Project P0 的共享业务仓储服务。

本模块直接落在 core 层，供 FastAPI app 与未来 Celery worker 共同使用；
它负责 Project 的创建、状态维护、六模块文档读写以及 Paper 关联。
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from core.assets import create_asset, create_asset_link, update_asset_from_path
from core.schema import PROJECT_SCHEMA_SQL
from core.storage import configured_data_root, configured_db_path


# 创建 Project 时自动初始化的六个核心 Markdown 模块。
PROJECT_DOCUMENTS: tuple[tuple[str, str, str], ...] = (
    ("overview", "overview.md", "# Overview\n\n"),
    ("related-work", "related-work.md", "# Related Work\n\n"),
    ("method", "method.md", "# Method\n\n"),
    ("experiment", "experiment.md", "# Experiment\n\n"),
    ("conclusion", "conclusion.md", "# Conclusion\n\n"),
    ("manuscript", "manuscript.md", "# Manuscript\n\n"),
)


class ProjectRepositoryError(RuntimeError):
    """Project 仓储层异常基类，供 API 层统一转换为 HTTP 错误。"""

    code = "PROJECT_REPOSITORY_ERROR"


class ProjectNotFoundError(ProjectRepositoryError):
    """目标 Project 不存在或已被软删除。"""

    code = "PROJECT_NOT_FOUND"


class ProjectDocumentNotFoundError(ProjectRepositoryError):
    """目标 Project 文档角色不存在。"""

    code = "PROJECT_DOCUMENT_NOT_FOUND"


class ProjectDocumentVersionConflictError(ProjectRepositoryError):
    """Project 文档更新时发生版本冲突。"""

    code = "PROJECT_DOCUMENT_VERSION_CONFLICT"


class LinkedPaperNotFoundError(ProjectRepositoryError):
    """Project 关联 Paper 时，目标 Paper 不存在。"""

    code = "PAPER_NOT_FOUND"


@dataclass(frozen=True, slots=True)
class ProjectRecord:
    """数据库中的 Project 资源记录。"""

    project_id: int
    asset_id: int
    name: str
    project_slug: str
    status: str
    summary: str
    owner: str
    assets: dict[str, int]
    created_at: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class ProjectDocumentRecord:
    """Project 模块文档记录及其当前文件内容。"""

    project_id: int
    doc_id: int
    doc_role: str
    path: Path
    content: str
    version: int
    updated_at: str


@dataclass(frozen=True, slots=True)
class LinkedPaperRecord:
    """Project 与 Paper 的关联视图记录。"""

    paper_id: int
    title: str
    status: str
    relation_type: str


def slugify(value: str) -> str:
    """将 Project 名称转换为稳定可用的目录 slug。"""

    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    base = slug or "project"
    # 追加短随机后缀，避免同名 Project 目录和唯一索引冲突。
    return f"{base}-{uuid4().hex[:8]}"


class ProjectRepository:
    """Project P0 的 SQLite + 文件系统仓储实现。"""

    def __init__(
        self, db_path: Path | None = None, data_root: Path | None = None
    ) -> None:
        """初始化仓储路径，并确保 Project 所需表和目录存在。"""

        self.db_path = db_path or configured_db_path()
        self.data_root = data_root or configured_data_root()
        self.project_root = self.data_root / "projects_api"
        self.initialize()

    def initialize(self) -> None:
        """创建数据库文件、Project 根目录和必需表结构。"""

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.project_root.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript(PROJECT_SCHEMA_SQL)

    def connect(self) -> sqlite3.Connection:
        """打开 SQLite 连接，并启用 row_factory 便于按列名读取。"""

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def create_project(self, values: dict[str, Any]) -> ProjectRecord:
        """创建 Project 资源，并同步初始化六个 Markdown 模块文档。"""

        now = utc_now()
        name = str(values["name"])
        project_slug = str(values.get("project_slug") or slugify(name))
        project_dir = self.project_root / project_slug

        with self.connect() as conn:
            project_dir.mkdir(parents=True, exist_ok=True)
            # Project 本身先进入统一资产层，再挂接领域表 biz_project。
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
                    values.get("status", "active"),
                    values.get("summary", ""),
                    values.get("owner", ""),
                    now,
                    now,
                ),
            )
            # 六模块文件和 doc_layout 必须与 Project 在同一事务中落库。
            self._create_default_documents(conn, asset_id, project_dir, now)
            conn.commit()
        return self.get_project(asset_id)

    def get_project(self, project_id: int) -> ProjectRecord:
        """根据 asset_id 查询单个未删除 Project。"""

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
        """按关键字、状态和分页条件查询 Project 列表。"""

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
            # total 与 rows 使用同一 where 条件，保持分页元数据一致。
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
        """更新 Project 基础字段和资产层更新时间。"""

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
                # display_name 与 biz_project.name 同步，避免列表展示不一致。
                conn.execute(
                    "UPDATE asset_registry SET display_name = ? WHERE asset_id = ?",
                    (mapped["name"], project_id),
                )
            conn.commit()
        return self.get_project(project_id)

    def link_paper(self, project_id: int, paper_id: int) -> list[LinkedPaperRecord]:
        """将已有 Paper 关联到 Project，重复关联时保持幂等。"""

        self.get_project(project_id)
        self._ensure_paper_exists(paper_id)
        with self.connect() as conn:
            existing = conn.execute(
                """
                SELECT 1 FROM asset_link
                WHERE source_id = ? AND target_id = ? AND relation_type = 'REFERENCES'
                """,
                (project_id, paper_id),
            ).fetchone()
            if existing is None:
                # 当前 P0 使用 REFERENCES 表示 Project 引用 Paper。
                create_asset_link(
                    conn,
                    source_id=project_id,
                    target_id=paper_id,
                    relation_type="REFERENCES",
                )
                conn.commit()
        return self.list_linked_papers(project_id)

    def list_linked_papers(self, project_id: int) -> list[LinkedPaperRecord]:
        """查询 Project 已关联且未删除的 Paper 列表。"""

        self.get_project(project_id)
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT bp.asset_id, bp.title, bp.status, al.relation_type
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
        """读取 Project 指定模块文档及其版本信息。"""

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
        # 文件缺失时返回空内容，避免数据库记录可查但 API 直接崩溃。
        content = path.read_text(encoding="utf-8") if path.exists() else ""
        return ProjectDocumentRecord(
            project_id=project_id,
            doc_id=int(row["doc_id"]),
            doc_role=doc_role,
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
        """更新 Project 模块文档，并执行乐观版本校验。"""

        document = self.get_document(project_id, doc_role)
        if base_version is not None and base_version != document.version:
            raise ProjectDocumentVersionConflictError("Project document conflict.")

        now = utc_now()
        document.path.parent.mkdir(parents=True, exist_ok=True)
        document.path.write_text(content.rstrip() + "\n", encoding="utf-8")
        with self.connect() as conn:
            # 文件写入后同步刷新资产层的大小、hash 和更新时间。
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
        """确认目标 Paper 存在且未被软删除。"""

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
        """为新 Project 创建六个默认 Markdown 文档和资产关系。"""

        for role, file_name, content in PROJECT_DOCUMENTS:
            path = project_dir / file_name
            path.write_text(content, encoding="utf-8")
            # 每个 Markdown 模块都是独立资产，便于后续版本和关系追踪。
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
        """将 SQLite row 映射为不可变 ProjectRecord。"""

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
        """返回 Project 六模块文档角色到资产 ID 的映射。"""

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


def utc_now() -> str:
    """返回 ISO 格式的 UTC 时间字符串。"""

    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat()


def records_to_dicts(records: list[LinkedPaperRecord]) -> list[dict[str, Any]]:
    """将 Project-Paper 关联记录转换为 API 可序列化字典列表。"""

    return [asdict(record) for record in records]


def record_to_dict(record: ProjectRecord) -> dict[str, Any]:
    """将 ProjectRecord 转换为 API 返回字典。"""

    return {
        "project_id": record.project_id,
        "asset_id": record.asset_id,
        "name": record.name,
        "project_slug": record.project_slug,
        "status": record.status,
        "summary": record.summary,
        "owner": record.owner,
        "assets": record.assets,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }


def document_to_dict(record: ProjectDocumentRecord) -> dict[str, Any]:
    """将 ProjectDocumentRecord 转换为 API 返回字典。"""

    return {
        "project_id": record.project_id,
        "doc_id": record.doc_id,
        "doc_role": record.doc_role,
        "content": record.content,
        "version": record.version,
        "updated_at": record.updated_at,
    }
