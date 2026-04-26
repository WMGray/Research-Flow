"""Paper storage backed by SQLite and the local filesystem.

The repository lives in the shared core layer so both the API and worker
processes can reuse the same persistence logic.
"""

from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import shutil
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from core.assets import (
    create_asset,
    create_asset_link,
    path_hash,
    path_size,
    update_asset_from_path,
)
from core.config import get_settings
from core.schema import PAPER_SCHEMA_SQL
from core.services.paper_download.service import PaperDownloadService
from core.services.papers.models import (
    DocumentNotFoundError,
    DocumentRecord,
    DocumentVersionConflictError,
    DuplicatePaperError,
    JobCancelNotAllowedError,
    JobNotFoundError,
    JobRecord,
    PaperArtifactRecord,
    PaperNotFoundError,
    PaperPipelineRunRecord,
    PaperRecord,
    RefineParseInput,
    map_paper_update_values,
    paper_record_from_row,
    paper_sort_column,
    utc_now,
)
from core.services.papers.refine_runtime import refine_markdown
from core.services.papers.section_split_runtime import split_canonical_sections
from core.services.papers.summary_runtime import (
    generate_paper_note,
    merge_managed_note_blocks,
)
from core.services.pdf_parser import PDFParserService
from core.services.pdf_parser.models import PDFParserError
from core.storage import configured_data_root, configured_db_path


SCHEMA_SQL = PAPER_SCHEMA_SQL
FINAL_JOB_STATUSES = {"succeeded", "failed", "cancelled"}
CANONICAL_SECTION_ORDER: tuple[tuple[str, str], ...] = (
    ("related_work", "Related Work"),
    ("method", "Method"),
    ("experiment", "Experiment"),
    ("conclusion", "Conclusion"),
)
@dataclass(frozen=True, slots=True)
class RepositoryPaperDownloadRequest:
    source_url: str | None
    doi: str | None
    title: str | None
    year: str
    venue: str
    output_dir: str | None
    overwrite: bool | None


