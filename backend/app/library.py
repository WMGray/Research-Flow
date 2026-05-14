from __future__ import annotations

import json
import re
import shutil
import unicodedata
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from string import Template
from typing import Any

import yaml


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(read_text(path))
    return data if isinstance(data, dict) else {}


def write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
        newline="\n",
    )


def read_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(read_text(path))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")


def slugify(value: str, fallback: str = "paper") -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_text).strip("-").lower()
    return slug or fallback


def unique_list(values: list[Any]) -> list[Any]:
    seen: set[Any] = set()
    result: list[Any] = []
    for item in values:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def split_front_matter(text: str) -> tuple[dict[str, Any], str]:
    normalized = text.replace("\r\n", "\n")
    if not normalized.startswith("---\n"):
        return {}, text
    try:
        _, remainder = normalized.split("---\n", 1)
        header, body = remainder.split("\n---\n", 1)
    except ValueError:
        return {}, text
    data = yaml.safe_load(header)
    return (data if isinstance(data, dict) else {}), body


def load_markdown_front_matter(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    front_matter, _ = split_front_matter(read_text(path))
    return front_matter


def merge_metadata(*sources: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for source in sources:
        for key, value in source.items():
            if value in (None, "", [], {}):
                continue
            if key == "tags":
                current = list(result.get("tags", []))
                if isinstance(value, list):
                    current.extend(value)
                elif isinstance(value, str):
                    current.append(value)
                else:
                    current.append(str(value))
                result["tags"] = unique_list(current)
                continue
            result[key] = value
    if "tags" not in result:
        result["tags"] = ["paper"]
    return result


@dataclass(slots=True)
class BatchRecord:
    batch_id: str
    title: str
    candidate_total: int
    keep_total: int
    reject_total: int
    review_status: str
    path: str
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class PaperRecord:
    paper_id: str
    title: str
    slug: str
    stage: str
    status: str
    domain: str
    area: str
    topic: str
    year: int | None
    venue: str
    doi: str
    tags: list[str]
    path: str
    paper_path: str
    note_path: str
    refined_path: str
    images_path: str
    metadata_path: str
    error: str
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class PaperLibrary:
    def __init__(self, data_root: Path) -> None:
        self.data_root = data_root
        self.discover_root = data_root / "Discover"
        self.acquire_root = data_root / "Acquire"
        self.library_root = data_root / "Library"
        self.template_root = data_root / "templates"
        self.ensure_layout()

    def ensure_layout(self) -> None:
        for path in [
            self.discover_root / "search_batches",
            self.acquire_root / "curated",
            self.library_root / "unclassified",
            self.template_root,
        ]:
            path.mkdir(parents=True, exist_ok=True)

    def _relative_id(self, path: Path) -> str:
        return str(path.relative_to(self.data_root)).replace("\\", "__").replace("/", "__")

    def _paper_stage(self, path: Path) -> str:
        if self.acquire_root in path.parents:
            return "acquire"
        if self.library_root in path.parents:
            return "library"
        return "unknown"

    def _paper_record_from_dir(self, paper_dir: Path) -> PaperRecord:
        metadata_path = paper_dir / "metadata.yaml"
        note_path = paper_dir / "note.md"
        refined_path = paper_dir / "refined.md"
        paper_path = paper_dir / "paper.pdf"
        images_path = paper_dir / "images"

        metadata = read_yaml(metadata_path)
        note_metadata = load_markdown_front_matter(note_path)
        merged = merge_metadata(note_metadata, metadata)
        title = str(merged.get("title") or paper_dir.name)
        slug = paper_dir.name
        status = str(merged.get("status") or ("processed" if paper_path.exists() else "needs-pdf"))
        domain = str(merged.get("domain") or "")
        area = str(merged.get("area") or merged.get("subdomain") or "")
        topic = str(merged.get("topic") or "")
        year_value = merged.get("year")
        try:
            year = int(year_value) if year_value not in (None, "") else None
        except (TypeError, ValueError):
            year = None
        updated_at = str(merged.get("updated_at") or utc_now())
        error = str(merged.get("error") or "")
        tags = [str(tag) for tag in merged.get("tags", []) if tag]
        if not tags:
            tags = ["paper"]

        return PaperRecord(
            paper_id=self._relative_id(paper_dir),
            title=title,
            slug=slug,
            stage=self._paper_stage(paper_dir),
            status=status,
            domain=domain,
            area=area,
            topic=topic,
            year=year,
            venue=str(merged.get("venue") or ""),
            doi=str(merged.get("doi") or ""),
            tags=tags,
            path=str(paper_dir),
            paper_path=str(paper_path) if paper_path.exists() else "",
            note_path=str(note_path) if note_path.exists() else "",
            refined_path=str(refined_path) if refined_path.exists() else "",
            images_path=str(images_path) if images_path.exists() else "",
            metadata_path=str(metadata_path) if metadata_path.exists() else "",
            error=error,
            updated_at=updated_at,
        )

    def list_papers(self) -> list[PaperRecord]:
        paper_dirs = []
        for root in [self.acquire_root, self.library_root]:
            if root.exists():
                paper_dirs.extend(
                    path.parent for path in root.rglob("metadata.yaml") if path.parent.is_dir()
                )
        records = [self._paper_record_from_dir(paper_dir) for paper_dir in paper_dirs]
        return sorted(records, key=lambda item: (item.updated_at, item.title), reverse=True)

    def list_batches(self) -> list[BatchRecord]:
        batches_root = self.discover_root / "search_batches"
        records: list[BatchRecord] = []
        if not batches_root.exists():
            return records
        for batch_dir in sorted([path for path in batches_root.iterdir() if path.is_dir()]):
            candidates_path = batch_dir / "candidates.json"
            review_path = batch_dir / "review.md"
            title = batch_dir.name.replace("-", " ")
            candidates = read_json(candidates_path) or []
            candidate_total = len(candidates) if isinstance(candidates, list) else 0
            review_text = read_text(review_path) if review_path.exists() else ""
            keep_total = len(re.findall(r"\|\s*keep\s*\|", review_text, flags=re.IGNORECASE))
            reject_total = len(re.findall(r"\|\s*reject\s*\|", review_text, flags=re.IGNORECASE))
            review_status = "reviewed" if review_text else "pending"
            records.append(
                BatchRecord(
                    batch_id=batch_dir.name,
                    title=title,
                    candidate_total=candidate_total,
                    keep_total=keep_total,
                    reject_total=reject_total,
                    review_status=review_status,
                    path=str(batch_dir),
                    updated_at=datetime.fromtimestamp(batch_dir.stat().st_mtime, tz=timezone.utc).isoformat(),
                )
            )
        return sorted(records, key=lambda item: item.updated_at, reverse=True)

    def get_paper(self, paper_id: str) -> PaperRecord | None:
        for paper in self.list_papers():
            if paper.paper_id == paper_id or paper.slug == paper_id:
                return paper
        return None

    def _status_counts(self, papers: list[PaperRecord]) -> dict[str, int]:
        counts = Counter(paper.status for paper in papers)
        return dict(sorted(counts.items()))

    def dashboard_home(self) -> dict[str, Any]:
        papers = self.list_papers()
        batches = self.list_batches()
        status_counts = self._status_counts(papers)
        recent_papers = [paper.to_dict() for paper in papers[:6]]
        queue_items = [paper.to_dict() for paper in papers if paper.status in {"needs-pdf", "needs-review", "failed"}][:8]
        totals = {
            "papers": len(papers),
            "batches": len(batches),
            "processed": status_counts.get("processed", 0),
            "curated": len([paper for paper in papers if paper.stage == "acquire"]),
            "library": len([paper for paper in papers if paper.stage == "library"]),
            "needs_pdf": status_counts.get("needs-pdf", 0),
            "needs_review": status_counts.get("needs-review", 0),
            "failed": status_counts.get("failed", 0),
        }
        return {
            "totals": totals,
            "status_counts": status_counts,
            "recent_papers": recent_papers,
            "queue_items": queue_items,
            "recent_batches": [batch.to_dict() for batch in batches[:5]],
            "paths": {
                "data_root": str(self.data_root),
                "discover_root": str(self.discover_root),
                "acquire_root": str(self.acquire_root),
                "library_root": str(self.library_root),
            },
        }

    def dashboard_discover(self) -> dict[str, Any]:
        batches = self.list_batches()
        return {
            "summary": {
                "batch_total": len(batches),
                "reviewed_total": len([batch for batch in batches if batch.review_status == "reviewed"]),
            },
            "batches": [batch.to_dict() for batch in batches],
        }

    def dashboard_acquire(self) -> dict[str, Any]:
        papers = self.list_papers()
        queue = [paper for paper in papers if paper.stage == "acquire"]
        return {
            "summary": {
                "curated_total": len(queue),
                "needs_pdf_total": len([paper for paper in queue if paper.status == "needs-pdf"]),
                "needs_review_total": len([paper for paper in queue if paper.status == "needs-review"]),
                "failed_total": len([paper for paper in queue if paper.status == "failed"]),
            },
            "queue": [paper.to_dict() for paper in queue],
        }

    def dashboard_library(self) -> dict[str, Any]:
        papers = self.list_papers()
        library_papers = [paper for paper in papers if paper.stage == "library"]
        unclassified = [paper for paper in library_papers if not paper.domain or paper.domain == "unclassified"]
        return {
            "summary": {
                "library_total": len(library_papers),
                "unclassified_total": len(unclassified),
                "processed_total": len([paper for paper in library_papers if paper.status == "processed"]),
            },
            "papers": [paper.to_dict() for paper in library_papers],
        }

    def _template_note(self, metadata: dict[str, Any]) -> str:
        template_path = self.template_root / "paper-note-template.md"
        if template_path.exists():
            template = read_text(template_path)
        else:
            template = (
                "---\n"
                "title: $title\n"
                "year: $year\n"
                "venue: $venue\n"
                "doi: $doi\n"
                "domain: $domain\n"
                "area: $area\n"
                "topic: $topic\n"
                "status: $status\n"
                "tags:\n"
                "$tags\n"
                "---\n\n"
                "# 文章摘要\n\n"
                "# 缩写与术语解释\n\n"
                "# 深度背景与动机分析\n\n"
                "# 本文方法\n\n"
                "# 实验结果\n\n"
                "# 结论局限\n\n"
                "# 与我研究的关联\n"
            )
        tags = metadata.get("tags") or ["paper"]
        tag_lines = "\n".join(f"  - {tag}" for tag in tags)
        return Template(template).safe_substitute(
            title=metadata.get("title") or "",
            year=metadata.get("year") or "",
            venue=metadata.get("venue") or "",
            doi=metadata.get("doi") or "",
            domain=metadata.get("domain") or "",
            area=metadata.get("area") or "",
            topic=metadata.get("topic") or "",
            status=metadata.get("status") or "draft",
            tags=tag_lines,
        )

    def _resolve_target_path(self, metadata: dict[str, Any], slug: str, target_path: str | None = None) -> Path:
        if target_path:
            return self.library_root / target_path
        domain = str(metadata.get("domain") or "").strip()
        area = str(metadata.get("area") or metadata.get("subdomain") or "").strip()
        topic = str(metadata.get("topic") or "").strip()
        if not domain:
            return self.library_root / "unclassified" / slug
        parts = [domain]
        if area:
            parts.append(area)
        if topic:
            parts.append(topic)
        return self.library_root.joinpath(*parts, slug)

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

    def _copy_source_assets(self, source: Path, target: Path, *, move: bool = False) -> None:
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
                continue
            self._transfer_file(item, destination, move=move)

        if move and source.exists():
            try:
                source.rmdir()
            except OSError:
                pass

    def ingest(
        self,
        source: Path,
        *,
        domain: str | None = None,
        area: str | None = None,
        topic: str | None = None,
        target_path: str | None = None,
        move: bool = False,
    ) -> PaperRecord:
        source = source.resolve()
        if not source.exists():
            raise FileNotFoundError(source)

        source_metadata: dict[str, Any] = {}
        if source.is_dir():
            source_metadata = merge_metadata(load_markdown_front_matter(source / "note.md"), read_yaml(source / "metadata.yaml"))
        elif source.suffix.lower() in {".md", ".markdown"}:
            source_metadata = load_markdown_front_matter(source)

        title = str(source_metadata.get("title") or source.stem or source.name)
        slug = slugify(title, fallback=slugify(source.name, fallback="paper"))
        metadata = merge_metadata(
            source_metadata,
            {
                "title": title,
                "domain": domain or source_metadata.get("domain"),
                "area": area or source_metadata.get("area") or source_metadata.get("subdomain"),
                "topic": topic or source_metadata.get("topic"),
            },
        )
        target = self._resolve_target_path(metadata, slug, target_path)
        if target.exists():
            write_yaml(target / "metadata.yaml", merge_metadata(read_yaml(target / "metadata.yaml"), {"status": "needs-review", "error": "Target already exists"}))
            return self._paper_record_from_dir(target)

        target.mkdir(parents=True, exist_ok=True)
        self._copy_source_assets(source, target, move=move)

        if not (target / "note.md").exists():
            write_text(target / "note.md", self._template_note(metadata))

        metadata_to_write = merge_metadata(
            metadata,
            {
                "status": "processed" if (target / "paper.pdf").exists() else "needs-pdf",
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
        return self._paper_record_from_dir(target)

    def migrate(
        self,
        source: Path,
        *,
        domain: str | None = None,
        area: str | None = None,
        topic: str | None = None,
        target_path: str | None = None,
    ) -> PaperRecord:
        return self.ingest(source, domain=domain, area=area, topic=topic, target_path=target_path, move=True)

    def generate_note_template(self, metadata: dict[str, Any]) -> str:
        return self._template_note(metadata)
