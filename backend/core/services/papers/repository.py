from __future__ import annotations

import json
import os
import re
import shutil
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from string import Template
from typing import Any

from backend.core.services.papers.models import (
    BatchRecord,
    CandidateRecord,
    GenerateNoteInput,
    ImportPaperInput,
    IngestPaperInput,
    PaperCapabilities,
    PaperEventRecord,
    PaperRecord,
    ParserArtifacts,
    ParserRunRecord,
    ReviewDecisionInput,
    UpdateClassificationInput,
)
from backend.core.services.papers.layouts import PaperDataLayout, resolve_data_layout
from backend.core.services.papers.parser import PdfParserResult
from backend.core.services.papers.utils import load_markdown_front_matter, merge_metadata, read_json, read_text, read_yaml, slugify, split_front_matter, utc_now, write_json, write_text, write_yaml


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


DEFAULT_SEARCH_AGENT_SETTINGS = {
    "command_template": "",
    "prompt_template": (
        "请围绕 {keywords} 检索候选论文。\n"
        "Venue: {venue}\n"
        "Year range: {year_start}-{year_end}\n"
        "Source: {source}\n"
        "Max results: {max_results}\n\n"
        "请输出结构化 candidates.json，字段至少包含 title、authors、year、venue、doi、arxiv_id、url、abstract、relevance。"
    ),
    "max_results": 20,
    "default_source": "manual",
}