class PaperRepository:
    """Paper 资源、文档和动作任务的仓储实现。"""

    def __init__(
        self, db_path: Path | None = None, data_root: Path | None = None
    ) -> None:
        self.db_path = db_path or configured_db_path()
        self.data_root = data_root or configured_data_root()
        self.paper_root = self.data_root / "papers_api"
        self.initialize()

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.paper_root.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript(SCHEMA_SQL)

    def connect(self) -> sqlite3.Connection:
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
                    zotero_id, paper_stage, download_status, parse_status,
                    refine_status, review_status, note_status, category_id,
                    source_url, pdf_url, tags
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    "metadata_ready",
                    "pending",
                    "pending",
                    "pending",
                    "pending",
                    "empty",
                    values.get("category_id"),
                    values.get("source_url", ""),
                    values.get("pdf_url", ""),
                    json.dumps(values.get("tags", []), ensure_ascii=False),
                ),
            )
            self._create_default_documents(
                conn=conn,
                paper_id=asset_id,
                paper_dir=paper_dir,
                title=values["title"],
                now=now,
            )
            conn.commit()
        return self.get_paper(asset_id)

    def find_by_doi(self, doi: str) -> PaperRecord | None:
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
        where = ["ar.is_deleted = 0"]
        params: list[Any] = []

        if query.get("q"):
            where.append("(bp.title LIKE ? OR bp.doi LIKE ? OR bp.authors LIKE ?)")
            pattern = f"%{query['q']}%"
            params.extend([pattern, pattern, pattern])
        if query.get("category_id") is not None:
            where.append("bp.category_id = ?")
            params.append(query["category_id"])
        if query.get("paper_stage"):
            where.append("bp.paper_stage = ?")
            params.append(query["paper_stage"])
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
                conn.execute(
                    "UPDATE asset_registry SET display_name = ? WHERE asset_id = ?",
                    (values["title"], paper_id),
                )
            conn.commit()
        return self.get_paper(paper_id)

    def delete_paper(self, paper_id: int) -> None:
        self.get_paper(paper_id)
        now = utc_now()
        with self.connect() as conn:
            conn.execute(
                "UPDATE asset_registry SET is_deleted = 1, updated_at = ? WHERE asset_id = ?",
                (now, paper_id),
            )
            conn.execute(
                "UPDATE biz_paper SET paper_stage = 'error' WHERE asset_id = ?",
                (paper_id,),
            )
            conn.commit()

    def get_document(self, paper_id: int, doc_role: str) -> DocumentRecord:
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
        document = self.get_document(paper_id, doc_role)
        if base_version is not None and base_version != document.version:
            raise DocumentVersionConflictError("Document version conflict.")

        now = utc_now()
        normalized_content = content.rstrip() + "\n" if content.strip() else ""
        document.path.parent.mkdir(parents=True, exist_ok=True)
        document.path.write_text(normalized_content, encoding="utf-8")
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
                (now, paper_id, doc_role),
            )
            conn.execute(
                "UPDATE asset_registry SET updated_at = ? WHERE asset_id = ?",
                (now, paper_id),
            )
            if doc_role == "note":
                conn.execute(
                    """
                    UPDATE biz_paper
                    SET note_status = ?
                    WHERE asset_id = ?
                    """,
                    ("user_modified", paper_id),
                )
            conn.commit()
        return self.get_document(paper_id, doc_role)

    def run_download(self, paper_id: int) -> JobRecord:
        paper = self.get_paper(paper_id)
        pdf_path = self._pdf_path(paper_id)
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        download_mode = "existing_file" if pdf_path.exists() else "metadata_stub"
        download_payload: dict[str, Any] = {}
        warning: str | None = None

        local_pdf = self._resolve_local_pdf_reference(paper)
        if not pdf_path.exists() and local_pdf is not None:
            shutil.copy2(local_pdf, pdf_path)
            download_mode = "attached_local_pdf"

        if not pdf_path.exists() and self._network_download_enabled(paper):
            try:
                row, result = PaperDownloadService().download(
                    self._download_request_for_paper(paper)
                )
                download_payload = {
                    "resolution": self._jsonable_record(row),
                    "download": dict(result),
                }
                file_path = str(result.get("file_path") or "")
                source_path = Path(file_path)
                if (
                    str(result.get("status") or "") == "downloaded"
                    and file_path
                    and source_path.is_file()
                ):
                    shutil.copy2(source_path, pdf_path)
                    download_mode = "gpaper"
                else:
                    warning = str(result.get("detail") or "gPaper did not return a PDF file.")
            except Exception as exc:  # noqa: BLE001 - recorded in job result and dev fallback
                warning = str(exc)

        if not pdf_path.exists():
            if warning is None and (paper.pdf_url or paper.source_url or paper.doi):
                warning = "Network paper download is disabled; using metadata fallback PDF."
            self._write_metadata_pdf_stub(paper, pdf_path)

        now = utc_now()
        with self.connect() as conn:
            self._upsert_paper_artifact(
                conn=conn,
                paper_id=paper_id,
                artifact_key="source_pdf",
                artifact_type="pdf",
                stage="download",
                path=pdf_path,
                metadata={
                    "mode": download_mode,
                    "warning": warning or "",
                },
                now=now,
            )
            conn.execute(
                """
                UPDATE biz_paper
                SET paper_stage = ?, download_status = ?
                WHERE asset_id = ?
                """,
                ("downloaded", "succeeded", paper_id),
            )
            conn.execute(
                "UPDATE asset_registry SET updated_at = ? WHERE asset_id = ?",
                (now, paper_id),
            )
            conn.commit()
        return self._create_pipeline_job(
            paper_id=paper_id,
            job_type="paper_download",
            status="succeeded",
            progress=1.0,
            message="Prepared paper PDF for parsing.",
            result={
                "pdf_path": str(pdf_path),
                "download_mode": download_mode,
                "warning": warning,
                **download_payload,
            },
            stage="download",
            input_artifacts=[],
            output_artifacts=["source_pdf"],
            metrics={"file_size": path_size(pdf_path)},
        )

    def run_parse(
        self,
        paper_id: int,
        *,
        parser: str,
        force: bool,
    ) -> JobRecord:
        paper = self.get_paper(paper_id)
        raw_path = self._raw_markdown_path(paper_id)
        parse_mode = "existing_raw" if raw_path.exists() and not force else "metadata_fallback"
        parse_warning: str | None = None
        parsed_artifacts: dict[str, str] = {}

        if not raw_path.exists() or force:
            raw_content, parse_mode, parse_warning, parsed_artifacts = (
                self._extract_raw_markdown_for_paper(paper, parser)
            )
        else:
            raw_content = raw_path.read_text(encoding="utf-8")

        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(raw_content, encoding="utf-8")

        now = utc_now()
        with self.connect() as conn:
            self._upsert_paper_artifact(
                conn=conn,
                paper_id=paper_id,
                artifact_key="raw_markdown",
                artifact_type="markdown",
                stage="parse",
                path=raw_path,
                metadata={
                    "parser": parser,
                    "mode": parse_mode,
                    "warning": parse_warning or "",
                    "artifacts": parsed_artifacts,
                },
                now=now,
            )
            conn.execute(
                """
                UPDATE biz_paper
                SET paper_stage = ?, parse_status = ?, refine_status = ?
                WHERE asset_id = ?
                """,
                ("parsed", "succeeded", "pending", paper_id),
            )
            conn.execute(
                "UPDATE asset_registry SET updated_at = ? WHERE asset_id = ?",
                (now, paper_id),
            )
            conn.commit()
        return self._create_pipeline_job(
            paper_id=paper_id,
            job_type="paper_parse",
            status="succeeded",
            progress=1.0,
            message="Parsed paper into raw markdown.",
            result={
                "raw_path": str(raw_path),
                "parser": parser,
                "force": force,
                "parse_mode": parse_mode,
                "warning": parse_warning,
                "artifacts": parsed_artifacts,
            },
            stage="parse",
            input_artifacts=["source_pdf"] if self._pdf_path(paper_id).exists() else [],
            output_artifacts=["raw_markdown"],
            metrics={"raw_chars": len(raw_content)},
        )

    def run_refine_parse(self, paper_id: int, request: RefineParseInput) -> JobRecord:
        paper = self.get_paper(paper_id)
        raw_path = self._raw_markdown_path(paper_id)
        if not raw_path.exists():
            return self._create_pipeline_job(
                paper_id=paper_id,
                job_type="paper_refine_parse",
                status="failed",
                progress=1.0,
                message="Cannot refine before parse produces raw markdown.",
                error={
                    "code": "PAPER_RAW_MARKDOWN_MISSING",
                    "message": "Run /api/v1/papers/{paper_id}/parse before refine-parse.",
                    "details": {},
                },
                result={
                    "skill_key": request.skill_key,
                    "instruction_present": bool(request.instruction.strip()),
                },
                stage="refine",
                input_artifacts=["raw_markdown"],
                output_artifacts=[],
                metrics={},
            )

        refined_path = self.get_document(paper_id, "refined").path
        try:
            execution = refine_markdown(
                markdown_path=raw_path,
                output_path=refined_path,
                skill_key=request.skill_key,
                instruction=request.instruction,
                metadata={
                    "title": paper.title,
                    "authors": paper.authors,
                    "year": paper.year,
                    "venue": paper.venue,
                    "doi": paper.doi,
                },
            )
        except Exception as exc:  # noqa: BLE001 - surfaced as failed job payload
            now = utc_now()
            with self.connect() as conn:
                conn.execute(
                    """
                    UPDATE biz_paper
                    SET refine_status = ?
                    WHERE asset_id = ?
                    """,
                    ("failed", paper_id),
                )
                conn.execute(
                    "UPDATE asset_registry SET updated_at = ? WHERE asset_id = ?",
                    (now, paper_id),
                )
                conn.commit()
            return self._create_pipeline_job(
                paper_id=paper_id,
                job_type="paper_refine_parse",
                status="failed",
                progress=1.0,
                message="LLM refine-parse failed before execution completed.",
                error={
                    "code": "PAPER_REFINE_FAILED",
                    "message": str(exc),
                    "details": {},
                },
                result={
                    "skill_key": request.skill_key,
                    "instruction_present": bool(request.instruction.strip()),
                },
                stage="refine",
                input_artifacts=["raw_markdown"],
                output_artifacts=[],
                metrics={},
            )
        if not execution.refined:
            now = utc_now()
            with self.connect() as conn:
                conn.execute(
                    """
                    UPDATE biz_paper
                    SET refine_status = ?
                    WHERE asset_id = ?
                    """,
                    ("failed", paper_id),
                )
                conn.execute(
                    "UPDATE asset_registry SET updated_at = ? WHERE asset_id = ?",
                    (now, paper_id),
                )
                conn.commit()
            return self._create_pipeline_job(
                paper_id=paper_id,
                job_type="paper_refine_parse",
                status="failed",
                progress=1.0,
                message="LLM refine-parse failed.",
                error={
                    "code": "PAPER_REFINE_FAILED",
                    "message": execution.error or "LLM refine-parse failed.",
                    "details": {},
                },
                result={
                    "skill_key": execution.skill_key,
                    "template_key": execution.template_key,
                    "feature": execution.feature,
                    "artifact_dir": str(execution.artifact_dir),
                    "artifacts": execution.artifacts,
                    "verify_status": execution.verify_status,
                    "applied_patch_count": execution.applied_patch_count,
                    "rejected_patch_count": execution.rejected_patch_count,
                    "deterministic_operation_count": execution.deterministic_operation_count,
                    "instruction_present": bool(request.instruction.strip()),
                },
                stage="refine",
                input_artifacts=["raw_markdown"],
                output_artifacts=list(execution.artifacts),
                metrics={
                    "verify_status": execution.verify_status,
                    "applied_patch_count": execution.applied_patch_count,
                    "rejected_patch_count": execution.rejected_patch_count,
                    "deterministic_operation_count": execution.deterministic_operation_count,
                },
            )

        refined_content = refined_path.read_text(encoding="utf-8")
        self._replace_document(paper_id, "refined", refined_content)
        now = utc_now()
        with self.connect() as conn:
            refined_doc = self.get_document(paper_id, "refined")
            self._upsert_existing_asset_artifact(
                conn=conn,
                paper_id=paper_id,
                asset_id=refined_doc.doc_id,
                artifact_key="refined_markdown",
                artifact_type="markdown",
                stage="refine",
                path=refined_doc.path,
                metadata={
                    "skill_key": execution.skill_key,
                    "verify_status": execution.verify_status,
                    "deterministic_operation_count": execution.deterministic_operation_count,
                },
                now=now,
            )
            for artifact_key, artifact_path in execution.artifacts.items():
                self._upsert_paper_artifact(
                    conn=conn,
                    paper_id=paper_id,
                    artifact_key=f"refine_{artifact_key}",
                    artifact_type="json",
                    stage="refine",
                    path=Path(artifact_path),
                    metadata={"skill_key": execution.skill_key},
                    now=now,
                )
            conn.execute(
                """
                UPDATE biz_paper
                SET paper_stage = ?, parse_status = ?, refine_status = ?
                WHERE asset_id = ?
                """,
                ("refined", "succeeded", "succeeded", paper_id),
            )
            conn.execute(
                "UPDATE asset_registry SET updated_at = ? WHERE asset_id = ?",
                (now, paper_id),
            )
            conn.commit()
        return self._create_pipeline_job(
            paper_id=paper_id,
            job_type="paper_refine_parse",
            status="succeeded",
            progress=1.0,
            message="Refined parsed markdown.",
            result={
                "refined_chars": len(refined_content),
                "refined_path": str(refined_path),
                "skill_key": execution.skill_key,
                "template_key": execution.template_key,
                "feature": execution.feature,
                "llm_run_id": execution.llm_run_id,
                "artifact_dir": str(execution.artifact_dir),
                "artifacts": execution.artifacts,
                "verify_status": execution.verify_status,
                "applied_patch_count": execution.applied_patch_count,
                "rejected_patch_count": execution.rejected_patch_count,
                "deterministic_operation_count": execution.deterministic_operation_count,
                "instruction_present": bool(request.instruction.strip()),
            },
            stage="refine",
            input_artifacts=["raw_markdown"],
            output_artifacts=[
                "refined_markdown",
                *[f"refine_{key}" for key in execution.artifacts],
            ],
            metrics={
                "refined_chars": len(refined_content),
                "verify_status": execution.verify_status,
                "applied_patch_count": execution.applied_patch_count,
                "rejected_patch_count": execution.rejected_patch_count,
                "deterministic_operation_count": execution.deterministic_operation_count,
            },
        )

    def submit_review(self, paper_id: int) -> PaperRecord:
        now = utc_now()
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE biz_paper
                SET paper_stage = ?, review_status = ?
                WHERE asset_id = ?
                """,
                ("refined", "waiting_review", paper_id),
            )
            conn.execute(
                "UPDATE asset_registry SET updated_at = ? WHERE asset_id = ?",
                (now, paper_id),
            )
            conn.commit()
        return self.get_paper(paper_id)

    def confirm_review(self, paper_id: int) -> PaperRecord:
        now = utc_now()
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE biz_paper
                SET paper_stage = ?, review_status = ?
                WHERE asset_id = ?
                """,
                ("review_confirmed", "confirmed", paper_id),
            )
            conn.execute(
                "UPDATE asset_registry SET updated_at = ? WHERE asset_id = ?",
                (now, paper_id),
            )
            conn.commit()
        return self.get_paper(paper_id)

    def run_split_sections(self, paper_id: int) -> JobRecord:
        paper = self.get_paper(paper_id)
        if paper.refine_status != "succeeded":
            return self._create_pipeline_job(
                paper_id=paper_id,
                job_type="paper_split_sections",
                status="failed",
                progress=1.0,
                message="Cannot split sections before refine-parse succeeds.",
                error={
                    "code": "PAPER_REFINED_MARKDOWN_MISSING",
                    "message": "Run /api/v1/papers/{paper_id}/refine-parse before split-sections.",
                    "details": {},
                },
                stage="split",
                input_artifacts=["refined_markdown"],
                output_artifacts=[],
                metrics={},
            )

        refined_content = self.get_document(paper_id, "refined").content
        section_records, split_report = self._write_sections_from_content(
            paper_id,
            refined_content,
        )
        split_report_path = self._sections_dir(paper_id) / "split_report.json"
        now = utc_now()
        with self.connect() as conn:
            for record in section_records:
                section_key = str(record["section_key"])
                self._upsert_paper_artifact(
                    conn=conn,
                    paper_id=paper_id,
                    artifact_key=f"section_{section_key}",
                    artifact_type="markdown",
                    stage="split",
                    path=self._sections_dir(paper_id) / f"{section_key}.md",
                    metadata={
                        "title": str(record["title"]),
                        "char_count": int(record["char_count"]),
                    },
                    now=now,
                )
            if split_report_path.exists():
                self._upsert_paper_artifact(
                    conn=conn,
                    paper_id=paper_id,
                    artifact_key="section_split_report",
                    artifact_type="json",
                    stage="split",
                    path=split_report_path,
                    metadata={
                        "strategy": split_report.get("strategy"),
                        "used_llm": split_report.get("used_llm"),
                    },
                    now=now,
                )
            conn.execute(
                """
                UPDATE biz_paper
                SET paper_stage = ?
                WHERE asset_id = ?
                """,
                ("sectioned", paper_id),
            )
            conn.execute(
                "UPDATE asset_registry SET updated_at = ? WHERE asset_id = ?",
                (now, paper_id),
            )
            conn.commit()
        section_keys = [record["section_key"] for record in section_records]
        return self._create_pipeline_job(
            paper_id=paper_id,
            job_type="paper_split_sections",
            status="succeeded",
            progress=1.0,
            message="Generated canonical paper sections.",
            result={"sections": section_keys},
            stage="split",
            input_artifacts=["refined_markdown"],
            output_artifacts=[f"section_{key}" for key in section_keys] + ["section_split_report"],
            metrics={
                "section_count": len(section_records),
                "split_strategy": split_report.get("strategy"),
                "used_llm": split_report.get("used_llm"),
            },
        )

    def run_generate_note(self, paper_id: int) -> JobRecord:
        paper = self.get_paper(paper_id)
        sections = self.list_sections(paper_id)
        if not sections:
            return self._create_pipeline_job(
                paper_id=paper_id,
                job_type="paper_generate_note",
                status="failed",
                progress=1.0,
                message="Cannot generate note before canonical sections exist.",
                error={
                    "code": "PAPER_SECTIONS_MISSING",
                    "message": "Run /api/v1/papers/{paper_id}/split-sections before generate-note.",
                    "details": {},
                },
                stage="summarize",
                input_artifacts=[],
                output_artifacts=[],
                metrics={},
            )
        if paper.note_status == "conflict_pending":
            return self._create_pipeline_job(
                paper_id=paper_id,
                job_type="paper_generate_note",
                status="failed",
                progress=1.0,
                message="Cannot overwrite a note with pending merge conflicts.",
                error={
                    "code": "PAPER_NOTE_CONFLICT_PENDING",
                    "message": "Resolve note conflicts before regenerating managed blocks.",
                    "details": {},
                },
                stage="summarize",
                input_artifacts=[
                    f"section_{section['section_key']}" for section in sections
                ],
                output_artifacts=[],
                metrics={"section_count": len(sections)},
            )

        existing_note = self.get_document(paper_id, "note").content
        note_result = generate_paper_note(paper=paper, sections=sections)
        note_content = note_result.content
        next_note_status = "clean_generated"
        if paper.note_status in {"user_modified", "merged"}:
            note_content = merge_managed_note_blocks(
                existing=existing_note,
                generated=note_result.content,
            )
            next_note_status = "merged"

        self._replace_document(paper_id, "note", note_content)
        now = utc_now()
        with self.connect() as conn:
            note_doc = self.get_document(paper_id, "note")
            self._upsert_existing_asset_artifact(
                conn=conn,
                paper_id=paper_id,
                asset_id=note_doc.doc_id,
                artifact_key="note_markdown",
                artifact_type="markdown",
                stage="summarize",
                path=note_doc.path,
                metadata={
                    "summary_source": note_result.source,
                    "template_key": note_result.template_key,
                    "feature": note_result.feature,
                    "merge_policy": next_note_status,
                },
                now=now,
            )
            conn.execute(
                """
                UPDATE biz_paper
                SET paper_stage = ?, note_status = ?
                WHERE asset_id = ?
                """,
                ("noted", next_note_status, paper_id),
            )
            conn.execute(
                "UPDATE asset_registry SET updated_at = ? WHERE asset_id = ?",
                (now, paper_id),
            )
            conn.commit()
        return self._create_pipeline_job(
            paper_id=paper_id,
            job_type="paper_generate_note",
            status="succeeded",
            progress=1.0,
            message="Generated paper note.md from canonical sections.",
            result={
                "managed_blocks": note_result.block_count,
                "summary_source": note_result.source,
                "template_key": note_result.template_key,
                "feature": note_result.feature,
                "llm_run_id": note_result.llm_run_id,
                "merge_policy": next_note_status,
            },
            stage="summarize",
            input_artifacts=[
                f"section_{section['section_key']}" for section in sections
            ],
            output_artifacts=["note_markdown"],
            metrics={
                "managed_blocks": note_result.block_count,
                "section_count": len(sections),
            },
        )

    def run_extract_knowledge(self, paper_id: int) -> JobRecord:
        note = self.get_document(paper_id, "note").content
        output_path = self._paper_dir(paper_id) / "extracted" / "knowledge.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "paper_id": paper_id,
            "items": [],
            "summary": note[:200],
        }
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        now = utc_now()
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE biz_paper
                SET paper_stage = ?
                WHERE asset_id = ?
                """,
                ("knowledge_extracted", paper_id),
            )
            conn.execute(
                "UPDATE asset_registry SET updated_at = ? WHERE asset_id = ?",
                (now, paper_id),
            )
            conn.commit()
        return self._create_job(
            paper_id=paper_id,
            job_type="paper_extract_knowledge",
            status="succeeded",
            progress=1.0,
            message="Generated local knowledge extraction placeholder.",
            result={"output_path": str(output_path), "item_count": 0},
        )

    def run_extract_datasets(self, paper_id: int) -> JobRecord:
        sections = self.list_sections(paper_id)
        output_path = self._paper_dir(paper_id) / "extracted" / "datasets.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "paper_id": paper_id,
            "items": [],
            "section_count": len(sections),
        }
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        now = utc_now()
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE biz_paper
                SET paper_stage = ?
                WHERE asset_id = ?
                """,
                ("dataset_extracted", paper_id),
            )
            conn.execute(
                "UPDATE asset_registry SET updated_at = ? WHERE asset_id = ?",
                (now, paper_id),
            )
            conn.commit()
        return self._create_job(
            paper_id=paper_id,
            job_type="paper_extract_datasets",
            status="succeeded",
            progress=1.0,
            message="Generated local dataset extraction placeholder.",
            result={"output_path": str(output_path), "item_count": 0},
        )

    def get_parsed_content(self, paper_id: int) -> dict[str, Any]:
        paper = self.get_paper(paper_id)
        raw_path = self._raw_markdown_path(paper_id)
        refined = self.get_document(paper_id, "refined")
        raw_content = raw_path.read_text(encoding="utf-8") if raw_path.exists() else ""
        refined_content = refined.content
        content = (
            refined_content
            if paper.refine_status == "succeeded" and refined_content.strip()
            else raw_content
        )
        return {
            "paper_id": paper_id,
            "page_count": max(1, content.count("\n#")),
            "char_count": len(content),
            "excerpt": content[:1200],
            "sections": self.list_sections(paper_id),
            "artifacts": {
                "note": self.get_document(paper_id, "note").version,
                "refined": refined.version,
                "has_raw": int(raw_path.exists()),
            },
        }

    def list_sections(self, paper_id: int) -> list[dict[str, Any]]:
        self.get_paper(paper_id)
        section_dir = self._sections_dir(paper_id)
        if not section_dir.exists():
            return []

        records: list[dict[str, Any]] = []
        for section_key, title in CANONICAL_SECTION_ORDER:
            path = section_dir / f"{section_key}.md"
            if not path.exists():
                continue
            content = path.read_text(encoding="utf-8")
            records.append(
                {
                    "section_key": section_key,
                    "title": title,
                    "content": content,
                    "char_count": len(content),
                }
            )
        return records

    def get_job(self, job_id: str) -> JobRecord:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
        if row is None:
            raise JobNotFoundError(f"Job not found: {job_id}")
        return self._job_from_row(row)

    def list_jobs(self, query: dict[str, Any]) -> tuple[list[JobRecord], int]:
        where = ["1 = 1"]
        params: list[Any] = []

        if query.get("resource_type"):
            where.append("resource_type = ?")
            params.append(query["resource_type"])
        if query.get("resource_id") is not None:
            where.append("resource_id = ?")
            params.append(query["resource_id"])
        if query.get("status"):
            where.append("status = ?")
            params.append(query["status"])

        where_sql = " AND ".join(where)
        page = int(query.get("page", 1))
        page_size = int(query.get("page_size", 20))
        offset = (page - 1) * page_size

        with self.connect() as conn:
            total = int(
                conn.execute(
                    f"SELECT COUNT(*) FROM jobs WHERE {where_sql}",
                    params,
                ).fetchone()[0]
            )
            rows = conn.execute(
                f"""
                SELECT *
                FROM jobs
                WHERE {where_sql}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                [*params, page_size, offset],
            ).fetchall()
        return [self._job_from_row(row) for row in rows], total

    def list_artifacts(self, paper_id: int) -> list[PaperArtifactRecord]:
        self.get_paper(paper_id)
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM biz_paper_artifact
                WHERE paper_id = ?
                ORDER BY stage ASC, artifact_key ASC
                """,
                (paper_id,),
            ).fetchall()
        return [self._artifact_from_row(row) for row in rows]

    def list_pipeline_runs(self, paper_id: int) -> list[PaperPipelineRunRecord]:
        self.get_paper(paper_id)
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM biz_paper_pipeline_run
                WHERE paper_id = ?
                ORDER BY created_at ASC
                """,
                (paper_id,),
            ).fetchall()
        return [self._pipeline_run_from_row(row) for row in rows]

    def cancel_job(self, job_id: str) -> JobRecord:
        job = self.get_job(job_id)
        if job.status in FINAL_JOB_STATUSES:
            raise JobCancelNotAllowedError(
                f"Job {job_id} cannot be cancelled from status {job.status}."
            )

        now = utc_now()
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE jobs
                SET status = ?, message = ?, updated_at = ?
                WHERE job_id = ?
                """,
                ("cancelled", "Cancelled by user.", now, job_id),
            )
            conn.commit()
        return self.get_job(job_id)

    def _create_default_documents(
        self,
        *,
        conn: sqlite3.Connection,
        paper_id: int,
        paper_dir: Path,
        title: str,
        now: str,
    ) -> None:
        defaults = {
            "note": ("note.md", f"# {title}\n"),
            "refined": (
                "parsed/refined.md",
                f"# {title}\n\n## Refined Parse\n\nPending parse.\n",
            ),
        }
        for role, (relative_path, content) in defaults.items():
            path = paper_dir / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            doc_id = create_asset(
                conn,
                storage_path=path,
                display_name=Path(relative_path).name,
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
                (
                    paper_id,
                    doc_id,
                    Path(relative_path).name,
                    str(path),
                    role,
                    1,
                    now,
                    now,
                ),
            )
            self._upsert_existing_asset_artifact(
                conn=conn,
                paper_id=paper_id,
                asset_id=doc_id,
                artifact_key="note_markdown" if role == "note" else "refined_markdown",
                artifact_type="markdown",
                stage="create",
                path=path,
                metadata={"doc_role": role},
                now=now,
            )

    def _paper_from_row(self, row: sqlite3.Row) -> PaperRecord:
        return paper_record_from_row(row, self._asset_map(int(row["asset_id"])))

    def _asset_map(self, paper_id: int) -> dict[str, int]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT doc_id, doc_role
                FROM biz_doc_layout
                WHERE parent_id = ?
                """,
                (paper_id,),
            ).fetchall()
        return {str(row["doc_role"]): int(row["doc_id"]) for row in rows}

    def _job_from_row(self, row: sqlite3.Row) -> JobRecord:
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

    def _artifact_from_row(self, row: sqlite3.Row) -> PaperArtifactRecord:
        return PaperArtifactRecord(
            artifact_id=int(row["artifact_id"]),
            paper_id=int(row["paper_id"]),
            asset_id=int(row["asset_id"]),
            artifact_key=str(row["artifact_key"]),
            artifact_type=str(row["artifact_type"]),
            stage=str(row["stage"]),
            storage_path=str(row["storage_path"]),
            content_hash=str(row["content_hash"]),
            file_size=int(row["file_size"]),
            version=int(row["version"]),
            metadata=json.loads(row["metadata"] or "{}"),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    def _pipeline_run_from_row(self, row: sqlite3.Row) -> PaperPipelineRunRecord:
        return PaperPipelineRunRecord(
            run_id=str(row["run_id"]),
            paper_id=int(row["paper_id"]),
            job_id=None if row["job_id"] is None else str(row["job_id"]),
            stage=str(row["stage"]),
            status=str(row["status"]),
            input_artifacts=json.loads(row["input_artifacts"] or "[]"),
            output_artifacts=json.loads(row["output_artifacts"] or "[]"),
            metrics=json.loads(row["metrics"] or "{}"),
            error=json.loads(row["error"]) if row["error"] else None,
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    def _paper_dir(self, paper_id: int) -> Path:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT pi.storage_path
                FROM asset_registry ar
                JOIN physical_item pi ON pi.item_id = ar.item_id
                WHERE ar.asset_id = ?
                """,
                (paper_id,),
            ).fetchone()
        if row is None:
            raise PaperNotFoundError(f"Paper not found: {paper_id}")
        return Path(str(row["storage_path"]))

    def _raw_markdown_path(self, paper_id: int) -> Path:
        return self._paper_dir(paper_id) / "parsed" / "raw.md"

    def _pdf_path(self, paper_id: int) -> Path:
        return self._paper_dir(paper_id) / "paper.pdf"

    def _sections_dir(self, paper_id: int) -> Path:
        return self._paper_dir(paper_id) / "parsed" / "sections"

    def _download_request_for_paper(
        self, paper: PaperRecord
    ) -> RepositoryPaperDownloadRequest:
        source_url = paper.pdf_url or paper.source_url or None
        return RepositoryPaperDownloadRequest(
            source_url=source_url,
            doi=paper.doi or None,
            title=paper.title,
            year="" if paper.year is None else str(paper.year),
            venue=paper.venue,
            output_dir=f"paper_api_{paper.paper_id}",
            overwrite=True,
        )

    def _network_download_enabled(self, paper: PaperRecord) -> bool:
        if not (paper.pdf_url or paper.source_url or paper.doi):
            return False
        return os.getenv("RFLOW_ENABLE_NETWORK_PAPER_DOWNLOAD", "").lower() in {
            "1",
            "true",
            "yes",
        }

    def _resolve_local_pdf_reference(self, paper: PaperRecord) -> Path | None:
        for value in (paper.pdf_url, paper.source_url):
            if not value:
                continue
            normalized = value.removeprefix("file://")
            candidate = Path(normalized).expanduser()
            if not candidate.is_absolute():
                candidate = (self._paper_dir(paper.paper_id) / normalized).resolve()
            if candidate.is_file() and candidate.suffix.lower() == ".pdf":
                return candidate
        return None

    def _write_metadata_pdf_stub(self, paper: PaperRecord, pdf_path: Path) -> None:
        pdf_path.write_bytes(
            (
                "%PDF-1.4\n"
                "% Research-Flow metadata fallback PDF\n"
                f"% Title: {paper.title}\n"
                f"% DOI: {paper.doi or 'N/A'}\n"
            ).encode("utf-8")
        )

    def _extract_raw_markdown_for_paper(
        self, paper: PaperRecord, parser: str
    ) -> tuple[str, str, str | None, dict[str, str]]:
        paper_id = paper.paper_id
        raw_candidates = self._local_mineru_markdown_candidates(paper_id)
        for candidate in raw_candidates:
            if candidate.exists():
                return (
                    candidate.read_text(encoding="utf-8"),
                    "existing_mineru_markdown",
                    None,
                    {"source_markdown_path": str(candidate)},
                )

        pdf_path = self._pdf_path(paper_id)
        if pdf_path.exists() and get_settings().mineru.api_token:
            try:
                bundle = asyncio.run(
                    PDFParserService(get_settings()).extract_raw_markdown(
                        pdf_path,
                        artifact_dir=self._paper_dir(paper_id) / "parsed" / "mineru",
                    )
                )
                return (
                    bundle.markdown_path.read_text(encoding="utf-8"),
                    "mineru",
                    None,
                    {
                        "mineru_markdown_path": str(bundle.markdown_path),
                        "mineru_image_dir": str(bundle.image_dir),
                        "mineru_content_list_path": ""
                        if bundle.content_list_path is None
                        else str(bundle.content_list_path),
                    },
                )
            except PDFParserError as exc:
                return (
                    self._build_raw_markdown(paper, parser),
                    "metadata_fallback",
                    f"{exc.error_code}: {exc.message}",
                    {"pdf_path": str(pdf_path)},
                )
            except Exception as exc:  # noqa: BLE001 - external MinerU/network failures fail open
                return (
                    self._build_raw_markdown(paper, parser),
                    "metadata_fallback",
                    f"MINERU_EXTERNAL_FAILURE: {exc}",
                    {"pdf_path": str(pdf_path)},
                )

        return (
            self._build_raw_markdown(paper, parser),
            "metadata_fallback",
            "MinerU input markdown or API token is not available.",
            {"pdf_path": str(pdf_path) if pdf_path.exists() else ""},
        )

    def _local_mineru_markdown_candidates(self, paper_id: int) -> list[Path]:
        paper_dir = self._paper_dir(paper_id)
        return [
            paper_dir / "parsed" / "mineru" / "full.md",
            paper_dir / "mineru" / "full.md",
            paper_dir / "parsed" / "full.md",
            paper_dir / "full.md",
        ]

    def _upsert_paper_artifact(
        self,
        *,
        conn: sqlite3.Connection,
        paper_id: int,
        artifact_key: str,
        artifact_type: str,
        stage: str,
        path: Path,
        metadata: dict[str, Any],
        now: str,
    ) -> int:
        row = conn.execute(
            """
            SELECT artifact_id, asset_id
            FROM biz_paper_artifact
            WHERE paper_id = ? AND artifact_key = ?
            """,
            (paper_id, artifact_key),
        ).fetchone()
        if row is None:
            asset_id = create_asset(
                conn,
                storage_path=path,
                display_name=path.name,
                asset_type=artifact_type,
                now=now,
            )
            create_asset_link(
                conn,
                source_id=paper_id,
                target_id=asset_id,
                relation_type="HAS_ARTIFACT",
            )
            cursor = conn.execute(
                """
                INSERT INTO biz_paper_artifact (
                    paper_id, asset_id, artifact_key, artifact_type, stage,
                    storage_path, content_hash, file_size, version, metadata,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    paper_id,
                    asset_id,
                    artifact_key,
                    artifact_type,
                    stage,
                    str(path),
                    path_hash(path),
                    path_size(path),
                    1,
                    json.dumps(metadata, ensure_ascii=False),
                    now,
                    now,
                ),
            )
            return int(cursor.lastrowid)

        asset_id = int(row["asset_id"])
        update_asset_from_path(conn, asset_id=asset_id, storage_path=path, now=now)
        conn.execute(
            """
            UPDATE biz_paper_artifact
            SET artifact_type = ?, stage = ?, storage_path = ?, content_hash = ?,
                file_size = ?, version = version + 1, metadata = ?, updated_at = ?
            WHERE artifact_id = ?
            """,
            (
                artifact_type,
                stage,
                str(path),
                path_hash(path),
                path_size(path),
                json.dumps(metadata, ensure_ascii=False),
                now,
                int(row["artifact_id"]),
            ),
        )
        return int(row["artifact_id"])

    def _upsert_existing_asset_artifact(
        self,
        *,
        conn: sqlite3.Connection,
        paper_id: int,
        asset_id: int,
        artifact_key: str,
        artifact_type: str,
        stage: str,
        path: Path,
        metadata: dict[str, Any],
        now: str,
    ) -> int:
        row = conn.execute(
            """
            SELECT artifact_id
            FROM biz_paper_artifact
            WHERE paper_id = ? AND artifact_key = ?
            """,
            (paper_id, artifact_key),
        ).fetchone()
        if row is None:
            cursor = conn.execute(
                """
                INSERT INTO biz_paper_artifact (
                    paper_id, asset_id, artifact_key, artifact_type, stage,
                    storage_path, content_hash, file_size, version, metadata,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    paper_id,
                    asset_id,
                    artifact_key,
                    artifact_type,
                    stage,
                    str(path),
                    path_hash(path),
                    path_size(path),
                    1,
                    json.dumps(metadata, ensure_ascii=False),
                    now,
                    now,
                ),
            )
            return int(cursor.lastrowid)

        conn.execute(
            """
            UPDATE biz_paper_artifact
            SET asset_id = ?, artifact_type = ?, stage = ?, storage_path = ?,
                content_hash = ?, file_size = ?, version = version + 1,
                metadata = ?, updated_at = ?
            WHERE artifact_id = ?
            """,
            (
                asset_id,
                artifact_type,
                stage,
                str(path),
                path_hash(path),
                path_size(path),
                json.dumps(metadata, ensure_ascii=False),
                now,
                int(row["artifact_id"]),
            ),
        )
        return int(row["artifact_id"])

    def _replace_document(self, paper_id: int, doc_role: str, content: str) -> None:
        document = self.get_document(paper_id, doc_role)
        now = utc_now()
        normalized_content = content.rstrip() + "\n" if content.strip() else ""
        document.path.parent.mkdir(parents=True, exist_ok=True)
        document.path.write_text(normalized_content, encoding="utf-8")
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
                (now, paper_id, doc_role),
            )
            conn.execute(
                "UPDATE asset_registry SET updated_at = ? WHERE asset_id = ?",
                (now, paper_id),
            )
            conn.commit()

    def _create_job(
        self,
        *,
        paper_id: int,
        job_type: str,
        status: str,
        progress: float,
        message: str,
        result: dict[str, Any] | None = None,
        error: dict[str, Any] | None = None,
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
                    "paper",
                    paper_id,
                    json.dumps(result, ensure_ascii=False) if result is not None else None,
                    json.dumps(error, ensure_ascii=False) if error is not None else None,
                    now,
                    now,
                ),
            )
            conn.commit()
        return self.get_job(job_id)

    def _create_pipeline_job(
        self,
        *,
        paper_id: int,
        job_type: str,
        status: str,
        progress: float,
        message: str,
        stage: str,
        input_artifacts: list[str],
        output_artifacts: list[str],
        metrics: dict[str, Any],
        result: dict[str, Any] | None = None,
        error: dict[str, Any] | None = None,
    ) -> JobRecord:
        job = self._create_job(
            paper_id=paper_id,
            job_type=job_type,
            status=status,
            progress=progress,
            message=message,
            result=result,
            error=error,
        )
        self._record_pipeline_run(
            paper_id=paper_id,
            job_id=job.job_id,
            stage=stage,
            status=status,
            input_artifacts=input_artifacts,
            output_artifacts=output_artifacts,
            metrics=metrics,
            error=error,
        )
        return job

    def _record_pipeline_run(
        self,
        *,
        paper_id: int,
        job_id: str,
        stage: str,
        status: str,
        input_artifacts: list[str],
        output_artifacts: list[str],
        metrics: dict[str, Any],
        error: dict[str, Any] | None,
    ) -> None:
        now = utc_now()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO biz_paper_pipeline_run (
                    run_id, paper_id, job_id, stage, status, input_artifacts,
                    output_artifacts, metrics, error, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"run_{uuid4().hex}",
                    paper_id,
                    job_id,
                    stage,
                    status,
                    json.dumps(input_artifacts, ensure_ascii=False),
                    json.dumps(output_artifacts, ensure_ascii=False),
                    json.dumps(metrics, ensure_ascii=False),
                    json.dumps(error, ensure_ascii=False) if error is not None else None,
                    now,
                    now,
                ),
            )
            conn.commit()

    def _jsonable_record(self, value: Any) -> dict[str, Any]:
        if is_dataclass(value):
            return asdict(value)
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        if hasattr(value, "__dict__"):
            return dict(value.__dict__)
        return {"value": str(value)}

    def _build_raw_markdown(self, paper: PaperRecord, parser: str) -> str:
        return (
            f"# {paper.title}\n\n"
            f"- Parser: {parser}\n"
            f"- DOI: {paper.doi or 'N/A'}\n"
            f"- Venue: {paper.venue or 'N/A'}\n"
            f"- Year: {paper.year or 'N/A'}\n\n"
            "## Parsed Body\n\n"
            "Research-Flow local placeholder parse output.\n"
        )

    def _write_sections_from_content(
        self, paper_id: int, content: str
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        split_result = split_canonical_sections(content)
        blocks = split_result.blocks
        section_dir = self._sections_dir(paper_id)
        section_dir.mkdir(parents=True, exist_ok=True)
        (section_dir / "split_report.json").write_text(
            json.dumps(split_result.report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        records: list[dict[str, Any]] = []
        for section_key, title in CANONICAL_SECTION_ORDER:
            section_content = blocks.get(section_key) or f"## {title}\n\nPending extraction.\n"
            path = section_dir / f"{section_key}.md"
            path.write_text(section_content.rstrip() + "\n", encoding="utf-8")
            records.append(
                {
                    "section_key": section_key,
                    "title": title,
                    "content": section_content.rstrip() + "\n",
                    "char_count": len(section_content),
                }
            )
        return records, split_result.report

    def _build_note_markdown(
        self, paper: PaperRecord, sections: list[dict[str, Any]]
    ) -> str:
        section_map = {section["section_key"]: section["content"].strip() for section in sections}
        block_map = {
            "research_question": section_map.get(
                "related_work", "Pending research question synthesis."
            ),
            "core_method": section_map.get("method", "Pending core method synthesis."),
            "main_contributions": section_map.get(
                "method", "Pending main contribution synthesis."
            ),
            "experiment_summary": section_map.get(
                "experiment", "Pending experiment summary synthesis."
            ),
            "limitations": section_map.get(
                "conclusion", "Pending limitation synthesis."
            ),
        }
        rendered_blocks = []
        for block_id, content in block_map.items():
            rendered_blocks.append(
                "\n".join(
                    [
                        f'<!-- RF:BLOCK_START id="{block_id}" managed="true" version="1" -->',
                        content,
                        f'<!-- RF:BLOCK_END id="{block_id}" -->',
                    ]
                )
            )
        return f"# {paper.title}\n\n" + "\n\n".join(rendered_blocks) + "\n"
