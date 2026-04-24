"""Paper 基础链路的 SQLite + 文件系统仓储。

本模块属于 core 共享能力层，不依赖 FastAPI app，可被 API 和 Worker 共同调用。
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any
from uuid import uuid4

from core.assets import (
    create_asset,
    create_asset_link,
    update_asset_from_path,
)
from core.storage import configured_data_root, configured_db_path
from core.services.papers.models import (
    DocumentNotFoundError,
    DocumentRecord,
    DocumentVersionConflictError,
    DuplicatePaperError,
    JobRecord,
    PaperNotFoundError,
    PaperRecord,
    map_paper_update_values,
    paper_record_from_row,
    paper_sort_column,
    utc_now,
)
from core.schema import PAPER_SCHEMA_SQL

# 兼容历史变量名，避免 PaperRepository 内部逻辑大范围改名。
SCHEMA_SQL = PAPER_SCHEMA_SQL


class PaperRepository:
    """Paper 资源、文档和 parse job 的仓储实现。"""

    def __init__(
        self, db_path: Path | None = None, data_root: Path | None = None
    ) -> None:
        """初始化数据库路径、数据根目录和 Paper 文件根目录。"""

        self.db_path = db_path or configured_db_path()
        self.data_root = data_root or configured_data_root()
        self.paper_root = self.data_root / "papers_api"
        self.initialize()

    def initialize(self) -> None:
        """创建 Paper 所需目录和表结构。"""

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.paper_root.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript(SCHEMA_SQL)

    def connect(self) -> sqlite3.Connection:
        """打开 SQLite 连接，并启用按列名读取。"""

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def create_paper(self, values: dict[str, Any]) -> PaperRecord:
        """创建 Paper 资产、业务记录和默认文档。"""

        doi = str(values.get("doi") or "")
        if doi and self.find_by_doi(doi) is not None:
            raise DuplicatePaperError(f"Paper with DOI already exists: {doi}")

        now = utc_now()
        with self.connect() as conn:
            paper_dir = self.paper_root / f"paper_{uuid4().hex}"
            paper_dir.mkdir(parents=True, exist_ok=True)
            # Paper 先注册为统一资产，再写入 biz_paper 领域表。
            asset_id = create_asset(
                conn,
                storage_path=paper_dir,
                display_name=values["title"],
                asset_type="Paper",
                now=now,
            )
            conn.execute(
                """
                INSERT INTO biz_paper (
                    asset_id, title, authors, pub_year, venue, venue_short, doi,
                    zotero_id, status, category_id, url, pdf_url, tags
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    asset_id,
                    values["title"],
                    json.dumps(values.get("authors", []), ensure_ascii=False),
                    values.get("year"),
                    values.get("venue", ""),
                    values.get("venue_short", ""),
                    doi,
                    values.get("zotero_id", ""),
                    values.get("status", "imported"),
                    values.get("category_id"),
                    values.get("url", ""),
                    values.get("pdf_url", ""),
                    json.dumps(values.get("tags", []), ensure_ascii=False),
                ),
            )
            self._create_default_documents(
                conn, asset_id, paper_dir, values["title"], now
            )
            conn.commit()
        return self.get_paper(asset_id)

    def find_by_doi(self, doi: str) -> PaperRecord | None:
        """按 DOI 查询未删除 Paper，用于重复检测。"""

        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT bp.*, ar.created_at, ar.updated_at, ar.is_deleted
                FROM biz_paper bp
                JOIN asset_registry ar ON ar.asset_id = bp.asset_id
                WHERE bp.doi = ? AND ar.is_deleted = 0
                LIMIT 1
                """,
                (doi,),
            ).fetchone()
        return self._paper_from_row(row) if row else None

    def get_paper(self, paper_id: int) -> PaperRecord:
        """根据 asset_id 查询单个未删除 Paper。"""

        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT bp.*, ar.created_at, ar.updated_at, ar.is_deleted
                FROM biz_paper bp
                JOIN asset_registry ar ON ar.asset_id = bp.asset_id
                WHERE bp.asset_id = ? AND ar.is_deleted = 0
                """,
                (paper_id,),
            ).fetchone()
        if row is None:
            raise PaperNotFoundError(f"Paper not found: {paper_id}")
        return self._paper_from_row(row)

    def list_papers(self, query: dict[str, Any]) -> tuple[list[PaperRecord], int]:
        """按查询条件分页列出 Paper。"""

        where = ["ar.is_deleted = 0"]
        params: list[Any] = []

        if query.get("q"):
            where.append("(bp.title LIKE ? OR bp.doi LIKE ? OR bp.authors LIKE ?)")
            pattern = f"%{query['q']}%"
            params.extend([pattern, pattern, pattern])
        if query.get("category_id") is not None:
            where.append("bp.category_id = ?")
            params.append(query["category_id"])
        if query.get("status"):
            where.append("bp.status = ?")
            params.append(query["status"])
        if query.get("year_from") is not None:
            where.append("bp.pub_year >= ?")
            params.append(query["year_from"])
        if query.get("year_to") is not None:
            where.append("bp.pub_year <= ?")
            params.append(query["year_to"])

        where_sql = " AND ".join(where)
        sort = paper_sort_column(query.get("sort", "updated_at"))
        order = "ASC" if query.get("order") == "asc" else "DESC"
        page = int(query.get("page", 1))
        page_size = int(query.get("page_size", 20))
        offset = (page - 1) * page_size

        with self.connect() as conn:
            # total 与 rows 使用同一 where 片段，保持分页统计一致。
            total = int(
                conn.execute(
                    f"""
                    SELECT COUNT(*)
                    FROM biz_paper bp
                    JOIN asset_registry ar ON ar.asset_id = bp.asset_id
                    WHERE {where_sql}
                    """,
                    params,
                ).fetchone()[0]
            )
            rows = conn.execute(
                f"""
                SELECT bp.*, ar.created_at, ar.updated_at, ar.is_deleted
                FROM biz_paper bp
                JOIN asset_registry ar ON ar.asset_id = bp.asset_id
                WHERE {where_sql}
                ORDER BY {sort} {order}
                LIMIT ? OFFSET ?
                """,
                [*params, page_size, offset],
            ).fetchall()
        return [self._paper_from_row(row) for row in rows], total

    def update_paper(self, paper_id: int, values: dict[str, Any]) -> PaperRecord:
        """更新 Paper 元数据，并同步资产层更新时间。"""

        self.get_paper(paper_id)
        if "doi" in values and values["doi"]:
            existing = self.find_by_doi(values["doi"])
            if existing is not None and existing.paper_id != paper_id:
                raise DuplicatePaperError(
                    f"Paper with DOI already exists: {values['doi']}"
                )

        mapped_values = map_paper_update_values(values)
        columns = [f"{key} = ?" for key in mapped_values]
        params = [*mapped_values.values(), paper_id]
        now = utc_now()

        with self.connect() as conn:
            if columns:
                conn.execute(
                    f"UPDATE biz_paper SET {', '.join(columns)} WHERE asset_id = ?",
                    params,
                )
            conn.execute(
                "UPDATE asset_registry SET updated_at = ? WHERE asset_id = ?",
                (now, paper_id),
            )
            if "title" in values:
                # 标题变更时同步更新资产展示名。
                conn.execute(
                    "UPDATE asset_registry SET display_name = ? WHERE asset_id = ?",
                    (values["title"], paper_id),
                )
            conn.commit()
        return self.get_paper(paper_id)

    def delete_paper(self, paper_id: int) -> None:
        """软删除 Paper，保留文件和历史关系。"""

        self.get_paper(paper_id)
        now = utc_now()
        with self.connect() as conn:
            conn.execute(
                "UPDATE asset_registry SET is_deleted = 1, updated_at = ? WHERE asset_id = ?",
                (now, paper_id),
            )
            conn.execute(
                "UPDATE biz_paper SET status = 'deleted' WHERE asset_id = ?",
                (paper_id,),
            )
            conn.commit()

    def get_document(self, paper_id: int, doc_role: str) -> DocumentRecord:
        """读取 Paper 指定角色文档及其版本信息。"""

        self.get_paper(paper_id)
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT *
                FROM biz_doc_layout
                WHERE parent_id = ? AND doc_role = ?
                """,
                (paper_id, doc_role),
            ).fetchone()
        if row is None:
            raise DocumentNotFoundError(f"Document not found: {paper_id}/{doc_role}")

        path = Path(row["doc_path"])
        # 文档文件缺失时返回空内容，让调用方能看到数据库记录仍存在。
        content = path.read_text(encoding="utf-8") if path.exists() else ""
        return DocumentRecord(
            paper_id=paper_id,
            doc_id=int(row["doc_id"]),
            doc_role=doc_role,
            path=path,
            content=content,
            version=int(row["version"]),
            updated_at=str(row["updated_at"]),
        )

    def update_document(
        self,
        paper_id: int,
        doc_role: str,
        content: str,
        base_version: int | None,
    ) -> DocumentRecord:
        """更新 Paper 文档，并执行乐观版本校验。"""

        document = self.get_document(paper_id, doc_role)
        if base_version is not None and base_version != document.version:
            raise DocumentVersionConflictError("Document version conflict.")

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
                (now, paper_id, doc_role),
            )
            conn.commit()
        return self.get_document(paper_id, doc_role)

    def create_parse_job(self, paper_id: int, message: str) -> JobRecord:
        """创建 Paper parse job，并把 Paper 状态推进到 parse_queued。"""

        self.update_paper(paper_id, {"status": "parse_queued"})
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
                    "paper_parse",
                    "queued",
                    0.0,
                    message,
                    "paper",
                    paper_id,
                    None,
                    None,
                    now,
                    now,
                ),
            )
            conn.commit()
        return self.get_job(job_id)

    def get_job(self, job_id: str) -> JobRecord:
        """根据 job_id 查询任务记录。"""

        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
        if row is None:
            raise PaperNotFoundError(f"Job not found: {job_id}")
        return JobRecord(
            job_id=str(row["job_id"]),
            type=str(row["type"]),
            status=str(row["status"]),
            progress=float(row["progress"]),
            message=str(row["message"]),
            resource_type=str(row["resource_type"]),
            resource_id=int(row["resource_id"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
            result=json.loads(row["result"]) if row["result"] else None,
            error=json.loads(row["error"]) if row["error"] else None,
        )

    def _create_default_documents(
        self,
        conn: sqlite3.Connection,
        paper_id: int,
        paper_dir: Path,
        title: str,
        now: str,
    ) -> None:
        """为新 Paper 初始化 LLM note 和 HUMAN note。"""

        defaults = {
            "llm": ("note.md", f"# {title}\n\n> 自动分析文档待生成。\n"),
            "human": ("HUMAN.md", f"# {title}\n\n## 人工笔记\n\n"),
        }
        for role, (file_name, content) in defaults.items():
            path = paper_dir / file_name
            path.write_text(content, encoding="utf-8")
            # 每个 Markdown 文档都作为独立资产挂接到 Paper。
            doc_id = create_asset(
                conn,
                storage_path=path,
                display_name=file_name,
                asset_type="Markdown",
                now=now,
            )
            create_asset_link(
                conn,
                source_id=paper_id,
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
                (paper_id, doc_id, file_name, str(path), role, 1, now, now),
            )

    def _paper_from_row(self, row: sqlite3.Row) -> PaperRecord:
        """将 SQLite row 映射为 PaperRecord。"""

        return paper_record_from_row(row, self._asset_map(int(row["asset_id"])))

    def _asset_map(self, paper_id: int) -> dict[str, int]:
        """返回 Paper 文档角色到资产 ID 的映射。"""

        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT doc_id, doc_role
                FROM biz_doc_layout
                WHERE parent_id = ?
                """,
                (paper_id,),
            ).fetchall()
        return {f"{row['doc_role']}_note": int(row["doc_id"]) for row in rows}