class PaperRepository:
    def __init__(self, data_root: Path, data_layout: str = "native") -> None:
        self.layout: PaperDataLayout = resolve_data_layout(data_root, data_layout)
        self.data_root = self.layout.data_root
        self.data_layout = self.layout.name
        self.discover_root = self.layout.discover_root
        self.search_batches_root = self.layout.search_batches_root
        self.acquire_root = self.layout.acquire_root
        self.curated_root = self.layout.curated_root
        self.library_root = self.layout.library_root
        self.legacy_library_roots = tuple(root for root in self.layout.legacy_library_roots if root != self.library_root)
        self.archive_root = self.layout.archive_root
        self.template_root = self.layout.template_root
        self.ensure_layout()

    def ensure_layout(self) -> None:
        for path in self.layout.ensure_paths():
            path.mkdir(parents=True, exist_ok=True)

    def list_papers(self) -> list[PaperRecord]:
        paper_dirs: set[Path] = set()
        for root in self._active_paper_roots():
            if not root.exists():
                continue
            for name in ("metadata.yaml", "metadata.json", "state.json", "paper.pdf", "note.md"):
                paper_dirs.update(path.parent for path in root.rglob(name) if path.parent.is_dir())
        records = [self._paper_record_from_dir(paper_dir) for paper_dir in paper_dirs]
        return sorted(records, key=lambda item: (item.updated_at, item.title), reverse=True)

    def list_batches(self) -> list[BatchRecord]:
        batches_root = self.search_batches_root
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
        batch_dir = self.search_batches_root / batch_id
        candidates_path = batch_dir / "candidates.json"
        data = read_json(candidates_path)
        rows = self._rows_from_candidate_data(data)
        target_index = self._candidate_index(rows, candidate_id)
        row = rows[target_index]
        candidate = self._candidate_record(batch_id, target_index, row, utc_now())
        if decision == "reset":
            row.pop("gate1_decision", None)
        elif decision == "keep":
            self._promote_candidate_to_library(batch_dir, row)
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
        batch_dir = self.search_batches_root / batch_id
        if not batch_dir.exists():
            raise FileNotFoundError(batch_id)

        candidates = self._rebuild_candidates(batch_dir)
        self._write_candidate_data(batch_dir / "candidates.json", [], candidates)
        return candidates

    def cleanup_batches(self) -> list[str]:
        removed: list[str] = []
        batches_root = self.search_batches_root
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
        batch_dir = self.search_batches_root / batch_id
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
        candidate = self._paper_dir_from_id(paper_id)
        if candidate is not None:
            return candidate
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

        asset_status = "pdf_ready" if (target / "paper.pdf").exists() else "missing_pdf"
        metadata_to_write = merge_metadata(
            metadata,
            {
                "updated_at": utc_now(),
                "path": str(target),
                "paper_path": str(target / "paper.pdf") if (target / "paper.pdf").exists() else "",
                "note_path": str(target / "note.md"),
                "refined_path": str(target / "refined.md") if (target / "refined.md").exists() else "",
                "images_path": str(target / "images") if (target / "images").exists() else "",
                "tags": metadata.get("tags") or ["paper"],
                "asset_status": asset_status,
                "parser_status": "not_started",
                "review_status": "pending",
                "note_status": "template" if (target / "note.md").exists() else "missing",
            },
        )
        write_yaml(target / "metadata.yaml", metadata_to_write)
        self.update_paper_state(
            target,
            {
                "asset_status": asset_status,
                "parser_status": "not_started",
                "review_status": "pending",
                "note_status": "template" if (target / "note.md").exists() else "missing",
                "read_status": "unread",
                "classification_status": "pending",
                "error": "",
            },
        )
        return self._paper_record_from_dir(target)

    def migrate(self, request: IngestPaperInput) -> PaperRecord:
        return self.ingest(IngestPaperInput(source=request.source, domain=request.domain, area=request.area, topic=request.topic, target_path=request.target_path, move=True))

    def import_paper(self, request: ImportPaperInput) -> PaperRecord:
        title = request.title.strip()
        if not title:
            raise ValueError("Title is required")

        source = request.source.expanduser().resolve(strict=False) if request.source else None
        if source is not None and not source.exists():
            raise FileNotFoundError(source)

        source_metadata = self._source_metadata(source) if source else {}
        metadata = merge_metadata(
            source_metadata,
            {
                "title": title,
                "authors": [author.strip() for author in request.authors if author.strip()],
                "year": request.year,
                "venue": request.venue.strip(),
                "doi": request.doi.strip(),
                "arxiv_id": request.arxiv_id.strip(),
                "url": request.url.strip(),
                "abstract": request.abstract.strip(),
                "summary": request.summary.strip(),
                "domain": request.domain.strip(),
                "area": request.area.strip(),
                "topic": request.topic.strip(),
                "tags": request.tags or ["paper"],
            },
        )
        slug = slugify(title, fallback="paper")
        target_dir = self._unique_library_target(self._resolve_target_path(metadata, slug))
        target_dir.mkdir(parents=True, exist_ok=True)

        if source is not None:
            self._copy_source_assets(source, target_dir, move=False)

        note_path = target_dir / "note.md"
        if not note_path.exists():
            write_text(note_path, self._render_note_template(metadata))

        paper_path = target_dir / "paper.pdf"
        asset_status = "pdf_ready" if paper_path.exists() else "missing_pdf"
        classification_status = "accepted" if metadata.get("domain") and metadata.get("area") and metadata.get("topic") else "pending"
        payload = merge_metadata(
            metadata,
            {
                "updated_at": utc_now(),
                "path": str(target_dir),
                "paper_path": str(paper_path) if paper_path.exists() else "",
                "note_path": str(note_path),
                "asset_status": asset_status,
                "parser_status": "not_started",
                "review_status": "accepted",
                "note_status": "template" if note_path.exists() else "missing",
                "read_status": "unread",
                "classification_status": classification_status,
                "metadata_import_mode": "manual",
            },
        )
        write_yaml(target_dir / "metadata.yaml", payload)
        self.update_paper_state(
            target_dir,
            {
                "asset_status": asset_status,
                "parser_status": "not_started",
                "review_status": "accepted",
                "note_status": "template" if note_path.exists() else "missing",
                "read_status": "unread",
                "classification_status": classification_status,
                "metadata_import_mode": "manual",
                "error": "",
            },
        )
        self._append_event(
            target_dir,
            "paper_imported",
            actor="user",
            result="success",
            message="论文已手动导入文库。",
            technical_detail=f"title={title}; source={source or ''}",
            next_action="可按需刷新元数据或绑定 PDF。",
        )
        return self._paper_record_from_dir(target_dir)

    def generate_note_template(self, request: GenerateNoteInput) -> str:
        return self._render_note_template(request.to_metadata())

    def generate_note_for_paper(self, paper_id: str, *, overwrite: bool = False) -> PaperRecord:
        paper_dir = self._require_paper_dir(paper_id)
        note_path = paper_dir / "note.md"
        if note_path.exists() and not overwrite:
            return self._paper_record_from_dir(paper_dir)

        record = self._paper_record_from_dir(paper_dir)
        if record.parser_status != "parsed":
            raise ValueError("Paper must be parsed before generating note")
        if record.refined_review_status != "approved":
            raise ValueError("Refined document must be approved before generating note")

        self._append_event(
            paper_dir,
            "llm_note_started",
            actor="system",
            result="pending",
            message="开始生成 LLM note。",
            next_action="等待 note 生成完成。",
        )
        content = self._render_note_template(self._paper_metadata(paper_dir))
        write_text(note_path, content)
        self.update_paper_state(
            paper_dir,
            {
                "note_status": "review_pending",
                "note_review_status": "pending",
                "note_path": str(note_path),
                "error": "",
            },
        )
        self._append_event(
            paper_dir,
            "llm_note_generated",
            actor="llm",
            result="pending",
            message="LLM note 已生成，等待人工审核。",
            next_action="请审核 note 内容。",
        )
        return self._paper_record_from_dir(paper_dir)

    def update_paper_state(self, paper_dir: Path, updates: dict[str, Any]) -> dict[str, Any]:
        state_path = paper_dir / "state.json"
        metadata_json_path = paper_dir / "metadata.json"
        state = self._safe_json_object(state_path)
        metadata = self._safe_json_object(metadata_json_path)
        payload = merge_metadata(self._source_metadata(paper_dir), metadata, state, updates, {"updated_at": utc_now()})
        payload = self._normalize_paper_payload(paper_dir, payload)
        payload = self._apply_explicit_clears(payload, updates)
        state_payload = merge_metadata(state, updates, {"updated_at": payload["updated_at"]})
        state_payload = self._apply_explicit_clears(state_payload, updates)
        write_json(state_path, state_payload)
        write_json(metadata_json_path, payload)
        if (paper_dir / "metadata.yaml").exists():
            yaml_payload = merge_metadata(read_yaml(paper_dir / "metadata.yaml"), payload)
            yaml_payload = self._apply_explicit_clears(yaml_payload, updates)
            write_yaml(paper_dir / "metadata.yaml", yaml_payload)
        return payload

    def update_metadata(self, paper_id: str, updates: dict[str, Any]) -> PaperRecord:
        paper_dir = self._require_paper_dir(paper_id)
        clean_updates = self._metadata_payload(updates)
        if any(key in clean_updates for key in ("domain", "area", "topic")):
            clean_updates["classification_status"] = "classified" if str(clean_updates.get("domain") or "").strip() else "pending"
        record = self._paper_record_from_dir(paper_dir)
        should_move = record.stage == "library" and any(key in clean_updates for key in ("title", "domain", "area", "topic"))
        if should_move:
            metadata = self._apply_explicit_clears(merge_metadata(self._paper_metadata(paper_dir), clean_updates), clean_updates)
            slug = slugify(str(metadata.get("title") or paper_dir.name), fallback=paper_dir.name)
            target_dir = self._resolve_target_path(metadata, slug)
            if target_dir.resolve(strict=False) != paper_dir.resolve(strict=False):
                if target_dir.exists():
                    target_dir = self._unique_library_target(target_dir)
                source_parent = paper_dir.parent
                self._transfer_tree(paper_dir, target_dir, move=True)
                self._prune_empty_parents(source_parent, stop_at=self.library_root)
                paper_dir = target_dir

        self.update_paper_state(paper_dir, self._apply_explicit_clears(merge_metadata(clean_updates, {"error": ""}), clean_updates))
        self._append_event(
            paper_dir,
            "metadata_updated",
            actor="user",
            result="success",
            message="元数据已更新。",
            technical_detail=", ".join(sorted(clean_updates.keys())),
            next_action="检查文库显示与分类路径是否符合预期。",
        )
        return self._paper_record_from_dir(paper_dir)

    def refresh_metadata(self, paper_id: str, query: dict[str, Any] | None = None) -> PaperRecord:
        paper_dir = self._require_paper_dir(paper_id)
        metadata = self._paper_metadata(paper_dir)
        query = self._metadata_payload(query or {})
        title = str(query.get("title") or metadata.get("title") or paper_dir.name).strip()
        doi = str(query.get("doi") or metadata.get("doi") or "").strip()
        arxiv_id = str(query.get("arxiv_id") or metadata.get("arxiv_id") or "").strip()
        url = str(query.get("url") or metadata.get("url") or metadata.get("paper_url") or "").strip()
        now = utc_now()

        inferred = self._infer_metadata_fields(
            {
                "title": title,
                "doi": doi,
                "arxiv_id": arxiv_id,
                "url": url,
                "authors": metadata.get("authors"),
                "abstract": metadata.get("abstract"),
                "summary": metadata.get("summary"),
                "venue": metadata.get("venue"),
                "year": metadata.get("year"),
            }
        )
        updates = self._metadata_payload(inferred)
        payload = self.update_paper_state(paper_dir, updates)

        sources_payload = {
            "updated_at": now,
            "query": {
                "title": title,
                "doi": doi,
                "arxiv_id": arxiv_id,
                "url": url,
            },
            "sources": [
                {
                    "provider": "local-refresh",
                    "confidence": 0.55 if title else 0.0,
                    "raw": {
                        "title": title,
                        "doi": doi,
                        "arxiv_id": arxiv_id,
                        "url": url,
                    },
                }
            ],
            "field_provenance": {
                key: "local-refresh"
                for key, value in updates.items()
                if value not in (None, "", [], {})
            },
        }
        write_json(paper_dir / "metadata_sources.json", sources_payload)
        self._append_jsonl(
            paper_dir / "metadata_refresh.jsonl",
            {
                "timestamp": now,
                "query": sources_payload["query"],
                "updated_fields": sorted(updates.keys()),
                "confidence": sources_payload["sources"][0]["confidence"],
            },
        )
        self._append_event(
            paper_dir,
            "metadata_refreshed",
            actor="system",
            result="success",
            message="元数据刷新记录已写入。",
            technical_detail=f"updated_fields={','.join(sorted(updates.keys()))}",
            next_action="检查 metadata_sources.json 中的字段来源。",
        )
        return self._paper_record_from_dir(Path(str(payload.get("path") or paper_dir)))

    def metadata_sources(self, paper_id: str) -> dict[str, Any]:
        paper_dir = self._require_paper_dir(paper_id)
        return self._safe_json_object(paper_dir / "metadata_sources.json")

    def paper_content(self, paper_id: str, *, max_chars: int = 4000) -> dict[str, Any]:
        paper_dir = self._require_paper_dir(paper_id)
        metadata = self._paper_metadata(paper_dir)
        note_text = self._read_artifact_body(paper_dir / "note.md", max_chars=max_chars)
        refined_text = self._read_artifact_body(paper_dir / "refined.md", max_chars=max_chars)
        parsed_text = self._read_artifact_body(paper_dir / "parsed" / "text.md", max_chars=max_chars)
        summary = str(metadata.get("summary") or "")
        abstract = str(metadata.get("abstract") or metadata.get("abstract_zh") or "")
        return {
            "paper_id": self._relative_id(paper_dir),
            "abstract": abstract,
            "summary": summary,
            "note_preview": note_text,
            "refined_preview": refined_text,
            "parsed_preview": parsed_text,
            "sources": {
                "abstract": "metadata.json" if abstract else "",
                "summary": "metadata.json" if summary else "",
                "note_preview": "note.md" if note_text else "",
                "refined_preview": "refined.md" if refined_text else "",
                "parsed_preview": "parsed/text.md" if parsed_text else "",
            },
        }

    def set_starred(self, paper_id: str, starred: bool) -> PaperRecord:
        paper_dir = self._require_paper_dir(paper_id)
        self.update_paper_state(paper_dir, {"starred": bool(starred)})
        return self._paper_record_from_dir(paper_dir)

    def list_research_logs(self, paper_id: str) -> list[dict[str, Any]]:
        paper_dir = self._require_paper_dir(paper_id)
        logs = self._read_jsonl(paper_dir / "research_logs.jsonl")
        return sorted(logs, key=lambda item: str(item.get("timestamp") or ""), reverse=True)

    def create_research_log(self, paper_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        paper_dir = self._require_paper_dir(paper_id)
        now = utc_now()
        log_id = slugify(str(payload.get("title") or "research-log"), fallback="research-log")
        existing_ids = {str(item.get("id") or "") for item in self.list_research_logs(paper_id)}
        if log_id in existing_ids:
            log_id = f"{log_id}-{len(existing_ids) + 1}"
        log = self._normalize_research_log(merge_metadata(payload, {"id": log_id, "timestamp": now, "updated_at": now}))
        self._append_jsonl(paper_dir / "research_logs.jsonl", log)
        self.update_paper_state(paper_dir, {"research_log_status": "ready"})
        return log

    def update_research_log(self, paper_id: str, log_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        paper_dir = self._require_paper_dir(paper_id)
        logs = self.list_research_logs(paper_id)
        updated: dict[str, Any] | None = None
        next_logs: list[dict[str, Any]] = []
        for log in logs:
            if str(log.get("id") or "") == log_id:
                updated = self._normalize_research_log(merge_metadata(log, payload, {"id": log_id, "updated_at": utc_now()}))
                next_logs.append(updated)
            else:
                next_logs.append(log)
        if updated is None:
            raise FileNotFoundError(log_id)
        self._write_jsonl(paper_dir / "research_logs.jsonl", sorted(next_logs, key=lambda item: str(item.get("timestamp") or "")))
        return updated

    def delete_research_log(self, paper_id: str, log_id: str) -> None:
        paper_dir = self._require_paper_dir(paper_id)
        logs = self.list_research_logs(paper_id)
        next_logs = [log for log in logs if str(log.get("id") or "") != log_id]
        if len(next_logs) == len(logs):
            raise FileNotFoundError(log_id)
        self._write_jsonl(paper_dir / "research_logs.jsonl", sorted(next_logs, key=lambda item: str(item.get("timestamp") or "")))

    def bind_assets(self, paper_id: str, source: Path, *, move: bool = False) -> PaperRecord:
        paper_dir = self._require_paper_dir(paper_id)
        resolved = source.expanduser().resolve(strict=False)
        if not resolved.exists():
            raise FileNotFoundError(resolved)
        self._copy_source_assets(resolved, paper_dir, move=move)
        asset_status = "pdf_ready" if (paper_dir / "paper.pdf").exists() else "missing_pdf"
        self.update_paper_state(paper_dir, {"asset_status": asset_status, "error": ""})
        return self._paper_record_from_dir(paper_dir)

    def get_search_agent_settings(self) -> dict[str, Any]:
        path = self._settings_root() / "search_agent.json"
        stored = self._safe_json_object(path)
        return merge_metadata(DEFAULT_SEARCH_AGENT_SETTINGS, stored)

    def update_search_agent_settings(self, updates: dict[str, Any]) -> dict[str, Any]:
        current = self.get_search_agent_settings()
        next_payload = merge_metadata(current, self._search_settings_payload(updates), {"updated_at": utc_now()})
        prompt = str(next_payload.get("prompt_template") or "")
        if "{keywords}" not in prompt:
            raise ValueError("prompt_template must include {keywords}")
        if int(next_payload.get("max_results") or 0) <= 0:
            raise ValueError("max_results must be positive")
        write_json(self._settings_root() / "search_agent.json", next_payload)
        return next_payload

    def create_search_batch(self, request: dict[str, Any]) -> dict[str, Any]:
        keywords = str(request.get("keywords") or "").strip()
        if not keywords:
            raise ValueError("keywords is required")
        settings = self.get_search_agent_settings()
        max_results = self._int_or_none(request.get("max_results")) or int(settings.get("max_results") or 20)
        source = str(request.get("source") or settings.get("default_source") or "manual")
        batch_id = self._unique_search_batch_id(slugify(keywords, fallback="search"))
        batch_dir = self.search_batches_root / batch_id
        batch_dir.mkdir(parents=True, exist_ok=True)
        variables = {
            "keywords": keywords,
            "venue": str(request.get("venue") or ""),
            "year_start": str(request.get("year_start") or ""),
            "year_end": str(request.get("year_end") or ""),
            "source": source,
            "max_results": str(max_results),
        }
        prompt = self._render_prompt_template(str(settings.get("prompt_template") or ""), variables)
        command = self._render_prompt_template(str(settings.get("command_template") or ""), variables)
        candidates = self._seed_candidates_from_keywords(batch_id, keywords, variables, max_results)
        job = {
            "job_id": batch_id,
            "batch_id": batch_id,
            "status": "created",
            "keywords": keywords,
            "source": source,
            "command_template": settings.get("command_template") or "",
            "rendered_command": command,
            "prompt_template": settings.get("prompt_template") or "",
            "rendered_prompt": prompt,
            "created_at": utc_now(),
            "updated_at": utc_now(),
        }
        write_text(batch_dir / "search.md", prompt)
        write_json(batch_dir / "job.json", job)
        write_json(batch_dir / "candidates.json", {"candidates": candidates})
        return {
            "job": job,
            "batch": self._batch_record_from_dir(batch_dir).to_dict(),
            "candidates": [self._candidate_record(batch_id, index, row, job["updated_at"]).to_dict() for index, row in enumerate(candidates)],
        }

    def get_search_job(self, job_id: str) -> dict[str, Any]:
        batch_dir = self.search_batches_root / job_id
        if not batch_dir.exists():
            raise FileNotFoundError(job_id)
        job = self._safe_json_object(batch_dir / "job.json")
        if not job:
            job = {
                "job_id": job_id,
                "batch_id": job_id,
                "status": "unknown",
                "updated_at": self._mtime(batch_dir),
            }
        return job

    def set_candidate_batch_decision(self, batch_id: str, candidate_ids: list[str], decision: str) -> list[CandidateRecord]:
        if not candidate_ids:
            candidate_ids = [candidate.candidate_id for candidate in self.list_candidates(batch_id) if candidate.decision == "pending"]
        records: list[CandidateRecord] = []
        for candidate_id in candidate_ids:
            records.append(self.set_candidate_decision(batch_id, candidate_id, decision))
        return records

    def mark_status(self, paper_id: str, status: str) -> PaperRecord:
        paper_dir = self._require_paper_dir(paper_id)
        updates = self._legacy_status_updates(status)
        updates["error"] = ""
        self.update_paper_state(paper_dir, updates)
        return self._paper_record_from_dir(paper_dir)

    def accept_paper(self, paper_id: str) -> PaperRecord:
        paper_dir = self._require_paper_dir(paper_id)
        record = self._paper_record_from_dir(paper_dir)
        if record.stage != "acquire":
            raise ValueError("Only acquire papers can be accepted")
        if record.parser_status != "parsed":
            raise ValueError("Paper must be parsed before accept")
        return self.promote_to_library(paper_dir)

    def promote_to_library(self, source_dir: Path) -> PaperRecord:
        metadata = self._paper_metadata(source_dir)
        slug = slugify(str(metadata.get("title") or source_dir.name), fallback=source_dir.name)
        target_dir = self._resolve_target_path(metadata, slug)
        target_dir = self._unique_library_target(target_dir)
        self._transfer_tree(source_dir, target_dir, move=True)
        self._prune_empty_parents(source_dir.parent, stop_at=self.data_root)
        self.update_paper_state(
            target_dir,
            {
                "review_status": "accepted",
                "error": "",
            },
        )
        self._append_event(
            target_dir,
            "accepted_to_library",
            actor="user",
            result="success",
            message="文献已进入 Library。",
            next_action="继续完成 refined 和 note 审核流程。",
        )
        return self._paper_record_from_dir(target_dir)

    def update_classification(self, request: UpdateClassificationInput) -> PaperRecord:
        paper_dir = self._require_paper_dir(request.paper_id)
        record = self._paper_record_from_dir(paper_dir)
        if record.stage != "library":
            raise ValueError("Only library papers can be reclassified")

        updates = self._metadata_updates(request)
        metadata = self._apply_explicit_clears(merge_metadata(self._paper_metadata(paper_dir), updates), updates)
        slug = slugify(str(metadata.get("title") or paper_dir.name), fallback=paper_dir.name)
        target_dir = self._resolve_target_path(metadata, slug)
        if target_dir.resolve(strict=False) != paper_dir.resolve(strict=False):
            if target_dir.exists():
                target_dir = self._unique_library_target(target_dir)
            source_parent = paper_dir.parent
            self._transfer_tree(paper_dir, target_dir, move=True)
            self._prune_empty_parents(source_parent, stop_at=self.library_root)
            paper_dir = target_dir

        self.update_paper_state(
            paper_dir,
            self._apply_explicit_clears(merge_metadata(updates, {"error": ""}), updates),
        )
        self._append_event(
            paper_dir,
            "classification_updated",
            actor="user",
            result="success",
            message="文献分类已更新。",
            technical_detail=f"domain={updates.get('domain', '')}; area={updates.get('area', '')}; topic={updates.get('topic', '')}",
            next_action="检查文献是否已就绪。",
        )
        return self._paper_record_from_dir(paper_dir)

    def create_library_folder(self, relative_path: str) -> Path:
        clean_parts = [part.strip() for part in relative_path.replace("\\", "/").split("/") if part.strip()]
        if not clean_parts:
            raise ValueError("Folder path is required")
        if len(clean_parts) > 3:
            raise ValueError("Library folders support Domain / Area / Topic only")
        if any(part in {".", ".."} for part in clean_parts):
            raise ValueError("Folder path cannot contain relative segments")

        target = self._resolve_library_target_path("/".join(clean_parts))
        target.mkdir(parents=True, exist_ok=True)
        return target

    def reject_paper(self, paper_id: str) -> PaperRecord:
        paper_dir = self._require_paper_dir(paper_id)
        record = self._paper_record_from_dir(paper_dir)
        if self.layout.reject_policy == "archive":
            target_dir = self._unique_archive_target(paper_dir.name)
            self._transfer_tree(paper_dir, target_dir, move=True)
            self._prune_empty_parents(paper_dir.parent, stop_at=self.data_root)
            self._write_archive_state(target_dir, record)
            return replace(record, path=str(target_dir), status="rejected", rejected=True, updated_at=utc_now())
        self._delete_tree(paper_dir)
        self._prune_empty_parents(paper_dir.parent, stop_at=self.data_root)
        return replace(record, status="rejected", rejected=True, updated_at=utc_now())

    def list_parser_runs(self, paper_id: str) -> list[ParserRunRecord]:
        paper_dir = self._require_paper_dir(paper_id)
        runs = self._parser_runs(paper_dir)
        return [self._parser_run_record(item, self._relative_id(paper_dir)) for item in runs]

    def list_paper_events(self, paper_id: str) -> list[PaperEventRecord]:
        paper_dir = self._require_paper_dir(paper_id)
        return [self._event_record(item) for item in self._paper_events(paper_dir)]

    def review_refined(self, request: ReviewDecisionInput) -> PaperRecord:
        paper_dir = self._require_paper_dir(request.paper_id)
        decision = self._review_decision(request.decision)
        record = self._paper_record_from_dir(paper_dir)
        if record.parser_status != "parsed":
            raise ValueError("Paper must be parsed before refined review")
        if not record.refined_path and not record.parser_artifacts.refined_path:
            raise ValueError("Refined document is missing")

        updates: dict[str, Any] = {
            "refined_review_status": decision,
            "error": "",
        }
        if decision == "rejected":
            updates["note_review_status"] = "pending" if record.note_path else "missing"
            updates["note_status"] = "review_pending" if record.note_path else "missing"

        self.update_paper_state(paper_dir, updates)
        self._append_event(
            paper_dir,
            f"refined_review_{decision}",
            actor="user",
            result="success" if decision == "approved" else "rejected",
            message="refined 文档已人工批准。" if decision == "approved" else "refined 文档已被驳回，需要修改后重新审核。",
            technical_detail=request.comment,
            next_action="生成 LLM note。" if decision == "approved" else "修正 refined 文档后重新提交审核。",
        )
        return self._paper_record_from_dir(paper_dir)

    def review_note(self, request: ReviewDecisionInput) -> PaperRecord:
        paper_dir = self._require_paper_dir(request.paper_id)
        decision = self._review_decision(request.decision)
        record = self._paper_record_from_dir(paper_dir)
        if not record.note_path:
            raise ValueError("Note is missing")
        if record.refined_review_status != "approved":
            raise ValueError("Refined document must be approved before note review")

        self.update_paper_state(
            paper_dir,
            {
                "note_review_status": decision,
                "note_status": "ready" if decision == "approved" else "review_pending",
                "error": "",
            },
        )
        self._append_event(
            paper_dir,
            f"note_review_{decision}",
            actor="user",
            result="success" if decision == "approved" else "rejected",
            message="LLM note 已人工批准。" if decision == "approved" else "LLM note 已被驳回，需要修改后重新审核。",
            technical_detail=request.comment,
            next_action="补全分类并进入已就绪。" if decision == "approved" else "修正 note 后重新提交审核。",
        )
        updated = self._paper_record_from_dir(paper_dir)
        if updated.workflow_status == "ready":
            self._append_event(
                paper_dir,
                "workflow_ready",
                actor="system",
                result="success",
                message="文献关键材料和人工审核都已完成。",
                next_action="可用于阅读、引用和项目复用。",
            )
            updated = self._paper_record_from_dir(paper_dir)
        return updated

    def record_parser_result(self, paper_id: str, result: PdfParserResult, *, started_at: str) -> PaperRecord:
        paper_dir = self._require_paper_dir(paper_id)
        finished_at = utc_now()
        parser_status = self._normalized_parser_status(result.status)
        persisted_error = result.error if parser_status == "failed" else ""
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

        self.update_paper_state(
            paper_dir,
            {
                "parser_status": parser_status,
                "refined_review_status": "pending" if parser_status == "parsed" else "",
                "note_review_status": "pending" if parser_status == "parsed" else "",
                "refined_path": result.refined_path,
                "images_path": result.image_dir,
                "parsed_text_path": result.text_path,
                "parsed_sections_path": result.sections_path,
                "pdf_analysis_path": str(paper_dir / "pdf_analysis.json"),
                "error": persisted_error,
            },
        )
        if parser_status == "parsed":
            self._append_event(
                paper_dir,
                "parse_succeeded",
                actor="system",
                result="success",
                message="PDF 解析完成，并写出解析产物。",
                technical_detail=f"parser={result.parser}; refined_path={result.refined_path}",
                next_action="请人工审核 refined 文档。",
            )
            self._append_event(
                paper_dir,
                "refined_generated",
                actor="system",
                result="pending",
                message="refined 文档已生成，等待人工审核。",
                technical_detail=result.refined_path,
                next_action="请审核 refined 文档。",
            )
        elif parser_status == "failed":
            self._append_event(
                paper_dir,
                "parse_failed",
                actor="system",
                result="failed",
                message="PDF 解析失败。",
                technical_detail=result.error,
                next_action="检查错误详情后重试解析。",
            )
        return self._paper_record_from_dir(paper_dir)

    def config_health(self) -> dict[str, Any]:
        paths = {
            "data_root": self.data_root,
            "discover_root": self.discover_root,
            "search_batches_root": self.search_batches_root,
            "library_root": self.library_root,
            "archive_root": self.archive_root,
            "template_root": self.template_root,
        }
        if self.data_layout != "native":
            paths["acquire_root"] = self.acquire_root
            paths["curated_root"] = self.curated_root
        return {
            "data_layout": self.data_layout,
            "data_root": str(self.data_root),
            "write_policy": self.layout.write_policy,
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
        events_path = paper_dir / "events.jsonl"
        parsed_text = paper_dir / "parsed" / "text.md"
        parsed_sections = paper_dir / "parsed" / "sections.json"
        pdf_analysis = paper_dir / "pdf_analysis.json"
        stage = self._paper_stage(paper_dir, metadata)
        asset_status = self._asset_status(metadata, paper_path)
        parser_status = self._parser_status(metadata, paper_dir)
        review_status = self._review_status(metadata)
        note_status = self._note_status(metadata, note_path)
        refined_review_status = self._refined_review_status(metadata, parser_status)
        note_review_status = self._note_review_status(metadata, note_status, note_path)
        classification_status = self._classification_status(metadata)
        workflow_status = self._workflow_status(
            asset_status=asset_status,
            parser_status=parser_status,
            note_status=note_status,
            refined_review_status=refined_review_status,
            note_review_status=note_review_status,
            classification_status=classification_status,
            note_path=note_path,
            error=str(metadata.get("error") or ""),
        )
        parser_artifacts = ParserArtifacts(
            text_path=str(parsed_text) if parsed_text.exists() else str(metadata.get("parsed_text_path") or ""),
            sections_path=str(parsed_sections) if parsed_sections.exists() else str(metadata.get("parsed_sections_path") or ""),
            refined_path=str(refined_path) if refined_path.exists() else str(metadata.get("refined_path") or ""),
        )
        status = self._compat_status(stage, asset_status, parser_status, review_status)
        capabilities = self._capabilities_for(
            stage=stage,
            asset_status=asset_status,
            parser_status=parser_status,
            note_status=note_status,
            refined_review_status=refined_review_status,
            note_review_status=note_review_status,
        )

        return PaperRecord(
            paper_id=self._relative_id(paper_dir),
            title=str(metadata.get("title") or paper_dir.name),
            slug=paper_dir.name,
            stage=stage,
            status=status,
            workflow_status=workflow_status,
            asset_status=asset_status,
            review_status=review_status,
            domain=str(metadata.get("domain") or ""),
            area=str(metadata.get("area") or metadata.get("subdomain") or ""),
            topic=str(metadata.get("topic") or ""),
            year=year,
            venue=str(metadata.get("venue") or ""),
            doi=str(metadata.get("doi") or ""),
            authors=self._string_list(metadata.get("authors")),
            abstract=str(metadata.get("abstract") or metadata.get("abstract_zh") or ""),
            summary=str(metadata.get("summary") or metadata.get("ai_summary") or ""),
            url=str(metadata.get("url") or metadata.get("paper_url") or ""),
            arxiv_id=str(metadata.get("arxiv_id") or metadata.get("arxiv") or ""),
            starred=bool(metadata.get("starred") or False),
            tags=[str(tag) for tag in metadata.get("tags", []) if tag] or ["paper"],
            path=str(paper_dir),
            paper_path=str(paper_path) if paper_path.exists() else "",
            note_path=str(note_path) if note_path.exists() else "",
            refined_path=str(refined_path) if refined_path.exists() else str(metadata.get("refined_path") or ""),
            images_path=str(images_path) if images_path.exists() else str(metadata.get("images_path") or ""),
            metadata_path=str(metadata_yaml) if metadata_yaml.exists() else "",
            metadata_json_path=str(metadata_json) if metadata_json.exists() else "",
            state_path=str(state_path) if state_path.exists() else "",
            events_path=str(events_path) if events_path.exists() else "",
            parsed_text_path=parser_artifacts.text_path,
            parsed_sections_path=parser_artifacts.sections_path,
            pdf_analysis_path=str(pdf_analysis) if pdf_analysis.exists() else str(metadata.get("pdf_analysis_path") or ""),
            parser_status=parser_status,
            note_status=note_status,
            note_review_status=note_review_status,
            parser_artifacts=parser_artifacts,
            capabilities=capabilities,
            read_status=str(metadata.get("read_status") or "unread"),
            refined_review_status=refined_review_status,
            classification_status=classification_status,
            rejected=False,
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
            abstract=str(row.get("abstract") or row.get("abstract_zh") or ""),
            url=str(row.get("url") or row.get("paper_url") or ""),
            doi=str(row.get("doi") or ""),
            arxiv_id=str(row.get("arxiv_id") or row.get("arxiv") or ""),
            pdf_url=str(row.get("pdf_url") or ""),
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
        artifact_root = self._candidate_artifact_root(batch_dir, row)
        if artifact_root and artifact_root.exists():
            if artifact_root.is_dir():
                self._delete_tree(artifact_root)
            else:
                artifact_root.unlink(missing_ok=True)
            self._prune_empty_parents(artifact_root.parent, stop_at=self.data_root)
            return

        for target in self._candidate_managed_targets(batch_dir, row):
            if not target.exists():
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

    def _promote_candidate_to_library(self, batch_dir: Path, row: dict[str, Any]) -> None:
        title = str(row.get("title") or "").strip()
        slug = slugify(title, fallback=str(row.get("candidate_id") or row.get("id") or "candidate"))

        source_path = self._resolve_candidate_source_path(batch_dir, row)
        source_metadata = self._source_metadata(source_path) if source_path and source_path.exists() else {}
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
        target_dir = self._unique_library_target(self._resolve_target_path(metadata, slug))
        target_dir.mkdir(parents=True, exist_ok=True)

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

        note_path = target_dir / "note.md"
        if not note_path.exists():
            write_text(note_path, self._render_note_template(metadata))

        paper_path = target_dir / "paper.pdf"
        asset_status = "pdf_ready" if paper_path.exists() else "missing_pdf"
        classification_status = "accepted" if metadata.get("domain") and metadata.get("area") and metadata.get("topic") else "pending"
        metadata_to_write = merge_metadata(
            metadata,
            {
                "updated_at": utc_now(),
                "path": str(target_dir),
                "paper_path": str(paper_path) if paper_path.exists() else "",
                "note_path": str(note_path),
                "refined_path": str(target_dir / "refined.md") if (target_dir / "refined.md").exists() else "",
                "images_path": str(target_dir / "images") if (target_dir / "images").exists() else "",
                "asset_status": asset_status,
                "parser_status": "not_started",
                "review_status": "accepted",
                "note_status": "template" if note_path.exists() else "missing",
                "read_status": "unread",
                "classification_status": classification_status,
            },
        )
        write_yaml(target_dir / "metadata.yaml", metadata_to_write)
        self.update_paper_state(
            target_dir,
            {
                "asset_status": asset_status,
                "parser_status": "not_started",
                "review_status": "accepted",
                "note_status": "template" if note_path.exists() else "missing",
                "read_status": "unread",
                "classification_status": classification_status,
                "error": "",
            },
        )

    def _resolve_candidate_source_path(self, batch_dir: Path, row: dict[str, Any]) -> Path | None:
        artifact_root = self._candidate_artifact_root(batch_dir, row)
        if artifact_root and artifact_root.exists():
            return artifact_root
        for key in ("result_path", "landing_path"):
            raw_path = str(row.get(key) or "").strip()
            if not raw_path:
                continue
            target = self._resolve_managed_path(raw_path, batch_dir)
            if target and target.exists():
                return target
        return None

    def _candidate_artifact_root(self, batch_dir: Path, row: dict[str, Any]) -> Path | None:
        for key in ("result_path", "note_path", "metadata_path", "pdf_analysis_path", "landing_path"):
            raw_path = str(row.get(key) or "").strip()
            if not raw_path:
                continue
            target = self._resolve_managed_path(raw_path, batch_dir)
            if target is None:
                continue
            if target.exists() and target.is_dir():
                return target
            parent = target.parent
            if self._looks_like_candidate_artifact_dir(parent):
                return parent
        return None

    def _candidate_managed_targets(self, batch_dir: Path, row: dict[str, Any]) -> list[Path]:
        targets: list[Path] = []
        seen: set[Path] = set()
        for key in ("result_path", "landing_path", "note_path", "metadata_path", "pdf_analysis_path"):
            raw_path = str(row.get(key) or "").strip()
            if not raw_path:
                continue
            target = self._resolve_managed_path(raw_path, batch_dir)
            if target is None or target in seen:
                continue
            seen.add(target)
            targets.append(target)
        return targets

    def _looks_like_candidate_artifact_dir(self, path: Path) -> bool:
        if not self._is_within_root(path) or not path.exists() or not path.is_dir():
            return False
        return any((path / name).exists() for name in ("note.md", "metadata.json", "paper.pdf", "pdf_analysis.json"))

    def _unique_acquire_target(self, slug: str) -> Path:
        base = self.curated_root / slug
        if not base.exists():
            return base
        index = 2
        while True:
            candidate = self.curated_root / f"{slug}-{index}"
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
            if self._is_protected_root(current):
                break
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

    def _is_protected_root(self, path: Path) -> bool:
        resolved = path.resolve(strict=False)
        return any(resolved == root.resolve(strict=False) for root in self.layout.protected_roots())

    def _render_note_template(self, metadata: dict[str, Any]) -> str:
        template_path = self.template_root / "paper-note-template.md"
        template = read_text(template_path) if template_path.exists() else DEFAULT_NOTE_TEMPLATE
        tags = metadata.get("tags") or ["paper"]
        tag_lines = "\n".join(f"  - {tag}" for tag in tags)
        return Template(template).safe_substitute(title=metadata.get("title") or "", year=metadata.get("year") or "", venue=metadata.get("venue") or "", doi=metadata.get("doi") or "", domain=metadata.get("domain") or "", area=metadata.get("area") or "", topic=metadata.get("topic") or "", status=metadata.get("status") or "draft", tags=tag_lines)

    def _resolve_target_path(self, metadata: dict[str, Any], slug: str, target_path: str | None = None) -> Path:
        if target_path:
            return self._resolve_library_target_path(target_path)
        domain = str(metadata.get("domain") or "").strip()
        area = str(metadata.get("area") or metadata.get("subdomain") or "").strip()
        topic = str(metadata.get("topic") or "").strip()
        if not domain:
            return self.library_root / "unclassified" / slug
        return self.library_root.joinpath(*[part for part in (domain, area, topic, slug) if part])

    def _resolve_library_target_path(self, target_path: str) -> Path:
        candidate = Path(target_path)
        if candidate.is_absolute():
            resolved = candidate.resolve(strict=False)
        elif candidate.parts and candidate.parts[0] == self.library_root.name:
            resolved = (self.data_root / candidate).resolve(strict=False)
        else:
            resolved = (self.library_root / candidate).resolve(strict=False)
        if not self._is_within_root(resolved):
            raise ValueError(f"Target path is outside data root: {target_path}")
        try:
            resolved.relative_to(self.library_root.resolve(strict=False))
        except ValueError as error:
            raise ValueError(f"Target path is outside library root: {target_path}") from error
        return resolved

    def _unique_library_target(self, base: Path) -> Path:
        if not base.exists():
            return base
        index = 2
        while True:
            candidate = base.parent / f"{base.name}-{index}"
            if not candidate.exists():
                return candidate
            index += 1

    def _unique_archive_target(self, slug: str) -> Path:
        base = self.archive_root / slug
        if not base.exists():
            return base
        index = 2
        while True:
            candidate = self.archive_root / f"{slug}-{index}"
            if not candidate.exists():
                return candidate
            index += 1

    def _write_archive_state(self, paper_dir: Path, record: PaperRecord) -> None:
        state = self._safe_json_object(paper_dir / "state.json")
        archived_state = merge_metadata(
            state,
            {
                "status": "rejected",
                "review_status": "rejected",
                "rejected": True,
                "archived_from": record.path,
                "path": str(paper_dir),
                "updated_at": utc_now(),
            },
        )
        write_json(paper_dir / "state.json", archived_state)

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

    def _paper_events(self, paper_dir: Path) -> list[dict[str, Any]]:
        events_path = paper_dir / "events.jsonl"
        if not events_path.exists():
            return []
        events: list[dict[str, Any]] = []
        for line in events_path.read_text(encoding="utf-8-sig").splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except ValueError:
                continue
            if isinstance(payload, dict):
                events.append(payload)
        return events

    def _append_event(
        self,
        paper_dir: Path,
        event: str,
        *,
        actor: str,
        result: str,
        message: str,
        technical_detail: str = "",
        next_action: str = "",
    ) -> None:
        events_path = paper_dir / "events.jsonl"
        payload = {
            "timestamp": utc_now(),
            "event": event,
            "actor": actor,
            "result": result,
            "message": message,
            "technical_detail": technical_detail,
            "next_action": next_action,
        }
        events_path.parent.mkdir(parents=True, exist_ok=True)
        with events_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def _parser_run_record(self, row: dict[str, Any], paper_id: str) -> ParserRunRecord:
        return ParserRunRecord(run_id=str(row.get("run_id") or ""), paper_id=paper_id, status=str(row.get("status") or ""), parser=str(row.get("parser") or ""), source_pdf=str(row.get("source_pdf") or ""), refined_path=str(row.get("refined_path") or ""), image_dir=str(row.get("image_dir") or ""), text_path=str(row.get("text_path") or ""), sections_path=str(row.get("sections_path") or ""), error=str(row.get("error") or ""), started_at=str(row.get("started_at") or ""), finished_at=str(row.get("finished_at") or ""))

    def _event_record(self, row: dict[str, Any]) -> PaperEventRecord:
        return PaperEventRecord(
            timestamp=str(row.get("timestamp") or ""),
            event=str(row.get("event") or ""),
            actor=str(row.get("actor") or ""),
            result=str(row.get("result") or ""),
            message=str(row.get("message") or ""),
            technical_detail=str(row.get("technical_detail") or ""),
            next_action=str(row.get("next_action") or ""),
        )

    def _normalize_paper_payload(self, paper_dir: Path, payload: dict[str, Any]) -> dict[str, Any]:
        paper_path = paper_dir / "paper.pdf"
        note_path = paper_dir / "note.md"
        parsed_text = paper_dir / "parsed" / "text.md"
        parsed_sections = paper_dir / "parsed" / "sections.json"
        refined_path = paper_dir / "refined.md"
        stage = self._paper_stage(paper_dir, payload)
        asset_status = self._asset_status(payload, paper_path)
        parser_status = self._parser_status(payload, paper_dir)
        review_status = self._review_status(payload)
        note_status = self._note_status(payload, note_path)
        refined_review_status = self._refined_review_status(payload, parser_status)
        note_review_status = self._note_review_status(payload, note_status, note_path)
        classification_status = self._classification_status(payload)
        compat_status = self._compat_status(stage, asset_status, parser_status, review_status)
        workflow_status = self._workflow_status(
            asset_status=asset_status,
            parser_status=parser_status,
            note_status=note_status,
            refined_review_status=refined_review_status,
            note_review_status=note_review_status,
            classification_status=classification_status,
            note_path=note_path,
            error=str(payload.get("error") or ""),
        )
        return merge_metadata(
            payload,
            {
                "stage": stage,
                "asset_status": asset_status,
                "parser_status": parser_status,
                "review_status": review_status,
                "note_status": note_status,
                "refined_review_status": refined_review_status,
                "note_review_status": note_review_status,
                "classification_status": classification_status,
                "status": compat_status,
                "workflow_status": workflow_status,
                "path": str(paper_dir),
                "paper_path": str(paper_path) if paper_path.exists() else "",
                "note_path": str(note_path) if note_path.exists() else "",
                "parsed_text_path": str(parsed_text) if parsed_text.exists() else str(payload.get("parsed_text_path") or ""),
                "parsed_sections_path": str(parsed_sections) if parsed_sections.exists() else str(payload.get("parsed_sections_path") or ""),
                "refined_path": str(refined_path) if refined_path.exists() else str(payload.get("refined_path") or ""),
            },
        )

    def _apply_explicit_clears(self, payload: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
        merged = dict(payload)
        for key, value in updates.items():
            if value in (None, "", [], {}):
                merged[key] = value
        return merged

    def _asset_status(self, metadata: dict[str, Any], paper_path: Path) -> str:
        stored = str(metadata.get("asset_status") or "").strip()
        if stored in {"missing_pdf", "pdf_ready"}:
            return stored
        legacy = str(metadata.get("workflow_status") or metadata.get("status") or "").strip()
        if legacy == "needs-pdf":
            return "missing_pdf"
        if legacy in {"applied", "processed", "needs-review", "parse-failed", "parse-pending"}:
            return "pdf_ready"
        return "pdf_ready" if paper_path.exists() else "missing_pdf"

    def _parser_status(self, metadata: dict[str, Any], paper_dir: Path | None = None) -> str:
        stored = str(metadata.get("parser_status") or "").strip()
        if stored in {"not_started", "running", "parsed", "failed"}:
            return stored
        legacy = str(metadata.get("workflow_status") or metadata.get("status") or "").strip()
        if legacy == "parse-failed":
            return "failed"
        if legacy in {"applied", "needs-review", "processed", "reviewed"}:
            return "parsed"
        if legacy in {"parse-pending", "needs-pdf"}:
            return "not_started"
        refine_status = str(metadata.get("refine_status") or "").strip()
        if refine_status in {"processed", "done", "generated", "human_edited"}:
            return "parsed"
        if paper_dir is not None and (paper_dir / "refined.md").exists():
            return "parsed"
        return self._normalized_parser_status(stored)

    def _review_status(self, metadata: dict[str, Any]) -> str:
        stored = str(metadata.get("review_status") or "").strip()
        if stored in {"pending", "accepted"}:
            return stored
        legacy = str(metadata.get("workflow_status") or metadata.get("status") or "").strip()
        classification_status = self._classification_status(metadata)
        return "accepted" if legacy in {"applied", "processed", "reviewed"} or classification_status in {"applied", "accepted"} else "pending"

    def _classification_status(self, metadata: dict[str, Any]) -> str:
        stored = str(metadata.get("classification_status") or "").strip()
        if stored == "applied":
            return "accepted"
        return stored or "pending"

    def _refined_review_status(self, metadata: dict[str, Any], parser_status: str) -> str:
        stored = str(metadata.get("refined_review_status") or "").strip()
        if stored in {"pending", "approved", "rejected"}:
            return stored
        return "pending" if parser_status == "parsed" else "missing"

    def _note_review_status(self, metadata: dict[str, Any], note_status: str, note_path: Path) -> str:
        stored = str(metadata.get("note_review_status") or "").strip()
        if stored in {"missing", "pending", "approved", "rejected"}:
            return stored
        if note_status in {"ready", "approved"}:
            return "approved"
        if note_status == "rejected":
            return "rejected"
        if note_status in {"template", "review_pending"} or note_path.exists():
            return "pending"
        return "missing"

    def _note_status(self, metadata: dict[str, Any], note_path: Path) -> str:
        stored = str(metadata.get("note_status") or "").strip()
        if stored in {"missing", "template", "ready", "generated", "review_pending", "approved", "rejected"}:
            return stored
        return "template" if note_path.exists() else "missing"

    def _workflow_status(
        self,
        *,
        asset_status: str,
        parser_status: str,
        note_status: str,
        refined_review_status: str,
        note_review_status: str,
        classification_status: str,
        note_path: Path,
        error: str,
    ) -> str:
        if error or parser_status == "failed":
            return "failed"
        if asset_status == "missing_pdf":
            return "missing_pdf"
        if asset_status == "downloading":
            return "downloading"
        if parser_status == "running":
            return "running"
        if parser_status == "not_started":
            return "not_started"
        if refined_review_status == "rejected":
            return "refine_rejected"
        if parser_status == "parsed" and refined_review_status != "approved":
            return "refine_review_pending"
        if note_status in {"missing"} or not note_path.exists():
            return "note_missing"
        if note_review_status == "rejected":
            return "note_rejected"
        if note_review_status != "approved":
            return "note_review_pending"
        if classification_status not in {"classified", "accepted"}:
            return "unclassified"
        return "ready"

    def _compat_status(self, stage: str, asset_status: str, parser_status: str, review_status: str) -> str:
        del stage
        if asset_status == "missing_pdf":
            return "needs-pdf"
        if parser_status == "failed":
            return "parse-failed"
        if review_status == "accepted":
            return "processed"
        if parser_status == "parsed":
            return "needs-review"
        return "parse-pending"

    def _status_from_parser(self, parser_status: str) -> str:
        return self._compat_status("acquire", "pdf_ready", self._normalized_parser_status(parser_status), "pending")

    def _normalized_parser_status(self, parser_status: str) -> str:
        if parser_status in {"processed", "done", "generated", "human_edited"}:
            return "parsed"
        if parser_status == "failed":
            return "failed"
        if parser_status in {"pending", "skipped", "parse-pending", "needs-pdf", ""}:
            return "not_started"
        if parser_status in {"not_started", "running", "parsed", "failed"}:
            return parser_status
        return "not_started"

    def _review_decision(self, decision: str) -> str:
        normalized = decision.strip().lower()
        if normalized not in {"approved", "rejected"}:
            raise ValueError("Review decision must be approved or rejected")
        return normalized

    def _legacy_status_updates(self, status: str) -> dict[str, Any]:
        if status == "processed":
            return {"review_status": "accepted"}
        if status == "needs-review":
            return {"review_status": "pending", "parser_status": "parsed"}
        if status == "needs-pdf":
            return {"asset_status": "missing_pdf", "parser_status": "not_started", "review_status": "pending"}
        if status == "parse-failed":
            return {"asset_status": "pdf_ready", "parser_status": "failed", "review_status": "pending"}
        return {"review_status": "pending"}

    def _metadata_updates(self, request: UpdateClassificationInput) -> dict[str, Any]:
        domain = request.domain.strip()
        area = request.area.strip() if domain else ""
        topic = request.topic.strip() if area else ""
        updates: dict[str, Any] = {
            "domain": domain,
            "area": area,
            "topic": topic,
            "classification_status": "classified" if domain else "pending",
        }
        optional_values: dict[str, Any] = {
            "title": request.title,
            "venue": request.venue,
            "year": request.year,
            "tags": request.tags,
            "status": request.status,
            "paper_path": request.paper_path,
            "note_path": request.note_path,
            "refined_path": request.refined_path,
        }
        for key, value in optional_values.items():
            if value is not None:
                updates[key] = value
        return updates

    def _metadata_payload(self, updates: dict[str, Any]) -> dict[str, Any]:
        allowed = {
            "title",
            "authors",
            "year",
            "venue",
            "doi",
            "arxiv_id",
            "url",
            "paper_url",
            "pdf_url",
            "abstract",
            "summary",
            "domain",
            "area",
            "topic",
            "tags",
            "paper_path",
            "note_path",
            "refined_path",
            "classification_status",
        }
        payload: dict[str, Any] = {}
        for key, value in updates.items():
            if key not in allowed:
                continue
            if key in {"authors", "tags"}:
                payload[key] = self._string_list(value)
                continue
            if key == "year":
                payload[key] = self._int_or_none(value)
                continue
            payload[key] = value.strip() if isinstance(value, str) else value
        return payload

    def _search_settings_payload(self, updates: dict[str, Any]) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if "command_template" in updates and updates["command_template"] is not None:
            payload["command_template"] = str(updates["command_template"])
        if "prompt_template" in updates and updates["prompt_template"] is not None:
            payload["prompt_template"] = str(updates["prompt_template"])
        if "default_source" in updates and updates["default_source"] is not None:
            payload["default_source"] = str(updates["default_source"])
        if "max_results" in updates and updates["max_results"] is not None:
            payload["max_results"] = int(updates["max_results"])
        return payload

    def _infer_metadata_fields(self, metadata: dict[str, Any]) -> dict[str, Any]:
        title = str(metadata.get("title") or "").strip()
        doi = str(metadata.get("doi") or "").strip()
        arxiv_id = str(metadata.get("arxiv_id") or "").strip()
        url = str(metadata.get("url") or "").strip()
        updates: dict[str, Any] = {
            "title": title,
            "doi": doi,
            "arxiv_id": arxiv_id or self._arxiv_id_from_text(url),
            "url": url,
            "authors": self._string_list(metadata.get("authors")),
            "abstract": str(metadata.get("abstract") or "").strip(),
            "summary": str(metadata.get("summary") or "").strip(),
            "venue": str(metadata.get("venue") or "").strip(),
            "year": self._int_or_none(metadata.get("year")),
        }
        if not updates["url"] and updates["arxiv_id"]:
            updates["url"] = f"https://arxiv.org/abs/{updates['arxiv_id']}"
        if not updates["summary"] and updates["abstract"]:
            updates["summary"] = str(updates["abstract"])[:500]
        if not updates["venue"] and updates["arxiv_id"]:
            updates["venue"] = "arXiv"
        if not updates["abstract"] and title:
            updates["abstract"] = ""
        return {key: value for key, value in updates.items() if value not in (None, [], {})}

    def _arxiv_id_from_text(self, value: str) -> str:
        match = re.search(r"arxiv\.org/(?:abs|pdf)/([^/?#]+)", value, flags=re.IGNORECASE)
        return match.group(1).replace(".pdf", "") if match else ""

    def _settings_root(self) -> Path:
        path = self.data_root / "settings"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _render_prompt_template(self, template: str, variables: dict[str, str]) -> str:
        try:
            return template.format(**variables)
        except (KeyError, ValueError):
            rendered = template
            for key, value in variables.items():
                rendered = rendered.replace(f"{{{key}}}", value)
            return rendered

    def _seed_candidates_from_keywords(self, batch_id: str, keywords: str, variables: dict[str, str], max_results: int) -> list[dict[str, Any]]:
        title = keywords.strip()
        return [
            {
                "id": "P001",
                "candidate_id": "P001",
                "title": title,
                "authors": [],
                "year": self._int_or_none(variables.get("year_end")) or self._int_or_none(variables.get("year_start")),
                "venue": variables.get("venue") or "",
                "source_type": variables.get("source") or "manual",
                "collection_role": "seed",
                "paper_type": "metadata-only",
                "quality": 50,
                "relevance": 50,
                "relevance_reason_zh": "由新建检索关键词生成的待补全候选。后续可由 Codex CLI job 覆盖 candidates.json。",
                "landing_status": "metadata-only",
                "result_path": f"Discover/search_batches/{batch_id}/results/P001",
                "abstract": "",
                "url": "",
                "doi": "",
                "arxiv_id": "",
                "pdf_url": "",
                "max_results": max_results,
            }
        ]

    def _unique_search_batch_id(self, slug: str) -> str:
        date_prefix = datetime.now(timezone.utc).strftime("%Y%m%d")
        base = f"{date_prefix}-{slug}"
        candidate = base
        index = 2
        while (self.search_batches_root / candidate).exists():
            candidate = f"{base}-{index}"
            index += 1
        return candidate

    def _batch_record_from_dir(self, batch_dir: Path) -> BatchRecord:
        candidates = self._candidate_rows(batch_dir / "candidates.json")
        return BatchRecord(
            batch_id=batch_dir.name,
            title=batch_dir.name.replace("-", " "),
            candidate_total=len(candidates),
            keep_total=len([row for row in candidates if self._candidate_decision(row) == "keep"]),
            reject_total=len([row for row in candidates if self._candidate_decision(row) == "reject"]),
            review_status="reviewed" if (batch_dir / "review.md").exists() else "pending",
            path=str(batch_dir),
            updated_at=self._mtime(batch_dir),
        )

    def _read_artifact_body(self, path: Path, *, max_chars: int) -> str:
        if not path.exists():
            return ""
        try:
            content = read_text(path)
        except OSError:
            return ""
        _, body = split_front_matter(content)
        return body.strip()[:max_chars]

    def _normalize_research_log(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(payload.get("id") or slugify(str(payload.get("title") or "research-log"), fallback="research-log")),
            "timestamp": str(payload.get("timestamp") or utc_now()),
            "updated_at": str(payload.get("updated_at") or utc_now()),
            "title": str(payload.get("title") or "阅读记录"),
            "bullets": self._string_list(payload.get("bullets")),
            "next_steps": self._string_list(payload.get("next_steps") or payload.get("nextSteps")),
            "tasks": self._task_list(payload.get("tasks")),
        }

    def _task_list(self, value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []
        tasks: list[dict[str, Any]] = []
        for index, item in enumerate(value):
            if not isinstance(item, dict):
                continue
            label = str(item.get("label") or "").strip()
            if not label:
                continue
            tasks.append(
                {
                    "id": str(item.get("id") or slugify(label, fallback=f"task-{index}")),
                    "label": label,
                    "checked": bool(item.get("checked") or False),
                }
            )
        return tasks

    def _read_jsonl(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except ValueError:
                continue
            if isinstance(payload, dict):
                rows.append(payload)
        return rows

    def _append_jsonl(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def _write_jsonl(self, path: Path, rows: list[dict[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        content = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
        path.write_text(content, encoding="utf-8", newline="\n")

    def _string_list(self, value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return []

    def _active_paper_roots(self) -> tuple[Path, ...]:
        if self.data_layout == "native":
            return (self.library_root,)
        return (self.curated_root, self.library_root, *self.legacy_library_roots)

    def _capabilities_for(
        self,
        *,
        stage: str,
        asset_status: str,
        parser_status: str,
        note_status: str,
        refined_review_status: str,
        note_review_status: str,
    ) -> PaperCapabilities:
        can_parse = asset_status == "pdf_ready" and parser_status != "running" and stage in {"acquire", "library"}
        can_accept = stage == "acquire" and parser_status == "parsed"
        can_review_refined = parser_status == "parsed"
        can_generate_note = parser_status == "parsed" and refined_review_status == "approved" and note_status == "missing"
        can_review_note = note_status != "missing" and note_review_status != "approved" and refined_review_status == "approved"
        return PaperCapabilities(
            parse=can_parse,
            accept=can_accept,
            generate_note=can_generate_note,
            review_refined=can_review_refined,
            review_note=can_review_note,
            delete=True,
        )

    def _require_paper_dir(self, paper_id: str) -> Path:
        paper_dir = self.get_paper_dir(paper_id)
        if paper_dir is None:
            raise FileNotFoundError(paper_id)
        return paper_dir

    def _relative_id(self, path: Path) -> str:
        return str(path.relative_to(self.data_root)).replace("\\", "__").replace("/", "__")

    def _paper_dir_from_id(self, paper_id: str) -> Path | None:
        relative = Path(*[part for part in paper_id.split("__") if part])
        if not relative.parts:
            return None
        candidate = (self.data_root / relative).resolve(strict=False)
        if not candidate.exists() or not candidate.is_dir():
            return None
        try:
            candidate.relative_to(self.data_root.resolve(strict=False))
        except ValueError:
            return None
        return candidate

    def _paper_stage(self, path: Path, metadata: dict[str, Any] | None = None) -> str:
        if path == self.curated_root or self.curated_root in path.parents:
            return "acquire"
        if path == self.library_root or self.library_root in path.parents:
            return "library"
        if any(path == root or root in path.parents for root in self.legacy_library_roots):
            return "library"
        try:
            relative = path.resolve(strict=False).relative_to(self.data_root.resolve(strict=False))
        except ValueError:
            relative = None
        if relative and relative.parts and relative.parts[0] in {"Library", "Papers"}:
            return "library"
        if metadata:
            status = str(metadata.get("status") or metadata.get("ingest_status") or "").strip()
            if status == "curated":
                return "acquire"
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
