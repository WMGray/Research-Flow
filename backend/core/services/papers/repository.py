from __future__ import annotations

import os
import re
import shutil
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from string import Template
from typing import Any

from backend.core.services.papers.models import BatchRecord, CandidateRecord, GenerateNoteInput, IngestPaperInput, ParserRunRecord, PaperRecord
from backend.core.services.papers.parser import PdfParserResult
from backend.core.services.papers.utils import load_markdown_front_matter, merge_metadata, read_json, read_text, read_yaml, slugify, utc_now, write_json, write_text, write_yaml


DEFAULT_NOTE_TEMPLATE = """---
title: $title
year: $year
venue: $venue
doi: $doi
domain: $domain
area: $area
topic: $topic
status: $status
tags:
$tags
---

# 文章摘要

# 缩写与术语

# 背景与问题定义

# 方法拆解

# 实验结果

# 局限与风险

# 与当前研究的关联
"""


class PaperRepository:
    def __init__(self, data_root: Path) -> None:
        self.data_root = data_root
        self.discover_root = data_root / "Discover"
        self.acquire_root = data_root / "Acquire"
        self.library_root = data_root / "Library"
        self.template_root = data_root / "templates"
        self.ensure_layout()

    def ensure_layout(self) -> None:
        for path in (
            self.discover_root / "search_batches",
            self.acquire_root / "curated",
            self.library_root / "unclassified",
            self.template_root,
        ):
            path.mkdir(parents=True, exist_ok=True)

    def list_papers(self) -> list[PaperRecord]:
        paper_dirs: set[Path] = set()
        for root in (self.acquire_root, self.library_root):
            if not root.exists():
                continue
            for name in ("metadata.yaml", "metadata.json", "state.json", "paper.pdf", "note.md"):
                paper_dirs.update(path.parent for path in root.rglob(name) if path.parent.is_dir())
        records = [self._paper_record_from_dir(paper_dir) for paper_dir in paper_dirs]
        return sorted(records, key=lambda item: (item.updated_at, item.title), reverse=True)

    def list_batches(self) -> list[BatchRecord]:
        batches_root = self.discover_root / "search_batches"
        if not batches_root.exists():
            return []

        records: list[BatchRecord] = []
        for batch_dir in sorted(path for path in batches_root.iterdir() if path.is_dir()):
            candidates = self._candidate_rows(batch_dir / "candidates.json")
            records.append(
                BatchRecord(
                    batch_id=batch_dir.name,
                    title=batch_dir.name.replace("-", " "),
                    candidate_total=len(candidates),
                    keep_total=len([row for row in candidates if self._candidate_decision(row) == "keep"]),
                    reject_total=len([row for row in candidates if self._candidate_decision(row) == "reject"]),
                    review_status="reviewed" if (batch_dir / "review.md").exists() else "pending",
                    path=str(batch_dir),
                    updated_at=self._mtime(batch_dir),
                )
            )
        return sorted(records, key=lambda item: item.updated_at, reverse=True)

    def list_candidates(self, batch_id: str | None = None) -> list[CandidateRecord]:
        batches = [batch for batch in self.list_batches() if batch_id in (None, batch.batch_id)]
        records: list[CandidateRecord] = []
        for batch in batches:
            batch_dir = Path(batch.path)
            for index, row in enumerate(self._candidate_rows(batch_dir / "candidates.json")):
                records.append(self._candidate_record(batch.batch_id, index, row, batch.updated_at))
        return records

    def set_candidate_decision(self, batch_id: str, candidate_id: str, decision: str) -> CandidateRecord:
        if decision not in {"keep", "reject", "reset"}:
            raise ValueError(f"Unsupported decision: {decision}")
        batch_dir = self.discover_root / "search_batches" / batch_id
        candidates_path = batch_dir / "candidates.json"
        data = read_json(candidates_path)
        rows = self._rows_from_candidate_data(data)
        target_index = self._candidate_index(rows, candidate_id)
        row = rows[target_index]
        candidate = self._candidate_record(batch_id, target_index, row, utc_now())
        if decision == "reset":
            row.pop("gate1_decision", None)
        elif decision == "keep":
            self._promote_candidate_to_acquire(batch_dir, row)
            rows.pop(target_index)
            self._write_candidate_data(candidates_path, data, rows)
            self._cleanup_batch_if_complete(batch_dir, rows)
            return replace(candidate, decision="keep", updated_at=utc_now())
        elif decision == "reject":
            self._delete_candidate_artifacts(batch_dir, row)
            rows.pop(target_index)
            self._write_candidate_data(candidates_path, data, rows)
            self._cleanup_batch_if_complete(batch_dir, rows)
            return replace(candidate, decision="reject", updated_at=utc_now())
        else:
            row["gate1_decision"] = decision
        row["gate1_updated_at"] = utc_now()
        self._write_candidate_data(candidates_path, data, rows)
        self._cleanup_batch_if_complete(batch_dir, rows)
        return self._candidate_record(batch_id, target_index, row, utc_now())

    def restore_batch_candidates(self, batch_id: str) -> list[dict[str, Any]]:
        batch_dir = self.discover_root / "search_batches" / batch_id
        if not batch_dir.exists():
            raise FileNotFoundError(batch_id)

        candidates = self._rebuild_candidates(batch_dir)
        self._write_candidate_data(batch_dir / "candidates.json", [], candidates)
        return candidates

    def cleanup_batches(self) -> list[str]:
        removed: list[str] = []
        batches_root = self.discover_root / "search_batches"
        if not batches_root.exists():
            return removed

        for batch_dir in sorted(path for path in batches_root.iterdir() if path.is_dir()):
            candidates = self._candidate_rows(batch_dir / "candidates.json")
            if not self._should_delete_batch(batch_dir, candidates):
                continue
            removed.append(batch_dir.name)
            self._delete_tree(batch_dir)

        self._prune_empty_parents(batches_root, stop_at=self.data_root)
        return removed

    def cleanup_batch(self, batch_id: str) -> bool:
        batch_dir = self.discover_root / "search_batches" / batch_id
        if not batch_dir.exists():
            return False
        candidates = self._candidate_rows(batch_dir / "candidates.json")
        if not self._should_delete_batch(batch_dir, candidates):
            return False
        self._delete_tree(batch_dir)
        self._prune_empty_parents(batch_dir.parent, stop_at=self.data_root)
        return True

    def get_paper(self, paper_id: str) -> PaperRecord | None:
        paper_dir = self.get_paper_dir(paper_id)
        return self._paper_record_from_dir(paper_dir) if paper_dir else None

    def get_paper_dir(self, paper_id: str) -> Path | None:
        for paper in self.list_papers():
            if paper.paper_id == paper_id or paper.slug == paper_id:
                return Path(paper.path)
        return None

    def ingest(self, request: IngestPaperInput) -> PaperRecord:
        source = request.source.resolve()
        if not source.exists():
            raise FileNotFoundError(source)

        source_metadata = self._source_metadata(source)
        title = str(source_metadata.get("title") or source.stem or source.name)
        slug = slugify(title, fallback=slugify(source.name, fallback="paper"))
        metadata = merge_metadata(
            source_metadata,
            {
                "title": title,
                "domain": request.domain or source_metadata.get("domain"),
                "area": request.area or source_metadata.get("area") or source_metadata.get("subdomain"),
                "topic": request.topic or source_metadata.get("topic"),
            },
        )
        target = self._resolve_target_path(metadata, slug, request.target_path)
        if target.exists():
            self.update_paper_state(target, {"status": "needs-review", "workflow_status": "needs-review", "error": "Target already exists"})
            return self._paper_record_from_dir(target)

        target.mkdir(parents=True, exist_ok=True)
        self._copy_source_assets(source, target, move=request.move)
        if not (target / "note.md").exists():
            write_text(target / "note.md", self._render_note_template(metadata))

        status = "processed" if (target / "paper.pdf").exists() else "needs-pdf"
        metadata_to_write = merge_metadata(
            metadata,
            {
                "status": status,
                "updated_at": utc_now(),
                "path": str(target),
                "paper_path": str(target / "paper.pdf") if (target / "paper.pdf").exists() else "",
                "note_path": str(target / "note.md"),
                "refined_path": str(target / "refined.md") if (target / "refined.md").exists() else "",
                "images_path": str(target / "images") if (target / "images").exists() else "",
                "tags": metadata.get("tags") or ["paper"],
            },
        )
        write_yaml(target / "metadata.yaml", metadata_to_write)
        self.update_paper_state(
            target,
            {
                "status": status,
                "workflow_status": status,
                "refine_status": "queued" if status == "processed" else "needs-pdf",
                "parser_status": "parse-pending" if status == "processed" else "needs-pdf",
                "note_status": "template",
                "read_status": "unread",
                "classification_status": "pending",
                "error": "",
            },
        )
        return self._paper_record_from_dir(target)

    def migrate(self, request: IngestPaperInput) -> PaperRecord:
        return self.ingest(IngestPaperInput(source=request.source, domain=request.domain, area=request.area, topic=request.topic, target_path=request.target_path, move=True))

    def generate_note_template(self, request: GenerateNoteInput) -> str:
        return self._render_note_template(request.to_metadata())

    def generate_note_for_paper(self, paper_id: str, *, overwrite: bool = False) -> PaperRecord:
        paper_dir = self._require_paper_dir(paper_id)
        note_path = paper_dir / "note.md"
        if note_path.exists() and not overwrite:
            return self._paper_record_from_dir(paper_dir)

        content = self._render_note_template(self._paper_metadata(paper_dir))
        write_text(note_path, content)
        self.update_paper_state(
            paper_dir,
            {
                "note_status": "template",
                "note_path": str(note_path),
                "error": "",
            },
        )
        return self._paper_record_from_dir(paper_dir)

    def update_paper_state(self, paper_dir: Path, updates: dict[str, Any]) -> dict[str, Any]:
        state_path = paper_dir / "state.json"
        metadata_json_path = paper_dir / "metadata.json"
        state = self._safe_json_object(state_path)
        metadata = self._safe_json_object(metadata_json_path)
        payload = merge_metadata(self._source_metadata(paper_dir), metadata, state, updates, {"updated_at": utc_now()})
        write_json(state_path, merge_metadata(state, updates, {"updated_at": payload["updated_at"]}))
        write_json(metadata_json_path, payload)
        if (paper_dir / "metadata.yaml").exists():
            write_yaml(paper_dir / "metadata.yaml", merge_metadata(read_yaml(paper_dir / "metadata.yaml"), updates, {"updated_at": payload["updated_at"]}))
        return payload

    def mark_status(self, paper_id: str, status: str) -> PaperRecord:
        paper_dir = self._require_paper_dir(paper_id)
        self.update_paper_state(paper_dir, {"status": status, "workflow_status": status, "error": ""})
        return self._paper_record_from_dir(paper_dir)

    def reject_paper(self, paper_id: str) -> PaperRecord:
        paper_dir = self._require_paper_dir(paper_id)
        record = self._paper_record_from_dir(paper_dir)
        self._delete_tree(paper_dir)
        self._prune_empty_parents(paper_dir.parent, stop_at=self.data_root)
        return replace(record, status="rejected", rejected=True, updated_at=utc_now())

    def list_parser_runs(self, paper_id: str) -> list[ParserRunRecord]:
        paper_dir = self._require_paper_dir(paper_id)
        runs = self._parser_runs(paper_dir)
        return [self._parser_run_record(item, self._relative_id(paper_dir)) for item in runs]

    def record_parser_result(self, paper_id: str, result: PdfParserResult, *, started_at: str) -> PaperRecord:
        paper_dir = self._require_paper_dir(paper_id)
        finished_at = utc_now()
        run = {
            "run_id": f"run-{finished_at.replace(':', '').replace('+', 'Z')}",
            "paper_id": self._relative_id(paper_dir),
            "status": result.status,
            "parser": result.parser,
            "source_pdf": str(paper_dir / "paper.pdf"),
            "refined_path": result.refined_path,
            "image_dir": result.image_dir,
            "text_path": result.text_path,
            "sections_path": result.sections_path,
            "error": result.error,
            "started_at": started_at,
            "finished_at": finished_at,
        }
        runs = self._parser_runs(paper_dir)
        runs.append(run)
        write_json(paper_dir / "parser_runs.json", runs)

        status = self._status_from_parser(result.status)
        self.update_paper_state(
            paper_dir,
            {
                "status": status,
                "workflow_status": status,
                "refine_status": result.status,
                "parser_status": status,
                "refined_path": result.refined_path,
                "images_path": result.image_dir,
                "parsed_text_path": result.text_path,
                "parsed_sections_path": result.sections_path,
                "pdf_analysis_path": str(paper_dir / "pdf_analysis.json"),
                "error": result.error,
            },
        )
        return self._paper_record_from_dir(paper_dir)

    def config_health(self) -> dict[str, Any]:
        paths = {
            "data_root": self.data_root,
            "discover_root": self.discover_root,
            "acquire_root": self.acquire_root,
            "library_root": self.library_root,
            "template_root": self.template_root,
        }
        return {
            "data_root": str(self.data_root),
            "paths": {key: {"path": str(path), "exists": path.exists(), "is_dir": path.is_dir()} for key, path in paths.items()},
        }

    def _paper_record_from_dir(self, paper_dir: Path) -> PaperRecord:
        metadata = self._paper_metadata(paper_dir)
        year = self._int_or_none(metadata.get("year"))
        paper_path = paper_dir / "paper.pdf"
        note_path = paper_dir / "note.md"
        refined_path = paper_dir / "refined.md"
        images_path = paper_dir / "images"
        metadata_yaml = paper_dir / "metadata.yaml"
        metadata_json = paper_dir / "metadata.json"
        state_path = paper_dir / "state.json"
        parsed_text = paper_dir / "parsed" / "text.md"
        parsed_sections = paper_dir / "parsed" / "sections.json"
        pdf_analysis = paper_dir / "pdf_analysis.json"
        status = self._resolved_status(metadata, paper_path)

        return PaperRecord(
            paper_id=self._relative_id(paper_dir),
            title=str(metadata.get("title") or paper_dir.name),
            slug=paper_dir.name,
            stage=self._paper_stage(paper_dir),
            status=status,
            domain=str(metadata.get("domain") or ""),
            area=str(metadata.get("area") or metadata.get("subdomain") or ""),
            topic=str(metadata.get("topic") or ""),
            year=year,
            venue=str(metadata.get("venue") or ""),
            doi=str(metadata.get("doi") or ""),
            tags=[str(tag) for tag in metadata.get("tags", []) if tag] or ["paper"],
            path=str(paper_dir),
            paper_path=str(paper_path) if paper_path.exists() else "",
            note_path=str(note_path) if note_path.exists() else "",
            refined_path=str(refined_path) if refined_path.exists() else str(metadata.get("refined_path") or ""),
            images_path=str(images_path) if images_path.exists() else str(metadata.get("images_path") or ""),
            metadata_path=str(metadata_yaml) if metadata_yaml.exists() else "",
            metadata_json_path=str(metadata_json) if metadata_json.exists() else "",
            state_path=str(state_path) if state_path.exists() else "",
            parsed_text_path=str(parsed_text) if parsed_text.exists() else str(metadata.get("parsed_text_path") or ""),
            parsed_sections_path=str(parsed_sections) if parsed_sections.exists() else str(metadata.get("parsed_sections_path") or ""),
            pdf_analysis_path=str(pdf_analysis) if pdf_analysis.exists() else str(metadata.get("pdf_analysis_path") or ""),
            parser_status=str(metadata.get("parser_status") or ("parse-pending" if paper_path.exists() else "needs-pdf")),
            note_status=str(metadata.get("note_status") or "template"),
            read_status=str(metadata.get("read_status") or "unread"),
            refined_review_status=str(metadata.get("refined_review_status") or "pending"),
            classification_status=str(metadata.get("classification_status") or "pending"),
            rejected=bool(metadata.get("rejected") or status == "rejected"),
            error=str(metadata.get("error") or ""),
            updated_at=str(metadata.get("updated_at") or utc_now()),
        )

    def _paper_metadata(self, paper_dir: Path) -> dict[str, Any]:
        return merge_metadata(
            load_markdown_front_matter(paper_dir / "note.md"),
            read_yaml(paper_dir / "metadata.yaml"),
            self._safe_json_object(paper_dir / "metadata.json"),
            self._safe_json_object(paper_dir / "state.json"),
        )

    def _source_metadata(self, source: Path) -> dict[str, Any]:
        if source.is_dir():
            return merge_metadata(load_markdown_front_matter(source / "note.md"), read_yaml(source / "metadata.yaml"), self._safe_json_object(source / "metadata.json"), self._safe_json_object(source / "state.json"))
        if source.suffix.lower() in {".md", ".markdown"}:
            return load_markdown_front_matter(source)
        return {}

    def _candidate_record(self, batch_id: str, index: int, row: dict[str, Any], updated_at: str) -> CandidateRecord:
        authors = row.get("authors") if isinstance(row.get("authors"), list) else []
        return CandidateRecord(
            candidate_id=str(row.get("id") or row.get("candidate_id") or index),
            batch_id=batch_id,
            title=str(row.get("title") or ""),
            authors=[str(author) for author in authors],
            year=self._int_or_none(row.get("year")),
            venue=str(row.get("venue") or ""),
            decision=self._candidate_decision(row),
            source_type=str(row.get("source_type") or ""),
            collection_role=str(row.get("collection_role") or ""),
            paper_type=str(row.get("paper_type") or ""),
            quality=self._bounded_score(row.get("quality"), 72),
            relevance=self._bounded_score(row.get("relevance"), 84),
            recommendation_reason=str(
                row.get("relevance_reason_zh")
                or row.get("screening_reason_zh")
                or row.get("source_evidence")
                or row.get("abstract_zh")
                or ""
            ),
            landing_status=str(row.get("landing_status") or row.get("pdf_status") or ""),
            result_path=str(row.get("result_path") or row.get("landing_path") or ""),
            updated_at=str(row.get("gate1_updated_at") or updated_at),
        )

    def _candidate_rows(self, path: Path) -> list[dict[str, Any]]:
        return self._rows_from_candidate_data(read_json(path))

    def _rows_from_candidate_data(self, data: Any) -> list[dict[str, Any]]:
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and isinstance(data.get("candidates"), list):
            return data["candidates"]
        return []

    def _write_candidate_data(self, path: Path, original: Any, rows: list[dict[str, Any]]) -> None:
        if isinstance(original, dict):
            payload = dict(original)
            payload["candidates"] = rows
            write_json(path, payload)
            return
        write_json(path, rows)

    def _candidate_index(self, rows: list[dict[str, Any]], candidate_id: str) -> int:
        for index, row in enumerate(rows):
            if candidate_id in {str(index), str(row.get("id") or ""), str(row.get("candidate_id") or "")}:
                return index
        raise FileNotFoundError(candidate_id)

    def _candidate_decision(self, row: dict[str, Any]) -> str:
        return str(row.get("gate1_decision") or row.get("decision") or "pending").lower()

    def _delete_candidate_artifacts(self, batch_dir: Path, row: dict[str, Any]) -> None:
        for key in ("result_path", "landing_path"):
            raw_path = str(row.get(key) or "").strip()
            if not raw_path:
                continue
            target = self._resolve_managed_path(raw_path, batch_dir)
            if target is None or not target.exists():
                continue
            if target.is_dir():
                self._delete_tree(target)
            else:
                target.unlink(missing_ok=True)
            self._prune_empty_parents(target.parent, stop_at=self.data_root)

    def _cleanup_batch_if_complete(self, batch_dir: Path, rows: list[dict[str, Any]]) -> None:
        if self._should_delete_batch(batch_dir, rows):
            self._delete_tree(batch_dir)
            self._prune_empty_parents(batch_dir.parent, stop_at=self.data_root)

    def _should_delete_batch(self, batch_dir: Path, rows: list[dict[str, Any]]) -> bool:
        pending_total = len([row for row in rows if self._candidate_decision(row) == "pending"])
        if pending_total > 0:
            return False
        return any((batch_dir / name).exists() for name in ("candidates.json", "results", "search.md", "review.md"))

    def _rebuild_candidates(self, batch_dir: Path) -> list[dict[str, Any]]:
        from_results = self._rebuild_candidates_from_results(batch_dir)
        by_title = {
            str(row.get("title") or "").strip(): row
            for row in from_results
            if str(row.get("title") or "").strip()
        }
        by_slug = {
            slugify(str(row.get("title") or "").strip(), fallback=str(row.get("id") or "candidate")): row
            for row in from_results
            if str(row.get("title") or "").strip()
        }

        restored: list[dict[str, Any]] = []
        for row in self._rebuild_candidates_from_search_report(batch_dir):
            title = str(row.get("title") or "").strip()
            slug = slugify(title, fallback=str(row.get("id") or "candidate"))
            merged = merge_metadata(row, by_title.get(title, {}), by_slug.get(slug, {}))
            merged.setdefault("id", merged.get("candidate_id") or slugify(title, fallback=title or "candidate"))
            merged.setdefault("candidate_id", merged.get("id"))
            restored.append(merged)

        if restored:
            return restored
        return from_results

    def _rebuild_candidates_from_results(self, batch_dir: Path) -> list[dict[str, Any]]:
        results_dir = batch_dir / "results"
        if not results_dir.exists():
            return []

        candidates: list[dict[str, Any]] = []
        for metadata_path in sorted(results_dir.rglob("metadata.json")):
            payload = read_json(metadata_path)
            if not isinstance(payload, dict):
                continue
            row = dict(payload)
            row.setdefault("id", metadata_path.parent.name)
            row.setdefault("candidate_id", metadata_path.parent.name)
            row.setdefault("result_path", self._relative_results_path(metadata_path.parent))
            row.setdefault("landing_path", row.get("landing_path") or row.get("result_path") or "")
            candidates.append(row)
        return candidates

    def _promote_candidate_to_acquire(self, batch_dir: Path, row: dict[str, Any]) -> None:
        title = str(row.get("title") or "").strip()
        slug = slugify(title, fallback=str(row.get("candidate_id") or row.get("id") or "candidate"))
        target_dir = self._unique_acquire_target(slug)
        target_dir.mkdir(parents=True, exist_ok=True)

        source_path = self._resolve_candidate_source_path(batch_dir, row)
        source_metadata = self._source_metadata(source_path) if source_path and source_path.exists() else {}
        if source_path and source_path.exists():
            if source_path.is_dir():
                for item in sorted(source_path.iterdir(), key=lambda path: path.name):
                    destination = target_dir / item.name
                    if item.is_dir():
                        self._transfer_tree(item, destination, move=True)
                    else:
                        self._transfer_file(item, destination, move=True)
                source_path.rmdir()
                self._prune_empty_parents(source_path.parent, stop_at=self.data_root)
            elif source_path.is_file():
                destination = target_dir / ("paper.pdf" if source_path.suffix.lower() == ".pdf" else source_path.name)
                self._transfer_file(source_path, destination, move=True)
                self._prune_empty_parents(source_path.parent, stop_at=self.data_root)

        metadata = merge_metadata(
            source_metadata,
            {
                "title": title,
                "year": row.get("year"),
                "venue": row.get("venue"),
                "doi": row.get("doi"),
                "domain": row.get("domain"),
                "area": row.get("area") or row.get("subdomain"),
                "topic": row.get("topic"),
                "paper_type": row.get("paper_type"),
                "collection_role": row.get("collection_role"),
                "source_type": row.get("source_type"),
                "paper_url": row.get("paper_url"),
                "pdf_url": row.get("pdf_url"),
                "source_evidence": row.get("source_evidence"),
                "relevance_reason_zh": row.get("relevance_reason_zh"),
                "screening_reason_zh": row.get("screening_reason_zh"),
                "tags": [
                    "paper",
                    "candidate-keep",
                    str(row.get("venue") or "").strip().lower(),
                ],
            },
        )

        note_path = target_dir / "note.md"
        if not note_path.exists():
            write_text(note_path, self._render_note_template(metadata))

        paper_path = target_dir / "paper.pdf"
        status = "processed" if paper_path.exists() else "needs-pdf"
        metadata_to_write = merge_metadata(
            metadata,
            {
                "status": status,
                "updated_at": utc_now(),
                "path": str(target_dir),
                "paper_path": str(paper_path) if paper_path.exists() else "",
                "note_path": str(note_path),
                "refined_path": str(target_dir / "refined.md") if (target_dir / "refined.md").exists() else "",
                "images_path": str(target_dir / "images") if (target_dir / "images").exists() else "",
            },
        )
        write_yaml(target_dir / "metadata.yaml", metadata_to_write)
        self.update_paper_state(
            target_dir,
            {
                "status": status,
                "workflow_status": status,
                "refine_status": "queued" if status == "processed" else "needs-pdf",
                "parser_status": "parse-pending" if status == "processed" else "needs-pdf",
                "note_status": "template",
                "read_status": "unread",
                "classification_status": "pending",
                "error": "",
            },
        )

    def _resolve_candidate_source_path(self, batch_dir: Path, row: dict[str, Any]) -> Path | None:
        for key in ("result_path", "landing_path"):
            raw_path = str(row.get(key) or "").strip()
            if not raw_path:
                continue
            target = self._resolve_managed_path(raw_path, batch_dir)
            if target and target.exists():
                return target
        return None

    def _unique_acquire_target(self, slug: str) -> Path:
        base = self.acquire_root / "curated" / slug
        if not base.exists():
            return base
        index = 2
        while True:
            candidate = self.acquire_root / "curated" / f"{slug}-{index}"
            if not candidate.exists():
                return candidate
            index += 1

    def _rebuild_candidates_from_search_report(self, batch_dir: Path) -> list[dict[str, Any]]:
        search_path = batch_dir / "search.md"
        if not search_path.exists():
            return []

        content = read_text(search_path)
        match = re.search(r"## Candidates\s*\n\n((?:\|.*\n)+)", content)
        if not match:
            return []

        lines = [line.strip() for line in match.group(1).splitlines() if line.strip()]
        if len(lines) < 3:
            return []

        rows: list[dict[str, Any]] = []
        for line in lines[2:]:
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if len(cells) < 8:
                continue
            venue, year, paper_type, title, paper_cell, pdf_cell, relevance, local_status = cells[:8]
            paper_url = self._extract_markdown_link_target(paper_cell)
            pdf_target = self._extract_markdown_link_target(pdf_cell)
            rows.append(
                {
                    "id": slugify(title, fallback=title or "candidate"),
                    "candidate_id": slugify(title, fallback=title or "candidate"),
                    "title": title,
                    "authors": [],
                    "year": year,
                    "venue": venue,
                    "paper_type": paper_type,
                    "collection_role": self._infer_collection_role(paper_type),
                    "paper_url": paper_url,
                    "pdf_url": pdf_target if pdf_target.startswith("http") else "",
                    "source_type": "local",
                    "source_quality": "search-report",
                    "relevance_reason_zh": relevance,
                    "screening_reason_zh": relevance,
                    "landing_status": self._infer_landing_status(pdf_cell, local_status),
                    "landing_path": self._extract_local_path(pdf_target, local_status),
                    "result_path": self._extract_result_path(batch_dir, title),
                }
            )
        return rows

    def _extract_markdown_link_target(self, cell: str) -> str:
        match = re.search(r"\[[^\]]*\]\(([^)]+)\)", cell)
        return match.group(1).strip() if match else ""

    def _extract_local_path(self, pdf_target: str, local_status: str) -> str:
        if pdf_target and not pdf_target.startswith("http"):
            return pdf_target
        local_match = re.search(r"PDF downloaded:\s*([^\s].+)$", local_status)
        return local_match.group(1).strip() if local_match else ""

    def _extract_result_path(self, batch_dir: Path, title: str) -> str:
        results_dir = batch_dir / "results"
        if not results_dir.exists():
            return ""
        expected_slug = slugify(title, fallback=title or "candidate")
        for candidate_dir in results_dir.iterdir():
            if not candidate_dir.is_dir():
                continue
            if candidate_dir.name.startswith(expected_slug):
                return self._relative_results_path(candidate_dir)
        return ""

    def _infer_collection_role(self, paper_type: str) -> str:
        normalized = paper_type.strip().lower()
        if normalized == "benchmark":
            return "Core"
        if "survey" in normalized:
            return "Survey"
        if "application" in normalized:
            return "Application"
        return "Method"

    def _infer_landing_status(self, pdf_cell: str, local_status: str) -> str:
        if "PDF pending download" in pdf_cell or "pending" in local_status.lower():
            return "metadata-only"
        if "PDF downloaded" in local_status or "paper.pdf" in pdf_cell:
            return "pdf-downloaded"
        return "metadata-only"

    def _relative_results_path(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.data_root)).replace("\\", "/")
        except ValueError:
            return str(path)

    def _resolve_managed_path(self, raw_path: str, batch_dir: Path) -> Path | None:
        candidate = Path(raw_path)
        search_paths = [candidate]
        if not candidate.is_absolute():
            search_paths = [batch_dir / candidate, self.data_root / candidate]
        fallback: Path | None = None
        for path in search_paths:
            resolved = path.resolve(strict=False)
            if not self._is_within_root(resolved):
                continue
            if resolved.exists():
                return resolved
            if fallback is None:
                fallback = resolved
        return fallback

    def _delete_tree(self, path: Path) -> None:
        if path.exists():
            shutil.rmtree(path, onexc=self._handle_remove_readonly)

    def _handle_remove_readonly(self, func: Any, target: str, excinfo: Any) -> None:
        os.chmod(target, 0o700)
        func(target)

    def _prune_empty_parents(self, path: Path, *, stop_at: Path) -> None:
        current = path
        resolved_stop = stop_at.resolve(strict=False)
        while self._is_within_root(current) and current.resolve(strict=False) != resolved_stop:
            try:
                current.rmdir()
            except OSError:
                break
            current = current.parent

    def _is_within_root(self, path: Path) -> bool:
        try:
            path.resolve(strict=False).relative_to(self.data_root.resolve(strict=False))
            return True
        except ValueError:
            return False

    def _render_note_template(self, metadata: dict[str, Any]) -> str:
        template_path = self.template_root / "paper-note-template.md"
        template = read_text(template_path) if template_path.exists() else DEFAULT_NOTE_TEMPLATE
        tags = metadata.get("tags") or ["paper"]
        tag_lines = "\n".join(f"  - {tag}" for tag in tags)
        return Template(template).safe_substitute(title=metadata.get("title") or "", year=metadata.get("year") or "", venue=metadata.get("venue") or "", doi=metadata.get("doi") or "", domain=metadata.get("domain") or "", area=metadata.get("area") or "", topic=metadata.get("topic") or "", status=metadata.get("status") or "draft", tags=tag_lines)

    def _resolve_target_path(self, metadata: dict[str, Any], slug: str, target_path: str | None = None) -> Path:
        if target_path:
            return self.library_root / target_path
        domain = str(metadata.get("domain") or "").strip()
        area = str(metadata.get("area") or metadata.get("subdomain") or "").strip()
        topic = str(metadata.get("topic") or "").strip()
        if not domain:
            return self.library_root / "unclassified" / slug
        return self.library_root.joinpath(*[part for part in (domain, area, topic, slug) if part])

    def _copy_source_assets(self, source: Path, target: Path, *, move: bool) -> None:
        if source.is_file():
            if source.suffix.lower() == ".pdf":
                self._transfer_file(source, target / "paper.pdf", move=move)
            elif source.suffix.lower() in {".md", ".markdown"}:
                self._transfer_file(source, target / "note.md", move=move)
            return
        for item in sorted(source.iterdir(), key=lambda path: path.name):
            destination = target / item.name
            if item.is_dir():
                self._transfer_tree(item, destination, move=move)
            else:
                self._transfer_file(item, destination, move=move)
        if move and source.exists():
            try:
                source.rmdir()
            except OSError:
                pass

    def _transfer_file(self, source: Path, destination: Path, *, move: bool) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if move:
            shutil.move(str(source), str(destination))
            return
        shutil.copy2(source, destination)

    def _transfer_tree(self, source: Path, destination: Path, *, move: bool) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if move:
            shutil.move(str(source), str(destination))
            return
        shutil.copytree(source, destination, dirs_exist_ok=True)

    def _safe_json_object(self, path: Path) -> dict[str, Any]:
        try:
            data = read_json(path)
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def _parser_runs(self, paper_dir: Path) -> list[dict[str, Any]]:
        try:
            data = read_json(paper_dir / "parser_runs.json")
        except (OSError, ValueError):
            return []
        return data if isinstance(data, list) else []

    def _parser_run_record(self, row: dict[str, Any], paper_id: str) -> ParserRunRecord:
        return ParserRunRecord(run_id=str(row.get("run_id") or ""), paper_id=paper_id, status=str(row.get("status") or ""), parser=str(row.get("parser") or ""), source_pdf=str(row.get("source_pdf") or ""), refined_path=str(row.get("refined_path") or ""), image_dir=str(row.get("image_dir") or ""), text_path=str(row.get("text_path") or ""), sections_path=str(row.get("sections_path") or ""), error=str(row.get("error") or ""), started_at=str(row.get("started_at") or ""), finished_at=str(row.get("finished_at") or ""))

    def _resolved_status(self, metadata: dict[str, Any], paper_path: Path) -> str:
        if metadata.get("rejected"):
            return "rejected"
        status = str(metadata.get("workflow_status") or metadata.get("status") or "").strip()
        if status:
            return status
        return "processed" if paper_path.exists() else "needs-pdf"

    def _status_from_parser(self, parser_status: str) -> str:
        if parser_status == "processed":
            return "processed"
        if parser_status == "failed":
            return "parse-failed"
        if parser_status == "needs-pdf":
            return "needs-pdf"
        return "needs-review" if parser_status in {"pending", "skipped"} else "parse-pending"

    def _require_paper_dir(self, paper_id: str) -> Path:
        paper_dir = self.get_paper_dir(paper_id)
        if paper_dir is None:
            raise FileNotFoundError(paper_id)
        return paper_dir

    def _relative_id(self, path: Path) -> str:
        return str(path.relative_to(self.data_root)).replace("\\", "__").replace("/", "__")

    def _paper_stage(self, path: Path) -> str:
        if self.acquire_root in path.parents:
            return "acquire"
        if self.library_root in path.parents:
            return "library"
        return "unknown"

    def _mtime(self, path: Path) -> str:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()

    def _int_or_none(self, value: Any) -> int | None:
        try:
            return int(value) if value not in (None, "") else None
        except (TypeError, ValueError):
            return None

    def _bounded_score(self, value: Any, default: int) -> int:
        try:
            score = int(value)
        except (TypeError, ValueError):
            score = default
        return max(0, min(100, score))
