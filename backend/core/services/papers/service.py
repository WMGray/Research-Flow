from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from backend.core.config import get_settings
from backend.core.services.papers.models import (
    BatchRecord,
    CandidateRecord,
    GenerateNoteInput,
    IngestPaperInput,
    ParsePdfInput,
    ParserRunRecord,
    PaperRecord,
)
from backend.core.services.papers.parser import parse_pdf, parser_health
from backend.core.services.papers.repository import PaperRepository
from backend.core.services.papers.utils import utc_now


class PaperService:
    def __init__(
        self,
        data_root: Path | None = None,
        repository: PaperRepository | None = None,
    ) -> None:
        resolved_root = data_root or get_settings().data_root
        self.repository = repository or PaperRepository(resolved_root)

    def list_papers(self) -> list[PaperRecord]:
        return self.repository.list_papers()

    def list_batches(self) -> list[BatchRecord]:
        return self.repository.list_batches()

    def list_candidates(self, batch_id: str | None = None) -> list[CandidateRecord]:
        return self.repository.list_candidates(batch_id)

    def set_candidate_decision(
        self,
        batch_id: str,
        candidate_id: str,
        decision: str,
    ) -> CandidateRecord:
        return self.repository.set_candidate_decision(batch_id, candidate_id, decision)

    def restore_batch_candidates(self, batch_id: str) -> list[dict[str, Any]]:
        return self.repository.restore_batch_candidates(batch_id)

    def cleanup_batches(self) -> list[str]:
        return self.repository.cleanup_batches()

    def cleanup_batch(self, batch_id: str) -> bool:
        return self.repository.cleanup_batch(batch_id)

    def get_paper(self, paper_id: str) -> PaperRecord | None:
        return self.repository.get_paper(paper_id)

    def ingest(
        self,
        source: Path | IngestPaperInput,
        *,
        domain: str | None = None,
        area: str | None = None,
        topic: str | None = None,
        target_path: str | None = None,
        move: bool = False,
    ) -> PaperRecord:
        request = self._to_ingest_input(
            source,
            domain=domain,
            area=area,
            topic=topic,
            target_path=target_path,
            move=move,
        )
        return self.repository.ingest(request)

    def migrate(
        self,
        source: Path | IngestPaperInput,
        *,
        domain: str | None = None,
        area: str | None = None,
        topic: str | None = None,
        target_path: str | None = None,
    ) -> PaperRecord:
        request = self._to_ingest_input(
            source,
            domain=domain,
            area=area,
            topic=topic,
            target_path=target_path,
            move=True,
        )
        return self.repository.migrate(request)

    def generate_note_template(
        self,
        metadata: dict[str, Any] | GenerateNoteInput,
    ) -> str:
        request = self._to_generate_note_input(metadata)
        return self.repository.generate_note_template(request)

    def generate_note_for_paper(self, paper_id: str, *, overwrite: bool = False) -> PaperRecord:
        return self.repository.generate_note_for_paper(paper_id, overwrite=overwrite)

    def parse_pdf(
        self,
        request: ParsePdfInput | str,
        *,
        force: bool = False,
        parser: str = "auto",
    ) -> PaperRecord:
        payload = request if isinstance(request, ParsePdfInput) else ParsePdfInput(paper_id=request, force=force, parser=parser)
        paper_dir = self.repository.get_paper_dir(payload.paper_id)
        if paper_dir is None:
            raise FileNotFoundError(payload.paper_id)
        started_at = utc_now()
        result = parse_pdf(paper_dir, force=payload.force, parser=payload.parser)
        return self.repository.record_parser_result(payload.paper_id, result, started_at=started_at)

    def list_parser_runs(self, paper_id: str) -> list[ParserRunRecord]:
        return self.repository.list_parser_runs(paper_id)

    def mark_review(self, paper_id: str) -> PaperRecord:
        return self.repository.mark_status(paper_id, "needs-review")

    def mark_processed(self, paper_id: str) -> PaperRecord:
        return self.repository.mark_status(paper_id, "processed")

    def reject_paper(self, paper_id: str) -> PaperRecord:
        return self.repository.reject_paper(paper_id)

    def config_health(self) -> dict[str, Any]:
        health = self.repository.config_health()
        health["parser"] = parser_health()
        return health

    def dashboard_home(self) -> dict[str, Any]:
        papers = self.list_papers()
        batches = self.list_batches()
        status_counts = self._status_counts(papers)
        return {
            "totals": {
                "papers": len(papers),
                "batches": len(batches),
                "processed": status_counts.get("processed", 0),
                "curated": len([paper for paper in papers if paper.stage == "acquire"]),
                "library": len([paper for paper in papers if paper.stage == "library"]),
                "needs_pdf": status_counts.get("needs-pdf", 0),
                "needs_review": status_counts.get("needs-review", 0),
                "parse_failed": status_counts.get("parse-failed", 0),
                "rejected": status_counts.get("rejected", 0),
                "failed": status_counts.get("failed", 0),
            },
            "status_counts": status_counts,
            "recent_papers": [paper.to_dict() for paper in papers[:6]],
            "queue_items": [
                paper.to_dict()
                for paper in papers
                if paper.status in {"needs-pdf", "needs-review", "parse-failed", "failed"}
            ][:8],
            "recent_batches": [batch.to_dict() for batch in batches[:5]],
            "paths": {
                "data_root": str(self.repository.data_root),
                "discover_root": str(self.repository.discover_root),
                "acquire_root": str(self.repository.acquire_root),
                "library_root": str(self.repository.library_root),
            },
        }

    def dashboard_papers_overview(self) -> dict[str, Any]:
        papers = self.list_papers()
        return {
            "papers": [paper.to_dict() for paper in papers],
            "totals": self.dashboard_home()["totals"],
        }

    def dashboard_discover(self) -> dict[str, Any]:
        batches = self.list_batches()
        candidates = self.list_candidates()
        return {
            "summary": {
                "batch_total": len(batches),
                "reviewed_total": len(
                    [batch for batch in batches if batch.review_status == "reviewed"]
                ),
                "candidate_total": len(candidates),
                "keep_total": len([candidate for candidate in candidates if candidate.decision == "keep"]),
                "reject_total": len([candidate for candidate in candidates if candidate.decision == "reject"]),
                "pending_total": len([candidate for candidate in candidates if candidate.decision == "pending"]),
            },
            "batches": [batch.to_dict() for batch in batches],
            "candidates": [candidate.to_dict() for candidate in candidates],
        }

    def dashboard_acquire(self) -> dict[str, Any]:
        papers = [paper for paper in self.list_papers() if paper.stage == "acquire"]
        return {
            "summary": {
                "curated_total": len(papers),
                "needs_pdf_total": len(
                    [paper for paper in papers if paper.status == "needs-pdf"]
                ),
                "needs_review_total": len(
                    [paper for paper in papers if paper.status == "needs-review"]
                ),
                "failed_total": len([paper for paper in papers if paper.status == "failed"]),
                "parse_failed_total": len([paper for paper in papers if paper.status == "parse-failed"]),
            },
            "queue": [paper.to_dict() for paper in papers],
        }

    def dashboard_library(self) -> dict[str, Any]:
        papers = [paper for paper in self.list_papers() if paper.stage == "library"]
        unclassified = [
            paper
            for paper in papers
            if not paper.domain or paper.domain == "unclassified"
        ]
        return {
            "summary": {
                "library_total": len(papers),
                "unclassified_total": len(unclassified),
                "processed_total": len(
                    [paper for paper in papers if paper.status == "processed"]
                ),
                "needs_review_total": len([paper for paper in papers if paper.status == "needs-review"]),
                "parse_failed_total": len([paper for paper in papers if paper.status == "parse-failed"]),
            },
            "papers": [paper.to_dict() for paper in papers],
        }

    def _status_counts(self, papers: list[PaperRecord]) -> dict[str, int]:
        counts = Counter(paper.status for paper in papers)
        return dict(sorted(counts.items()))

    def _to_ingest_input(
        self,
        source: Path | IngestPaperInput,
        *,
        domain: str | None,
        area: str | None,
        topic: str | None,
        target_path: str | None,
        move: bool,
    ) -> IngestPaperInput:
        if isinstance(source, IngestPaperInput):
            if source.move == move:
                return source
            return IngestPaperInput(
                source=source.source,
                domain=source.domain,
                area=source.area,
                topic=source.topic,
                target_path=source.target_path,
                move=move,
            )
        return IngestPaperInput(
            source=source,
            domain=domain,
            area=area,
            topic=topic,
            target_path=target_path,
            move=move,
        )

    def _to_generate_note_input(
        self,
        metadata: dict[str, Any] | GenerateNoteInput,
    ) -> GenerateNoteInput:
        if isinstance(metadata, GenerateNoteInput):
            return metadata
        raw_tags = metadata.get("tags", ["paper"])
        tags = [str(tag) for tag in raw_tags] if isinstance(raw_tags, list) else [str(raw_tags)]
        return GenerateNoteInput(
            title=str(metadata.get("title") or ""),
            year=metadata.get("year"),
            venue=str(metadata.get("venue") or ""),
            doi=str(metadata.get("doi") or ""),
            domain=str(metadata.get("domain") or ""),
            area=str(metadata.get("area") or ""),
            topic=str(metadata.get("topic") or ""),
            status=str(metadata.get("status") or "draft"),
            tags=tags or ["paper"],
        )
