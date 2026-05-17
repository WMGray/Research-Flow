from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from backend.core.config import get_settings
from backend.core.services.papers.models import (
    BatchRecord,
    CandidateRecord,
    GenerateNoteInput,
    ImportPaperInput,
    IngestPaperInput,
    ParsePdfInput,
    ParserRunRecord,
    PaperEventRecord,
    PaperRecord,
    ReviewDecisionInput,
    UpdateClassificationInput,
)
from backend.core.services.papers.parser import parse_pdf, parser_health
from backend.core.services.papers.repository import PaperRepository
from backend.core.services.papers.utils import utc_now


class PaperService:
    def __init__(
        self,
        data_root: Path | None = None,
        data_layout: str | None = None,
        repository: PaperRepository | None = None,
    ) -> None:
        settings = get_settings()
        resolved_root = data_root or settings.data_root
        resolved_layout = data_layout or settings.data_layout
        self.repository = repository or PaperRepository(resolved_root, data_layout=resolved_layout)

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

    def set_candidate_batch_decision(
        self,
        batch_id: str,
        candidate_ids: list[str],
        decision: str,
    ) -> list[CandidateRecord]:
        return self.repository.set_candidate_batch_decision(batch_id, candidate_ids, decision)

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

    def import_paper(self, request: ImportPaperInput) -> PaperRecord:
        return self.repository.import_paper(request)

    def refresh_metadata(self, paper_id: str, query: dict[str, Any] | None = None) -> PaperRecord:
        return self.repository.refresh_metadata(paper_id, query)

    def metadata_sources(self, paper_id: str) -> dict[str, Any]:
        return self.repository.metadata_sources(paper_id)

    def update_metadata(self, paper_id: str, updates: dict[str, Any]) -> PaperRecord:
        return self.repository.update_metadata(paper_id, updates)

    def paper_content(self, paper_id: str, *, max_chars: int = 4000) -> dict[str, Any]:
        return self.repository.paper_content(paper_id, max_chars=max_chars)

    def set_starred(self, paper_id: str, starred: bool) -> PaperRecord:
        return self.repository.set_starred(paper_id, starred)

    def bind_assets(self, paper_id: str, source: Path, *, move: bool = False) -> PaperRecord:
        return self.repository.bind_assets(paper_id, source, move=move)

    def list_research_logs(self, paper_id: str) -> list[dict[str, Any]]:
        return self.repository.list_research_logs(paper_id)

    def create_research_log(self, paper_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.repository.create_research_log(paper_id, payload)

    def update_research_log(self, paper_id: str, log_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.repository.update_research_log(paper_id, log_id, payload)

    def delete_research_log(self, paper_id: str, log_id: str) -> None:
        self.repository.delete_research_log(paper_id, log_id)

    def get_search_agent_settings(self) -> dict[str, Any]:
        return self.repository.get_search_agent_settings()

    def update_search_agent_settings(self, updates: dict[str, Any]) -> dict[str, Any]:
        return self.repository.update_search_agent_settings(updates)

    def create_search_batch(self, request: dict[str, Any]) -> dict[str, Any]:
        return self.repository.create_search_batch(request)

    def get_search_job(self, job_id: str) -> dict[str, Any]:
        return self.repository.get_search_job(job_id)

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

    def accept_paper(self, paper_id: str) -> PaperRecord:
        return self.repository.accept_paper(paper_id)

    def update_classification(
        self,
        request: UpdateClassificationInput | str,
        *,
        domain: str = "",
        area: str = "",
        topic: str = "",
    ) -> PaperRecord:
        payload = request if isinstance(request, UpdateClassificationInput) else UpdateClassificationInput(paper_id=request, domain=domain, area=area, topic=topic)
        return self.repository.update_classification(payload)

    def create_library_folder(self, relative_path: str) -> dict[str, str]:
        path = self.repository.create_library_folder(relative_path)
        return {
            "path": str(path),
            "relative_path": str(path.relative_to(self.repository.library_root)).replace("\\", "/"),
        }

    def list_library_folders(self) -> list[str]:
        root = self.repository.library_root
        if not root.exists():
            return []
        folders: list[str] = []
        for path in sorted(item for item in root.rglob("*") if item.is_dir()):
            if self._looks_like_paper_dir(path):
                continue
            relative = path.relative_to(root)
            if 1 <= len(relative.parts) <= 3:
                folders.append(str(relative).replace("\\", "/"))
        return folders

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

    def list_paper_events(self, paper_id: str) -> list[PaperEventRecord]:
        return self.repository.list_paper_events(paper_id)

    def review_refined(
        self,
        request: ReviewDecisionInput | str,
        *,
        decision: str = "",
        comment: str = "",
    ) -> PaperRecord:
        payload = request if isinstance(request, ReviewDecisionInput) else ReviewDecisionInput(paper_id=request, decision=decision, comment=comment)
        return self.repository.review_refined(payload)

    def review_note(
        self,
        request: ReviewDecisionInput | str,
        *,
        decision: str = "",
        comment: str = "",
    ) -> PaperRecord:
        payload = request if isinstance(request, ReviewDecisionInput) else ReviewDecisionInput(paper_id=request, decision=decision, comment=comment)
        return self.repository.review_note(payload)

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

    def _workflow_queue(self, papers: list[PaperRecord]) -> list[PaperRecord]:
        return [
            paper
            for paper in papers
            if paper.workflow_status not in {"ready"} and not paper.rejected
        ]

    def dashboard_home(self) -> dict[str, Any]:
        papers = self.list_papers()
        batches = self.list_batches()
        status_counts = self._status_counts(papers)
        queue_items = self._workflow_queue(papers)
        return {
            "totals": {
                "papers": len(papers),
                "batches": len(batches),
                "processed": len([paper for paper in papers if paper.review_status == "accepted"]),
                "curated": len([paper for paper in papers if paper.stage == "acquire"]),
                "library": len([paper for paper in papers if paper.stage == "library"]),
                "queued": len(queue_items),
                "needs_pdf": len([paper for paper in papers if paper.asset_status == "missing_pdf"]),
                "needs_review": len([paper for paper in papers if paper.parser_status == "parsed" and paper.refined_review_status != "approved"]),
                "parse_failed": len([paper for paper in papers if paper.parser_status == "failed"]),
                "failed": len([paper for paper in papers if paper.parser_status == "failed"]),
            },
            "status_counts": status_counts,
            "recent_papers": [paper.to_dict() for paper in papers[:6]],
            "queue_items": [paper.to_dict() for paper in queue_items[:8]],
            "recent_batches": [batch.to_dict() for batch in batches[:5]],
            "paths": {
                "data_root": str(self.repository.data_root),
                "discover_root": str(self.repository.discover_root),
                "papers_root": str(self.repository.library_root),
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

    def dashboard_papers(self) -> dict[str, Any]:
        papers = [paper for paper in self.list_papers() if paper.stage == "library" and paper.review_status == "accepted"]
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
                    [paper for paper in papers if paper.review_status == "accepted"]
                ),
                "needs_review_total": len(
                    [
                        paper
                        for paper in papers
                        if paper.workflow_status
                        in {"refine_review_pending", "refine_rejected", "note_review_pending", "note_rejected", "failed"}
                    ]
                ),
                "refine_review_total": len([paper for paper in papers if paper.workflow_status == "refine_review_pending"]),
                "note_review_total": len([paper for paper in papers if paper.workflow_status == "note_review_pending"]),
                "parse_failed_total": len([paper for paper in papers if paper.parser_status == "failed"]),
            },
            "papers": [paper.to_dict() for paper in papers],
            "paths": {
                "library_root": str(self.repository.library_root),
            },
            "folders": self.list_library_folders(),
        }

    def _status_counts(self, papers: list[PaperRecord]) -> dict[str, int]:
        counts = Counter(paper.status for paper in papers)
        return dict(sorted(counts.items()))

    def _looks_like_paper_dir(self, path: Path) -> bool:
        return any((path / name).exists() for name in ("metadata.yaml", "metadata.json", "state.json", "paper.pdf", "note.md"))

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
