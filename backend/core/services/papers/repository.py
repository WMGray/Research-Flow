"""Paper storage backed by SQLite and the local filesystem.

The repository lives in the shared core layer so both the API and worker
processes can reuse the same persistence logic.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sqlite3
import shutil
from dataclasses import asdict, dataclass, is_dataclass, replace
from pathlib import Path
from typing import Any
from uuid import uuid4

from core.assets import (
    create_asset,
    create_asset_link,
    hash_text,
    path_hash,
    path_size,
    update_asset_from_path,
)
from core.config import get_settings
from core.schema import PAPER_SCHEMA_SQL
from core.services.papers.download import PaperDownloadService
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
from core.services.papers.metadata import (
    authors_from_resolution,
    infer_ccf_rank,
    infer_sci_quartile,
)
from core.services.papers.refine import refine_markdown
from core.services.papers.split import (
    CANONICAL_SECTION_ORDER,
    split_canonical_sections,
    section_filename,
)
from core.services.papers.note import (
    extract_managed_blocks,
    generate_paper_note,
    merge_managed_note_blocks,
)
from core.services.papers.knowledge import extract_knowledge
from core.services.papers.parse import PDFParserService
from core.services.papers.parse.models import PDFParserError
from core.services.papers.parse.postprocess import process_mineru_markdown_artifacts
from core.services.resources import ResourceRepository
from core.storage import configured_data_root, configured_db_path


SCHEMA_SQL = PAPER_SCHEMA_SQL
FINAL_JOB_STATUSES = {"succeeded", "failed", "cancelled"}
KNOWN_DATASET_PATTERN = re.compile(
    r"\b("
    r"MMLU|ImageNet|COCO|CIFAR-10|CIFAR-100|GLUE|SuperGLUE|SQuAD|WMT|"
    r"WikiText|HumanEval|GSM8K|EPIC-KITCHENS-100|ScanNet|SUN RGB-D|S3DIS|"
    r"nuScenes|KITTI|ADE20K"
    r")\b",
    re.I,
)
GENERIC_DATASET_PATTERN = re.compile(
    r"\b([A-Z][A-Za-z0-9+\-]*(?:\s+[A-Z][A-Za-z0-9+\-]*){0,4}\s+"
    r"(?:dataset|benchmark|corpus|suite))\b",
    re.I,
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


@dataclass(frozen=True, slots=True)
class DatasetMention:
    name: str
    task_type: str
    data_domain: str
    evidence_text: str
    source_section: str


class PaperRepository:
    """Paper 资源、文档和动作任务的仓储实现。"""

    # ============================================================
    # Initialization
    # ============================================================

    def __init__(
        self, db_path: Path | None = None, data_root: Path | None = None
    ) -> None:
        self.db_path = db_path or configured_db_path()
        self.data_root = data_root or configured_data_root()
        self.paper_root = self.data_root / "Papers"
        self.initialize()

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.paper_root.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript(SCHEMA_SQL)
            self._migrate_schema(conn)
            conn.commit()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ============================================================
    # CRUD Operations
    # ============================================================

    def create_paper(self, values: dict[str, Any]) -> PaperRecord:
        """创建 Paper 资产、业务记录和默认文档。"""

        doi = str(values.get("doi") or "")
        if doi and self.find_by_doi(doi) is not None:
            raise DuplicatePaperError(f"Paper with DOI already exists: {doi}")

        now = utc_now()
        venue = str(values.get("venue", "") or "")
        venue_short = str(values.get("venue_short", "") or "")
        ccf_rank = str(values.get("ccf_rank", "") or "") or infer_ccf_rank(
            venue_short,
            venue,
        )
        sci_quartile = str(values.get("sci_quartile", "") or "") or infer_sci_quartile(
            venue_short,
            venue,
        )
        with self.connect() as conn:
            category_id = values.get("category_id")
            paper_slug = self._unique_paper_slug(conn, str(values["title"]))
            paper_dir = self._target_paper_dir_for_slug(conn, paper_slug, category_id)
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
                    asset_id, title, paper_slug, authors, abstract, pub_year,
                    venue, venue_short, ccf_rank, sci_quartile, doi, zotero_id, paper_stage,
                    download_status, parse_status, refine_status, review_status,
                    note_status, category_id, source_url, pdf_url, source_kind,
                    tags
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    asset_id,
                    values["title"],
                    paper_slug,
                    json.dumps(values.get("authors", []), ensure_ascii=False),
                    values.get("abstract", ""),
                    values.get("year"),
                    venue,
                    venue_short,
                    ccf_rank,
                    sci_quartile,
                    doi,
                    values.get("zotero_id", ""),
                    "metadata_ready",
                    "pending",
                    "pending",
                    "pending",
                    "pending",
                    "empty",
                    category_id,
                    values.get("source_url", ""),
                    values.get("pdf_url", ""),
                    values.get("source_kind", "manual"),
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
            self._write_metadata_json(conn, asset_id, now)
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
        paper = self.get_paper(paper_id)
        if "doi" in values and values["doi"]:
            existing = self.find_by_doi(values["doi"])
            if existing is not None and existing.paper_id != paper_id:
                raise DuplicatePaperError(
                    f"Paper with DOI already exists: {values['doi']}"
                )

        if ("venue" in values or "venue_short" in values) and "ccf_rank" not in values:
            inferred = infer_ccf_rank(
                str(values.get("venue_short", paper.venue_short) or ""),
                str(values.get("venue", paper.venue) or ""),
            )
            if inferred and not paper.ccf_rank:
                values["ccf_rank"] = inferred
        if ("venue" in values or "venue_short" in values) and "sci_quartile" not in values:
            inferred = infer_sci_quartile(
                str(values.get("venue_short", paper.venue_short) or ""),
                str(values.get("venue", paper.venue) or ""),
            )
            if inferred and not paper.sci_quartile:
                values["sci_quartile"] = inferred

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
            if "category_id" in values:
                self._relocate_paper_dir_for_category(conn, paper_id)
            conn.execute(
                "UPDATE asset_registry SET updated_at = ? WHERE asset_id = ?",
                (now, paper_id),
            )
            if "title" in values:
                conn.execute(
                    "UPDATE asset_registry SET display_name = ? WHERE asset_id = ?",
                    (values["title"], paper_id),
                )
            self._write_metadata_json(conn, paper_id, now)
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

    # ============================================================
    # Document Management
    # ============================================================

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

    def get_pdf_file_path(self, paper_id: int) -> Path:
        self.get_paper(paper_id)
        return self._pdf_path(paper_id)

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
                previous_managed_hashes = self._stored_managed_block_hashes(
                    conn,
                    paper_id,
                )
                note_status = self._note_status_after_user_edit(
                    conn=conn,
                    paper_id=paper_id,
                    content=normalized_content,
                )
                conn.execute(
                    """
                    UPDATE biz_paper
                    SET note_status = ?
                    WHERE asset_id = ?
                    """,
                    (note_status, paper_id),
                )
                self._upsert_note_state(
                    conn=conn,
                    paper_id=paper_id,
                    note_doc_id=document.doc_id,
                    note_status=note_status,
                    content=normalized_content,
                    now=now,
                    last_user_modified_at=now,
                    managed_block_hashes=(
                        previous_managed_hashes
                        if note_status == "conflict_pending"
                        else None
                    ),
                    conflict_reason=(
                        "Managed note blocks changed; resolve conflicts before regeneration."
                        if note_status == "conflict_pending"
                        else ""
                    ),
                )
            conn.commit()
        return self.get_document(paper_id, doc_role)

    # ============================================================
    # Pipeline Stages
    # ============================================================

    def run_download(self, paper_id: int) -> JobRecord:
        paper = self.get_paper(paper_id)
        pdf_path = self._pdf_path(paper_id)
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        download_mode = "existing_file" if pdf_path.exists() else "metadata_stub"
        download_payload: dict[str, Any] = {}
        metadata_updates: dict[str, Any] = {}
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
                metadata_updates = self._metadata_updates_from_resolution(paper, row)
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

        pdf_integrity = self._pdf_integrity_metadata(pdf_path)
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
                    **pdf_integrity,
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
            if metadata_updates:
                columns = [f"{key} = ?" for key in metadata_updates]
                conn.execute(
                    f"UPDATE biz_paper SET {', '.join(columns)} WHERE asset_id = ?",
                    [*metadata_updates.values(), paper_id],
                )
                if "title" in metadata_updates:
                    conn.execute(
                        "UPDATE asset_registry SET display_name = ? WHERE asset_id = ?",
                        (metadata_updates["title"], paper_id),
                    )
            conn.execute(
                "UPDATE asset_registry SET updated_at = ? WHERE asset_id = ?",
                (now, paper_id),
            )
            self._write_metadata_json(conn, paper_id, now)
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
                **pdf_integrity,
                **download_payload,
            },
            stage="download",
            input_artifacts=[],
            output_artifacts=["source_pdf"],
            metrics={
                "file_size": path_size(pdf_path),
                "is_real_pdf": pdf_integrity["is_real_pdf"],
            },
        )

    def _metadata_updates_from_resolution(
        self,
        paper: PaperRecord,
        resolution: object,
    ) -> dict[str, Any]:
        updates: dict[str, Any] = {}

        resolved_title = self._resolution_text(resolution, "title")
        if resolved_title and self._should_replace_title(paper.title, resolved_title):
            updates["title"] = resolved_title

        resolved_year = self._resolution_year(resolution)
        if resolved_year is not None and paper.year is None:
            updates["pub_year"] = resolved_year

        resolved_venue = self._resolution_text(resolution, "venue")
        if resolved_venue and not paper.venue:
            updates["venue"] = resolved_venue
        if resolved_venue and not paper.venue_short:
            updates["venue_short"] = resolved_venue

        if not paper.ccf_rank:
            ccf_rank = infer_ccf_rank(
                resolved_venue,
                paper.venue_short,
                paper.venue,
            )
            if ccf_rank:
                updates["ccf_rank"] = ccf_rank
        if not paper.sci_quartile:
            sci_quartile = infer_sci_quartile(
                resolved_venue,
                paper.venue_short,
                paper.venue,
            )
            if sci_quartile:
                updates["sci_quartile"] = sci_quartile

        resolved_authors = authors_from_resolution(resolution)
        if resolved_authors and not paper.authors:
            updates["authors"] = json.dumps(resolved_authors, ensure_ascii=False)

        resolved_doi = self._resolution_text(resolution, "doi")
        if resolved_doi and not paper.doi:
            updates["doi"] = resolved_doi

        resolved_landing_url = self._resolution_text(resolution, "landing_url")
        if resolved_landing_url and not paper.source_url:
            updates["source_url"] = resolved_landing_url

        resolved_pdf_url = (
            self._resolution_text(resolution, "pdf_url")
            or self._resolution_text(resolution, "final_url")
        )
        if resolved_pdf_url and not paper.pdf_url:
            updates["pdf_url"] = resolved_pdf_url

        return updates

    def _resolution_text(self, resolution: object, field_name: str) -> str:
        value = getattr(resolution, field_name, "")
        return str(value or "").strip()

    def _resolution_year(self, resolution: object) -> int | None:
        raw_year = self._resolution_text(resolution, "year")
        if not raw_year:
            return None
        try:
            return int(raw_year)
        except ValueError:
            return None

    def _should_replace_title(self, current_title: str, resolved_title: str) -> bool:
        current = current_title.strip()
        resolved = resolved_title.strip()
        if not resolved or resolved == current:
            return False
        return not current or self._looks_like_url(current)

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
        figure_dir = self._postprocessed_figure_dir(parsed_artifacts)
        figure_count = self._count_files(figure_dir) if figure_dir is not None else 0
        image_count = 0
        if figure_count == 0:
            image_count = self._sync_parse_images(
                raw_path=raw_path,
                parsed_artifacts=parsed_artifacts,
            )
        if image_count:
            parsed_artifacts = {
                **parsed_artifacts,
                "normalized_image_dir": str(raw_path.parent / "images"),
                "normalized_image_count": str(image_count),
            }

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
            if figure_count and figure_dir is not None:
                self._upsert_paper_artifact(
                    conn=conn,
                    paper_id=paper_id,
                    artifact_key="parse_figures",
                    artifact_type="directory",
                    stage="parse",
                    path=figure_dir,
                    metadata={"figure_count": figure_count},
                    now=now,
                )
            if image_count:
                self._upsert_paper_artifact(
                    conn=conn,
                    paper_id=paper_id,
                    artifact_key="parse_images",
                    artifact_type="directory",
                    stage="parse",
                    path=raw_path.parent / "images",
                    metadata={"image_count": image_count},
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
            output_artifacts=[
                "raw_markdown",
                *(["parse_figures"] if figure_count else []),
                *(["parse_images"] if image_count else []),
            ],
            metrics={
                "raw_chars": len(raw_content),
                "figure_count": figure_count,
                "image_count": image_count,
            },
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
                    "instruction_key": execution.instruction_key,
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
                "instruction_key": execution.instruction_key,
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
            self._write_metadata_json(conn, paper_id, now)
            conn.commit()
        return self.get_paper(paper_id)

    def create_confirm_pipeline_job(self, paper_id: int) -> JobRecord:
        self.get_paper(paper_id)
        return self._create_job(
            paper_id=paper_id,
            job_type="paper_confirm_pipeline",
            status="queued",
            progress=0.0,
            message="Confirm pipeline queued.",
        )

    def run_confirm_pipeline(
        self,
        paper_id: int,
        parent_job_id: str | None = None,
    ) -> JobRecord:
        parent_job = (
            self._finish_job(
                parent_job_id,
                status="running",
                progress=0.05,
                message="Confirm pipeline started.",
            )
            if parent_job_id
            else self._create_job(
                paper_id=paper_id,
                job_type="paper_confirm_pipeline",
                status="running",
                progress=0.05,
                message="Confirm pipeline started.",
            )
        )
        jobs: list[JobRecord] = []

        def fail(stage: str, job: JobRecord) -> JobRecord:
            jobs.append(job)
            return self._finish_job(
                parent_job.job_id,
                status="failed",
                progress=1.0,
                message=job.message,
                result={
                    "stage": stage,
                    "jobs": [asdict(record) for record in jobs],
                },
                error=job.error
                or {
                    "code": "PAPER_CONFIRM_PIPELINE_FAILED",
                    "message": job.message,
                    "details": {"stage": stage},
                },
            )

        try:
            self.confirm_review(paper_id)
            for stage, runner in (
                ("split", self.run_split_sections),
                ("summarize", self.run_generate_note),
                ("extract_knowledge", self.run_extract_knowledge),
                ("extract_datasets", self.run_extract_datasets),
            ):
                job = runner(paper_id)
                if job.status != "succeeded":
                    return fail(stage, job)
                jobs.append(job)
        except Exception as exc:  # noqa: BLE001 - recorded as parent job failure
            return self._finish_job(
                parent_job.job_id,
                status="failed",
                progress=1.0,
                message=str(exc),
                result={"jobs": [asdict(record) for record in jobs]},
                error={
                    "code": "PAPER_CONFIRM_PIPELINE_EXCEPTION",
                    "message": str(exc),
                    "details": {},
                },
            )

        return self._finish_job(
            parent_job.job_id,
            status="succeeded",
            progress=1.0,
            message="Confirmed review and completed paper extraction pipeline.",
            result={
                "paper_id": paper_id,
                "jobs": [asdict(record) for record in jobs],
                "paper": asdict(self.get_paper(paper_id)),
            },
        )

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
                    path=self._sections_dir(paper_id) / section_filename(section_key),
                    metadata={
                        "title": str(record["title"]),
                        "char_count": int(record["char_count"]),
                        "generated": bool(record.get("generated")),
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

        note_doc = self.get_document(paper_id, "note")
        existing_note = note_doc.content
        note_result = generate_paper_note(
            paper=paper,
            sections=sections,
            note_path=note_doc.path,
            image_base_dirs=self._note_image_base_dirs(paper_id),
        )
        note_content = note_result.content
        next_note_status = "clean_generated"
        merge_policy = "overwrite"
        if paper.note_status in {"user_modified", "merged"}:
            note_content = merge_managed_note_blocks(
                existing=existing_note,
                generated=note_result.content,
            )
            next_note_status = "merged"
            merge_policy = "merged"

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
                    "instruction_key": note_result.instruction_key,
                    "feature": note_result.feature,
                    "merge_policy": merge_policy,
                    "figure_count": note_result.figure_count,
                    "block_failures": list(note_result.block_failures),
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
            self._write_metadata_json(conn, paper_id, now)
            self._upsert_note_state(
                conn=conn,
                paper_id=paper_id,
                note_doc_id=note_doc.doc_id,
                note_status=next_note_status,
                content=note_content,
                now=now,
                last_generated_at=now,
                last_merge_policy=merge_policy,
                conflict_reason="",
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
                "instruction_key": note_result.instruction_key,
                "feature": note_result.feature,
                "llm_run_id": note_result.llm_run_id,
                "merge_policy": merge_policy,
                "figure_count": note_result.figure_count,
                "block_failures": list(note_result.block_failures),
            },
            stage="summarize",
            input_artifacts=[
                f"section_{section['section_key']}" for section in sections
            ],
            output_artifacts=["note_markdown"],
            metrics={
                "managed_blocks": note_result.block_count,
                "section_count": len(sections),
                "figure_count": note_result.figure_count,
            },
        )

    def run_extract_knowledge(self, paper_id: int) -> JobRecord:
        paper = self.get_paper(paper_id)
        note = self.get_document(paper_id, "note").content
        sections = self.list_sections(paper_id)
        resource_repository = ResourceRepository(
            db_path=self.db_path,
            data_root=self.data_root,
        )
        existing = resource_repository.list_knowledge_for_paper(paper_id)
        extraction_source = "existing_resource_links"
        skipped_reason = ""
        if existing:
            items = [
                {
                    "knowledge_id": record.resource_id,
                    "title": record.display_name,
                    "relation_type": record.relation_type,
                }
                for record in existing
            ]
        else:
            extraction = extract_knowledge(
                paper_title=paper.title,
                note=note,
                sections=sections,
            )
            extraction_source = extraction.source
            skipped_reason = extraction.skipped_reason
            items = []
            for item in extraction.items:
                record = resource_repository.create_knowledge(
                    {
                        "knowledge_type": item.knowledge_type,
                        "title": item.title,
                        "summary_zh": item.summary_zh,
                        "original_text_en": item.original_text_en,
                        "category_label": item.category_label,
                        "source_paper_asset_id": paper_id,
                        "source_section": item.source_section,
                        "source_locator": item.source_locator,
                        "evidence_text": item.evidence_text,
                        "confidence_score": item.confidence_score,
                        "review_status": "pending_review",
                        "llm_run_id": extraction.source,
                    }
                )
                items.append(
                    {
                        "knowledge_id": record.knowledge_id,
                        "title": record.title,
                        "knowledge_type": record.knowledge_type,
                        "category_label": record.category_label,
                        "source_section": record.source_section,
                        "confidence_score": record.confidence_score,
                        "relation_type": "EXTRACTED_FROM",
                    }
                )
        output_path = self._paper_dir(paper_id) / "extracted" / "knowledge.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "paper_id": paper_id,
            "source": extraction_source,
            "skipped_reason": skipped_reason,
            "items": items,
            "summary": note[:200],
            "section_count": len(sections),
        }
        output_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        now = utc_now()
        with self.connect() as conn:
            self._upsert_paper_artifact(
                conn=conn,
                paper_id=paper_id,
                artifact_key="extracted_knowledge",
                artifact_type="json",
                stage="extract",
                path=output_path,
                metadata={
                    "source": extraction_source,
                    "item_count": len(items),
                    "skipped_reason": skipped_reason,
                },
                now=now,
            )
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
            self._write_metadata_json(conn, paper_id, now)
            conn.commit()
        return self._create_job(
            paper_id=paper_id,
            job_type="paper_extract_knowledge",
            status="succeeded",
            progress=1.0,
            message=(
                "Extracted evidence-grounded knowledge from local paper text."
                if items
                else "No evidence-grounded knowledge candidates were detected."
            ),
            result={
                "output_path": str(output_path),
                "item_count": len(items),
                "source": extraction_source,
                "skipped_reason": skipped_reason,
            },
        )

    def run_extract_datasets(self, paper_id: int) -> JobRecord:
        paper = self.get_paper(paper_id)
        note = self.get_document(paper_id, "note").content
        sections = self.list_sections(paper_id)
        resource_repository = ResourceRepository(
            db_path=self.db_path,
            data_root=self.data_root,
        )
        existing = resource_repository.list_links_from_source(
            source_id=paper_id,
            target_type="Dataset",
        )
        if existing:
            items = [
                {
                    "dataset_id": record.resource_id,
                    "name": record.display_name,
                    "relation_type": record.relation_type,
                }
                for record in existing
            ]
        else:
            items = []
            for mention in self._extract_dataset_mentions(note=note, sections=sections):
                dataset = resource_repository.create_dataset(
                    {
                        "name": mention.name,
                        "normalized_name": mention.name.lower(),
                        "task_type": mention.task_type,
                        "data_domain": mention.data_domain,
                        "source": "paper_extract_datasets_local",
                        "description": (
                            f"Dataset or benchmark mention extracted from "
                            f"{paper.title} ({mention.source_section})."
                        ),
                        "benchmark_summary": mention.evidence_text,
                    }
                )
                resource_repository.link_dataset_to_paper(
                    paper_id=paper_id,
                    dataset_id=dataset.dataset_id,
                )
                items.append(
                    {
                        "dataset_id": dataset.dataset_id,
                        "name": dataset.name,
                        "task_type": dataset.task_type,
                        "data_domain": dataset.data_domain,
                        "source_section": mention.source_section,
                        "evidence_text": mention.evidence_text,
                        "relation_type": "MENTIONS_DATASET",
                    }
                )
        output_path = self._paper_dir(paper_id) / "extracted" / "datasets.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "paper_id": paper_id,
            "source": "paper_extract_datasets_local",
            "skipped_reason": (
                "" if items else "No dataset or benchmark mentions were detected."
            ),
            "items": items,
            "section_count": len(sections),
        }
        output_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        now = utc_now()
        with self.connect() as conn:
            self._upsert_paper_artifact(
                conn=conn,
                paper_id=paper_id,
                artifact_key="extracted_datasets",
                artifact_type="json",
                stage="extract",
                path=output_path,
                metadata={
                    "source": "paper_extract_datasets_local",
                    "item_count": len(items),
                },
                now=now,
            )
            conn.execute(
                """
                UPDATE biz_paper
                SET paper_stage = ?
                WHERE asset_id = ?
                """,
                ("completed", paper_id),
            )
            conn.execute(
                "UPDATE asset_registry SET updated_at = ? WHERE asset_id = ?",
                (now, paper_id),
            )
            self._write_metadata_json(conn, paper_id, now)
            conn.commit()
        return self._create_job(
            paper_id=paper_id,
            job_type="paper_extract_datasets",
            status="succeeded",
            progress=1.0,
            message=(
                "Extracted dataset mentions from local paper text."
                if items
                else "No dataset mentions were detected."
            ),
            result={
                "output_path": str(output_path),
                "item_count": len(items),
                "source": "paper_extract_datasets_local",
                "skipped_reason": (
                    "" if items else "No dataset or benchmark mentions were detected."
                ),
            },
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
            path = section_dir / section_filename(section_key)
            if not path.exists():
                continue
            content = path.read_text(encoding="utf-8")
            records.append(
                {
                    "section_key": section_key,
                    "title": title,
                    "content": content,
                    "char_count": len(content),
                    "generated": bool(content.strip()),
                }
            )
        return records

    def _extract_dataset_mentions(
        self,
        *,
        note: str,
        sections: list[dict[str, Any]],
        max_items: int = 5,
    ) -> list[DatasetMention]:
        sources: list[tuple[str, str]] = []
        if note.strip():
            sources.append(("note", note))
        for section in sections:
            content = str(section.get("content") or "")
            if content.strip():
                sources.append((str(section.get("section_key") or "section"), content))

        mentions: list[DatasetMention] = []
        seen: set[str] = set()
        for source_section, text in sources:
            for sentence in self._dataset_candidate_sentences(text):
                for name in self._dataset_names_from_sentence(sentence):
                    normalized = name.lower()
                    if normalized in seen:
                        continue
                    seen.add(normalized)
                    mentions.append(
                        DatasetMention(
                            name=name,
                            task_type=self._infer_dataset_task(sentence),
                            data_domain=self._infer_dataset_domain(sentence),
                            evidence_text=sentence,
                            source_section=source_section,
                        )
                    )
                    if len(mentions) >= max_items:
                        return mentions
        return mentions

    def _dataset_candidate_sentences(self, text: str) -> list[str]:
        compact = re.sub(r"\s+", " ", self._strip_markdown_for_matching(text)).strip()
        if not compact:
            return []
        return [
            sentence.strip(" -")
            for sentence in re.split(r"(?<=[.!?])\s+", compact)
            if 40 <= len(sentence.strip()) <= 700
        ]

    def _dataset_names_from_sentence(self, sentence: str) -> list[str]:
        names: list[str] = []
        for match in KNOWN_DATASET_PATTERN.finditer(sentence):
            names.append(match.group(1))
        for match in GENERIC_DATASET_PATTERN.finditer(sentence):
            candidate = re.sub(r"\s+", " ", match.group(1)).strip()
            if candidate.lower() in {"the dataset", "our dataset", "this dataset"}:
                continue
            if any(name.lower() in candidate.lower() for name in names):
                continue
            names.append(candidate)
        return self._dedupe_preserve_order(names)

    def _infer_dataset_task(self, sentence: str) -> str:
        lowered = sentence.lower()
        if any(token in lowered for token in ("classification", "classify")):
            return "classification"
        if any(token in lowered for token in ("question answering", "qa")):
            return "question_answering"
        if any(token in lowered for token in ("translation", "wmt")):
            return "machine_translation"
        if any(token in lowered for token in ("segmentation", "detection")):
            return "vision_benchmark"
        if any(token in lowered for token in ("reasoning", "gsm8k", "mmlu")):
            return "reasoning_benchmark"
        if any(token in lowered for token in ("benchmark", "evaluate", "evaluation")):
            return "benchmark"
        return ""

    def _infer_dataset_domain(self, sentence: str) -> str:
        lowered = sentence.lower()
        if any(token in lowered for token in ("image", "vision", "coco", "imagenet")):
            return "computer_vision"
        if any(token in lowered for token in ("language", "text", "qa", "translation")):
            return "nlp"
        if any(token in lowered for token in ("video", "instance segmentation")):
            return "video_understanding"
        if any(token in lowered for token in ("math", "reasoning", "gsm8k", "mmlu")):
            return "reasoning"
        return ""

    def _strip_markdown_for_matching(self, text: str) -> str:
        without_comments = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
        without_code = re.sub(r"```.*?```", " ", without_comments, flags=re.S)
        return without_code.replace("#", " ")

    def _dedupe_preserve_order(self, values: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            normalized = value.lower()
            if normalized in seen:
                continue
            seen.add(normalized)
            result.append(value)
        return result

    # ============================================================
    # Job & Artifact Management
    # ============================================================

    def get_job(self, job_id: str) -> JobRecord:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
        if row is None:
            raise JobNotFoundError(f"Job not found: {job_id}")
        return self._job_from_row(row)

    def _finish_job(
        self,
        job_id: str | None,
        *,
        status: str,
        progress: float,
        message: str,
        result: dict[str, Any] | None = None,
        error: dict[str, Any] | None = None,
    ) -> JobRecord:
        now = utc_now()
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE jobs
                SET status = ?, progress = ?, message = ?, result = ?,
                    error = ?, updated_at = ?
                WHERE job_id = ?
                """,
                (
                    status,
                    progress,
                    message,
                    json.dumps(result, ensure_ascii=False) if result is not None else None,
                    json.dumps(error, ensure_ascii=False) if error is not None else None,
                    now,
                    job_id,
                ),
            )
            conn.commit()
        return self.get_job(job_id)

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

    # ============================================================
    # Internal Helpers
    # ============================================================

    def _migrate_schema(self, conn: sqlite3.Connection) -> None:
        columns = self._table_columns(conn, "biz_paper")
        if "paper_slug" not in columns:
            conn.execute(
                "ALTER TABLE biz_paper ADD COLUMN paper_slug TEXT NOT NULL DEFAULT ''"
            )
        if "abstract" not in columns:
            conn.execute(
                "ALTER TABLE biz_paper ADD COLUMN abstract TEXT NOT NULL DEFAULT ''"
            )
        if "source_kind" not in columns:
            conn.execute(
                "ALTER TABLE biz_paper ADD COLUMN source_kind TEXT NOT NULL DEFAULT 'manual'"
            )
        if "ccf_rank" not in columns:
            conn.execute(
                "ALTER TABLE biz_paper ADD COLUMN ccf_rank TEXT NOT NULL DEFAULT ''"
            )
        if "sci_quartile" not in columns:
            conn.execute(
                "ALTER TABLE biz_paper ADD COLUMN sci_quartile TEXT NOT NULL DEFAULT ''"
            )
        self._backfill_paper_ranks(conn)
        self._backfill_paper_slugs(conn)
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_biz_paper_slug_unique ON biz_paper(paper_slug)"
        )

    def _target_paper_dir_for_slug(
        self,
        conn: sqlite3.Connection,
        paper_slug: str,
        category_id: object,
    ) -> Path:
        category_path = self._category_storage_path(conn, category_id)
        return self.paper_root / category_path / paper_slug

    def _category_storage_path(
        self,
        conn: sqlite3.Connection,
        category_id: object,
    ) -> Path:
        if category_id is None:
            return Path("unclassified")
        try:
            category_id_int = int(category_id)
        except (TypeError, ValueError):
            return Path("unclassified")
        row = conn.execute(
            "SELECT path FROM biz_category WHERE id = ?",
            (category_id_int,),
        ).fetchone()
        if row is None:
            return Path("unclassified")
        parts = [
            self._slugify_storage_segment(part)
            for part in str(row["path"]).split("/")
            if part.strip()
        ]
        return Path(*parts) if parts else Path("unclassified")

    def _slugify_storage_segment(self, value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return slug or "untitled"

    def _relocate_paper_dir_for_category(
        self,
        conn: sqlite3.Connection,
        paper_id: int,
    ) -> None:
        row = conn.execute(
            """
            SELECT bp.paper_slug, bp.category_id, pi.storage_path
            FROM biz_paper bp
            JOIN asset_registry ar ON ar.asset_id = bp.asset_id
            JOIN physical_item pi ON pi.item_id = ar.item_id
            WHERE bp.asset_id = ?
            """,
            (paper_id,),
        ).fetchone()
        if row is None:
            raise PaperNotFoundError(f"Paper not found: {paper_id}")

        current_dir = Path(str(row["storage_path"]))
        target_dir = self._target_paper_dir_for_slug(
            conn,
            str(row["paper_slug"]),
            row["category_id"],
        )
        if current_dir.resolve() == target_dir.resolve():
            return

        target_dir.parent.mkdir(parents=True, exist_ok=True)
        if current_dir.exists() and not target_dir.exists():
            shutil.move(str(current_dir), str(target_dir))
        else:
            target_dir.mkdir(parents=True, exist_ok=True)
        self._rewrite_paper_storage_paths(conn, paper_id, current_dir, target_dir)

    def _rewrite_paper_storage_paths(
        self,
        conn: sqlite3.Connection,
        paper_id: int,
        old_dir: Path,
        new_dir: Path,
    ) -> None:
        paper_asset = conn.execute(
            "SELECT item_id FROM asset_registry WHERE asset_id = ?",
            (paper_id,),
        ).fetchone()
        if paper_asset is not None:
            conn.execute(
                "UPDATE physical_item SET storage_path = ? WHERE item_id = ?",
                (str(new_dir), str(paper_asset["item_id"])),
            )

        doc_rows = conn.execute(
            """
            SELECT bdl.doc_id, bdl.doc_role, bdl.doc_path, ar.item_id
            FROM biz_doc_layout bdl
            JOIN asset_registry ar ON ar.asset_id = bdl.doc_id
            WHERE bdl.parent_id = ?
            """,
            (paper_id,),
        ).fetchall()
        for row in doc_rows:
            rewritten = self._rewrite_child_path(Path(str(row["doc_path"])), old_dir, new_dir)
            conn.execute(
                "UPDATE biz_doc_layout SET doc_path = ? WHERE parent_id = ? AND doc_role = ?",
                (str(rewritten), paper_id, str(row["doc_role"])),
            )
            conn.execute(
                "UPDATE physical_item SET storage_path = ? WHERE item_id = ?",
                (str(rewritten), str(row["item_id"])),
            )

        artifact_rows = conn.execute(
            """
            SELECT bpa.artifact_id, bpa.asset_id, bpa.storage_path, ar.item_id
            FROM biz_paper_artifact bpa
            JOIN asset_registry ar ON ar.asset_id = bpa.asset_id
            WHERE bpa.paper_id = ?
            """,
            (paper_id,),
        ).fetchall()
        for row in artifact_rows:
            rewritten = self._rewrite_child_path(
                Path(str(row["storage_path"])),
                old_dir,
                new_dir,
            )
            conn.execute(
                "UPDATE biz_paper_artifact SET storage_path = ? WHERE artifact_id = ?",
                (str(rewritten), int(row["artifact_id"])),
            )
            conn.execute(
                "UPDATE physical_item SET storage_path = ? WHERE item_id = ?",
                (str(rewritten), str(row["item_id"])),
            )

    def _rewrite_child_path(self, path: Path, old_dir: Path, new_dir: Path) -> Path:
        try:
            relative = path.resolve().relative_to(old_dir.resolve())
        except ValueError:
            return path
        return new_dir / relative

    def _table_columns(self, conn: sqlite3.Connection, table_name: str) -> set[str]:
        rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        return {str(row["name"]) for row in rows}

    def _backfill_paper_slugs(self, conn: sqlite3.Connection) -> None:
        rows = conn.execute(
            """
            SELECT asset_id, title, paper_slug
            FROM biz_paper
            ORDER BY asset_id ASC
            """
        ).fetchall()
        used = {
            str(row["paper_slug"])
            for row in rows
            if str(row["paper_slug"] or "").strip()
        }
        for row in rows:
            if str(row["paper_slug"] or "").strip():
                continue
            asset_id = int(row["asset_id"])
            slug = self._dedupe_slug(
                self._slugify_paper_title(str(row["title"]), f"paper-{asset_id}"),
                used,
            )
            used.add(slug)
            conn.execute(
                "UPDATE biz_paper SET paper_slug = ? WHERE asset_id = ?",
                (slug, asset_id),
            )

    def _backfill_paper_ranks(self, conn: sqlite3.Connection) -> None:
        rows = conn.execute(
            """
            SELECT asset_id, venue, venue_short, ccf_rank, sci_quartile
            FROM biz_paper
            ORDER BY asset_id ASC
            """
        ).fetchall()
        for row in rows:
            updates: dict[str, str] = {}
            venue = str(row["venue"] or "")
            venue_short = str(row["venue_short"] or "")
            if not str(row["ccf_rank"] or ""):
                ccf_rank = infer_ccf_rank(venue_short, venue)
                if ccf_rank:
                    updates["ccf_rank"] = ccf_rank
            if not str(row["sci_quartile"] or ""):
                sci_quartile = infer_sci_quartile(venue_short, venue)
                if sci_quartile:
                    updates["sci_quartile"] = sci_quartile
            if not updates:
                continue
            columns = [f"{key} = ?" for key in updates]
            conn.execute(
                f"UPDATE biz_paper SET {', '.join(columns)} WHERE asset_id = ?",
                [*updates.values(), int(row["asset_id"])],
            )

    def _unique_paper_slug(self, conn: sqlite3.Connection, title: str) -> str:
        rows = conn.execute(
            """
            SELECT paper_slug
            FROM biz_paper
            WHERE paper_slug != ''
            """
        ).fetchall()
        used = {str(row["paper_slug"]) for row in rows}
        base = self._slugify_paper_title(title, "paper")
        slug = self._dedupe_slug(base, used)
        if slug == base:
            return f"{slug}-{uuid4().hex[:8]}"
        return slug

    def _slugify_paper_title(self, title: str, fallback: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
        return slug or fallback

    def _dedupe_slug(self, base_slug: str, used: set[str]) -> str:
        if base_slug not in used:
            return base_slug
        for index in range(2, 10_000):
            candidate = f"{base_slug}-{index}"
            if candidate not in used:
                return candidate
        return f"{base_slug}-{uuid4().hex[:8]}"

    def _upsert_note_state(
        self,
        *,
        conn: sqlite3.Connection,
        paper_id: int,
        note_doc_id: int,
        note_status: str,
        content: str,
        now: str,
        last_generated_at: str | None = None,
        last_user_modified_at: str | None = None,
        last_merge_policy: str | None = None,
        managed_block_hashes: dict[str, str] | None = None,
        conflict_reason: str | None = None,
    ) -> None:
        current = conn.execute(
            """
            SELECT last_generated_at, last_user_modified_at, last_merge_policy,
                conflict_reason
            FROM biz_note_state
            WHERE paper_id = ?
            """,
            (paper_id,),
        ).fetchone()
        managed_hashes = (
            self._managed_block_hashes(content)
            if managed_block_hashes is None
            else managed_block_hashes
        )
        conn.execute(
            """
            INSERT INTO biz_note_state (
                paper_id, note_doc_id, note_status, document_hash,
                managed_block_hash_json, last_generated_at,
                last_user_modified_at, last_merge_policy, conflict_reason,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(paper_id) DO UPDATE SET
                note_doc_id = excluded.note_doc_id,
                note_status = excluded.note_status,
                document_hash = excluded.document_hash,
                managed_block_hash_json = excluded.managed_block_hash_json,
                last_generated_at = excluded.last_generated_at,
                last_user_modified_at = excluded.last_user_modified_at,
                last_merge_policy = excluded.last_merge_policy,
                conflict_reason = excluded.conflict_reason,
                updated_at = excluded.updated_at
            """,
            (
                paper_id,
                note_doc_id,
                note_status,
                hash_text(content),
                json.dumps(managed_hashes, ensure_ascii=False),
                last_generated_at
                if last_generated_at is not None
                else None if current is None else current["last_generated_at"],
                last_user_modified_at
                if last_user_modified_at is not None
                else None if current is None else current["last_user_modified_at"],
                last_merge_policy
                if last_merge_policy is not None
                else "" if current is None else current["last_merge_policy"],
                conflict_reason
                if conflict_reason is not None
                else "" if current is None else current["conflict_reason"],
                now,
            ),
        )

    def _note_status_after_user_edit(
        self,
        *,
        conn: sqlite3.Connection,
        paper_id: int,
        content: str,
    ) -> str:
        previous_hashes = self._stored_managed_block_hashes(conn, paper_id)
        if not previous_hashes:
            return "user_modified"
        current_hashes = self._managed_block_hashes(content)
        for block_id, previous_hash in previous_hashes.items():
            if current_hashes.get(block_id) != previous_hash:
                return "conflict_pending"
        return "user_modified"

    def _stored_managed_block_hashes(
        self,
        conn: sqlite3.Connection,
        paper_id: int,
    ) -> dict[str, str]:
        row = conn.execute(
            """
            SELECT managed_block_hash_json
            FROM biz_note_state
            WHERE paper_id = ?
            """,
            (paper_id,),
        ).fetchone()
        if row is None:
            return {}
        payload = json.loads(row["managed_block_hash_json"] or "{}")
        return {str(key): str(value) for key, value in payload.items()}

    def _managed_block_hashes(self, content: str) -> dict[str, str]:
        return {
            block_id: hash_text(block)
            for block_id, block in extract_managed_blocks(content).items()
        }

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
            if role == "note":
                self._upsert_note_state(
                    conn=conn,
                    paper_id=paper_id,
                    note_doc_id=doc_id,
                    note_status="empty",
                    content=content,
                    now=now,
                )

    def _paper_from_row(self, row: sqlite3.Row) -> PaperRecord:
        paper_id = int(row["asset_id"])
        record = paper_record_from_row(row, self._asset_map(paper_id))
        source_pdf = self._source_pdf_info(paper_id)
        record = replace(
            record,
            source_pdf_size=source_pdf["file_size"],
            source_pdf_is_real=source_pdf["is_real_pdf"],
        )
        latest_job = self._latest_job_for_paper(paper_id)
        if latest_job is None:
            return record
        return replace(
            record,
            latest_job_id=latest_job.job_id,
            latest_job_type=latest_job.type,
            latest_job_status=latest_job.status,
            latest_job_message=latest_job.message,
        )

    def _source_pdf_info(self, paper_id: int) -> dict[str, Any]:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT file_size, metadata
                FROM biz_paper_artifact
                WHERE paper_id = ? AND artifact_key = 'source_pdf'
                LIMIT 1
                """,
                (paper_id,),
            ).fetchone()
        if row is None:
            return {"file_size": 0, "is_real_pdf": False}
        metadata = json.loads(row["metadata"] or "{}")
        if "is_real_pdf" in metadata:
            return {
                "file_size": int(row["file_size"]),
                "is_real_pdf": bool(metadata["is_real_pdf"]),
            }
        return {
            "file_size": int(row["file_size"]),
            "is_real_pdf": int(row["file_size"]) >= get_settings().paper_download.min_pdf_size,
        }

    def _latest_job_for_paper(self, paper_id: int) -> JobRecord | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT *
                FROM jobs
                WHERE resource_type = 'paper' AND resource_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (paper_id,),
            ).fetchone()
        return self._job_from_row(row) if row else None

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

    def _pdf_integrity_metadata(self, path: Path) -> dict[str, Any]:
        file_size = path_size(path)
        header = ""
        if path.exists() and path.is_file():
            with path.open("rb") as handle:
                header = handle.read(5).decode("latin1", errors="replace")
        valid_pdf_header = header == "%PDF-"
        min_pdf_size = get_settings().paper_download.min_pdf_size
        return {
            "file_size": file_size,
            "pdf_header": header,
            "valid_pdf_header": valid_pdf_header,
            "min_pdf_size": min_pdf_size,
            "is_real_pdf": valid_pdf_header and file_size >= min_pdf_size,
        }

    def _sections_dir(self, paper_id: int) -> Path:
        return self._paper_dir(paper_id) / "parsed" / "sections"

    def _note_image_base_dirs(self, paper_id: int) -> list[Path]:
        paper_dir = self._paper_dir(paper_id)
        return [
            paper_dir,
            paper_dir / "images",
            paper_dir / "figures",
            paper_dir / "parsed",
            paper_dir / "parsed" / "sections",
            paper_dir / "parsed" / "images",
            paper_dir / "parsed" / "figures",
            paper_dir / "parsed" / "mineru",
            paper_dir / "parsed" / "mineru" / "images",
        ]

    def _postprocessed_figure_dir(self, parsed_artifacts: dict[str, str]) -> Path | None:
        value = parsed_artifacts.get("postprocessed_image_dir") or parsed_artifacts.get(
            "postprocessed_figure_dir"
        )
        if not value:
            return None
        path = Path(value)
        return path if path.exists() else None

    def _count_files(self, directory: Path | None) -> int:
        if directory is None or not directory.exists():
            return 0
        return sum(1 for path in directory.rglob("*") if path.is_file())

    def _sync_parse_images(
        self,
        *,
        raw_path: Path,
        parsed_artifacts: dict[str, str],
    ) -> int:
        target_dir = raw_path.parent / "images"
        source_dirs = self._parse_image_source_dirs(raw_path, parsed_artifacts)
        copied = 0
        for source_dir in source_dirs:
            if not source_dir.exists() or source_dir.resolve() == target_dir.resolve():
                continue
            for source_path in source_dir.rglob("*"):
                if not source_path.is_file():
                    continue
                relative_path = source_path.relative_to(source_dir)
                target_path = target_dir / relative_path
                target_path.parent.mkdir(parents=True, exist_ok=True)
                if target_path.exists() and path_hash(target_path) == path_hash(source_path):
                    copied += 1
                    continue
                shutil.copy2(source_path, target_path)
                copied += 1
        return copied

    def _parse_image_source_dirs(
        self,
        raw_path: Path,
        parsed_artifacts: dict[str, str],
    ) -> list[Path]:
        paper_dir = raw_path.parent.parent
        candidates: list[Path] = [
            raw_path.parent / "mineru" / "images",
            paper_dir / "mineru" / "images",
        ]
        for key in ("mineru_image_dir", "source_image_dir"):
            value = parsed_artifacts.get(key)
            if value:
                candidates.append(Path(value))
        for key in ("mineru_markdown_path", "source_markdown_path"):
            value = parsed_artifacts.get(key)
            if value:
                candidates.append(Path(value).parent / "images")

        unique: list[Path] = []
        seen: set[str] = set()
        for candidate in candidates:
            marker = str(candidate.resolve()) if candidate.exists() else str(candidate)
            if marker in seen:
                continue
            seen.add(marker)
            unique.append(candidate)
        return unique

    def _download_request_for_paper(
        self, paper: PaperRecord
    ) -> RepositoryPaperDownloadRequest:
        source_url = paper.pdf_url or paper.source_url
        if not source_url and self._looks_like_url(paper.title):
            source_url = paper.title
        return RepositoryPaperDownloadRequest(
            source_url=source_url or None,
            doi=paper.doi or None,
            title="" if self._looks_like_url(paper.title) else paper.title,
            year="" if paper.year is None else str(paper.year),
            venue=paper.venue,
            output_dir=f"paper_api_{paper.paper_id}",
            overwrite=True,
        )

    def _network_download_enabled(self, paper: PaperRecord) -> bool:
        if not (
            paper.pdf_url
            or paper.source_url
            or paper.doi
            or self._looks_like_url(paper.title)
        ):
            return False
        return os.getenv("RFLOW_ENABLE_NETWORK_PAPER_DOWNLOAD", "").lower() in {
            "1",
            "true",
            "yes",
        }

    def _looks_like_url(self, value: str) -> bool:
        return value.strip().lower().startswith(("http://", "https://"))

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
                raw_content, artifacts, warning = self._postprocess_mineru_markdown(
                    paper_id=paper_id,
                    markdown_path=candidate,
                    image_dir=candidate.parent / "images",
                    content_list_path=self._resolve_local_content_list_path(candidate.parent),
                    base_artifacts={"source_markdown_path": str(candidate)},
                )
                return raw_content, "existing_mineru_markdown", warning, artifacts

        pdf_path = self._pdf_path(paper_id)
        if pdf_path.exists() and get_settings().mineru.api_token:
            try:
                bundle = asyncio.run(
                    PDFParserService(get_settings()).extract_raw_markdown(
                        pdf_path,
                        artifact_dir=self._paper_dir(paper_id) / "parsed" / "mineru",
                    )
                )
                raw_content, artifacts, warning = self._postprocess_mineru_markdown(
                    paper_id=paper_id,
                    markdown_path=bundle.markdown_path,
                    image_dir=bundle.image_dir,
                    content_list_path=bundle.content_list_path,
                    base_artifacts={
                        "mineru_markdown_path": str(bundle.markdown_path),
                        "mineru_image_dir": str(bundle.image_dir),
                        "mineru_content_list_path": ""
                        if bundle.content_list_path is None
                        else str(bundle.content_list_path),
                    },
                )
                return raw_content, "mineru", warning, artifacts
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

    def _postprocess_mineru_markdown(
        self,
        *,
        paper_id: int,
        markdown_path: Path,
        image_dir: Path,
        content_list_path: Path | None,
        base_artifacts: dict[str, str],
    ) -> tuple[str, dict[str, str], str | None]:
        if not image_dir.exists():
            return markdown_path.read_text(encoding="utf-8"), base_artifacts, None

        parsed_dir = self._paper_dir(paper_id) / "parsed"
        output_markdown_path = parsed_dir / "postprocessed.md"
        output_figure_dir = parsed_dir / "images"
        try:
            processed = process_mineru_markdown_artifacts(
                raw_markdown_path=markdown_path,
                source_image_dir=image_dir,
                content_list_path=content_list_path,
                output_markdown_path=output_markdown_path,
                output_figure_dir=output_figure_dir,
            )
        except Exception as exc:  # noqa: BLE001 - raw MinerU Markdown remains usable
            return (
                markdown_path.read_text(encoding="utf-8"),
                base_artifacts,
                f"MINERU_POSTPROCESS_SKIPPED: {exc}",
            )

        artifacts = {
            **base_artifacts,
            "postprocessed_markdown_path": str(processed.markdown_path),
            "postprocessed_image_dir": str(processed.figure_dir),
            "postprocessed_figure_dir": str(processed.figure_dir),
            "postprocessed_figure_count": str(processed.figure_count),
            "postprocessed_raw_image_ref_count": str(processed.raw_image_ref_count),
            "postprocessed_grouped_image_ref_count": str(processed.grouped_image_ref_count),
        }
        return processed.markdown_path.read_text(encoding="utf-8"), artifacts, None

    def _resolve_local_content_list_path(self, artifact_dir: Path) -> Path | None:
        candidates = [
            artifact_dir / "content_list_v2.json",
            artifact_dir / "content_list.json",
            *sorted(artifact_dir.glob("*_content_list.json")),
        ]
        return next((candidate for candidate in candidates if candidate.exists()), None)

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
            self._write_metadata_json(conn, paper_id, now)
            conn.commit()

    def _write_metadata_json(
        self,
        conn: sqlite3.Connection,
        paper_id: int,
        now: str,
    ) -> None:
        row = conn.execute(
            """
            SELECT bp.*, pi.storage_path
            FROM biz_paper bp
            JOIN asset_registry ar ON ar.asset_id = bp.asset_id
            JOIN physical_item pi ON pi.item_id = ar.item_id
            WHERE bp.asset_id = ?
            """,
            (paper_id,),
        ).fetchone()
        if row is None:
            return

        paper_dir = Path(str(row["storage_path"]))
        metadata_path = paper_dir / "metadata.json"
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        category_path = ""
        if row["category_id"] is not None:
            category = conn.execute(
                "SELECT path FROM biz_category WHERE id = ?",
                (row["category_id"],),
            ).fetchone()
            category_path = "" if category is None else str(category["path"])
        artifacts = {
            str(artifact["artifact_key"]): str(artifact["storage_path"])
            for artifact in conn.execute(
                """
                SELECT artifact_key, storage_path
                FROM biz_paper_artifact
                WHERE paper_id = ?
                ORDER BY artifact_key ASC
                """,
                (paper_id,),
            ).fetchall()
        }
        payload = {
            "paper_id": paper_id,
            "paper_slug": str(row["paper_slug"]),
            "title": str(row["title"]),
            "authors": json.loads(row["authors"] or "[]"),
            "abstract": str(row["abstract"] or ""),
            "year": row["pub_year"],
            "venue": str(row["venue"] or ""),
            "venue_short": str(row["venue_short"] or ""),
            "doi": str(row["doi"] or ""),
            "source_url": str(row["source_url"] or ""),
            "pdf_url": str(row["pdf_url"] or ""),
            "source_kind": str(row["source_kind"] or ""),
            "category_id": row["category_id"],
            "category_path": category_path,
            "paper_stage": str(row["paper_stage"]),
            "download_status": str(row["download_status"]),
            "parse_status": str(row["parse_status"]),
            "refine_status": str(row["refine_status"]),
            "review_status": str(row["review_status"]),
            "note_status": str(row["note_status"]),
            "artifacts": artifacts,
            "updated_at": now,
        }
        metadata_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._upsert_paper_artifact(
            conn=conn,
            paper_id=paper_id,
            artifact_key="metadata_json",
            artifact_type="json",
            stage="metadata",
            path=metadata_path,
            metadata={"doc_role": "metadata"},
            now=now,
        )

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
            section_content = _rewrite_section_image_links(blocks.get(section_key, ""))
            path = section_dir / section_filename(section_key)
            rendered_content = section_content.rstrip()
            if rendered_content:
                rendered_content += "\n"
            path.write_text(rendered_content, encoding="utf-8")
            records.append(
                {
                    "section_key": section_key,
                    "title": title,
                    "content": rendered_content,
                    "char_count": len(rendered_content),
                    "generated": bool(rendered_content.strip()),
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


def _rewrite_section_image_links(markdown_text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        alt = match.group("alt")
        target = match.group("target").strip()
        normalized_target = target[2:] if target.startswith("./") else target
        if normalized_target.startswith(("images/", "figures/")):
            target = f"../{normalized_target}"
        return f"![{alt}]({target})"

    return re.sub(r"!\[(?P<alt>[^\]]*)]\((?P<target>[^)\s]+)\)", replace, markdown_text)
