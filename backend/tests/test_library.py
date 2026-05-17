from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.app.library import PaperLibrary, slugify, write_json, write_text, write_yaml
from backend.core.services.papers import parser as paper_parser
from backend.core.services.papers.parser import PdfParserResult
from backend.core.services.papers.utils import read_json


def write_sample_pdf(path: Path) -> None:
    path.write_text(
        "%PDF-1.4\n"
        "1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        "2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        "3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] >> endobj\n"
        "xref\n0 4\n0000000000 65535 f \n0000000010 00000 n \n0000000060 00000 n \n0000000112 00000 n \n"
        "trailer << /Root 1 0 R /Size 4 >>\nstartxref\n164\n%%EOF\n",
        encoding="utf-8",
        newline="\n",
    )


def create_source_paper(
    root: Path,
    *,
    title: str,
    metadata: dict[str, Any] | None = None,
    with_note: bool = True,
    with_pdf: bool = True,
) -> Path:
    paper_dir = root / slugify(title)
    paper_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "title": title,
        "year": 2024,
        "venue": "CVPR 2024",
        "status": "curated",
        "tags": ["paper"],
    }
    if metadata:
        payload.update(metadata)

    write_yaml(paper_dir / "metadata.yaml", payload)
    if with_note:
        write_text(
            paper_dir / "note.md",
            "---\n"
            f"title: {title}\n"
            "year: 2024\n"
            "venue: CVPR 2024\n"
            "status: curated\n"
            "tags:\n"
            "  - paper\n"
            "---\n\n# 摘要\n",
        )
    if with_pdf:
        write_sample_pdf(paper_dir / "paper.pdf")
    return paper_dir


def test_slugify_basic() -> None:
    assert (
        slugify("Long-Context Speech Synthesis with Context-Aware Memory")
        == "long-context-speech-synthesis-with-context-aware-memory"
    )


def test_dashboard_summary_reads_sample_data(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    library = PaperLibrary(data_root)

    batch_dir = data_root / "Discover" / "search_batches" / "2026-05-08-sample"
    batch_dir.mkdir(parents=True, exist_ok=True)
    write_json(batch_dir / "candidates.json", [{"title": "Example"}])
    write_text(batch_dir / "review.md", "| ID | Decision |\n| --- | --- |\n| P001 | keep |\n")

    paper_dir = data_root / "Library" / "Computer-Vision" / "Video-Understanding" / "Action-Anticipation" / "example-paper"
    paper_dir.mkdir(parents=True, exist_ok=True)
    write_sample_pdf(paper_dir / "paper.pdf")
    write_text(
        paper_dir / "note.md",
        "---\n"
        "title: Example Paper\n"
        "year: 2024\n"
        "venue: CVPR 2024\n"
        "domain: Computer-Vision\n"
        "area: Video-Understanding\n"
        "topic: Action-Anticipation\n"
        "status: processed\n"
        "tags:\n"
        "  - paper\n"
        "---\n\n# 摘要\n",
    )
    write_yaml(
        paper_dir / "metadata.yaml",
        {
            "title": "Example Paper",
            "year": 2024,
            "venue": "CVPR 2024",
            "domain": "Computer-Vision",
            "area": "Video-Understanding",
            "topic": "Action-Anticipation",
            "status": "processed",
            "tags": ["paper", "domain/Computer-Vision"],
            "updated_at": "2026-05-14T00:00:00+00:00",
        },
    )

    summary = library.dashboard_home()
    assert summary["totals"]["papers"] == 1
    assert summary["totals"]["batches"] == 1
    assert summary["totals"]["processed"] == 1
    assert summary["recent_papers"][0]["title"] == "Example Paper"


def test_metadata_priority_prefers_state_over_json_and_yaml(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    library = PaperLibrary(data_root)
    paper_dir = data_root / "Library" / "Speech" / "TTS" / "priority-paper"
    paper_dir.mkdir(parents=True, exist_ok=True)
    write_sample_pdf(paper_dir / "paper.pdf")
    write_yaml(paper_dir / "metadata.yaml", {"title": "YAML Title", "status": "processed"})
    write_json(paper_dir / "metadata.json", {"title": "JSON Title", "status": "needs-review"})
    write_json(paper_dir / "state.json", {"title": "State Title", "status": "parse-failed"})

    record = library.get_paper("priority-paper")

    assert record is not None
    assert record.title == "State Title"
    assert record.status == "parse-failed"


def test_ingest_generates_note_and_needs_pdf_status(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    library = PaperLibrary(data_root)
    source_dir = create_source_paper(
        tmp_path / "incoming",
        title="Flow Matching for Singing Voice",
        metadata={"year": 2025, "venue": "Preprint"},
        with_note=False,
        with_pdf=False,
    )

    record = library.ingest(
        source_dir,
        domain="Speech",
        area="Voice-Synthesis",
        topic="Singing-Voice-Synthesis",
    )

    target_dir = Path(record.path)
    assert record.status == "needs-pdf"
    assert target_dir.exists()
    assert (target_dir / "note.md").exists()
    assert (target_dir / "metadata.yaml").exists()
    assert not (target_dir / "paper.pdf").exists()


def test_generate_note_for_paper_does_not_overwrite_by_default(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    library = PaperLibrary(data_root)
    source_dir = create_source_paper(tmp_path / "incoming", title="Note Sample", with_note=False)
    record = library.ingest(source_dir, domain="Speech", area="TTS", topic="Control")
    note_path = Path(record.note_path)
    write_text(note_path, "# Human edits\n")

    generated = library.generate_note_for_paper(record.paper_id)

    assert generated.note_path == str(note_path)
    assert note_path.read_text(encoding="utf-8") == "# Human edits\n"


def test_ingest_conflict_marks_existing_target_for_review(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    library = PaperLibrary(data_root)

    existing_dir = data_root / "01_Papers" / "Speech" / "Voice-Synthesis" / "Singing-Voice-Synthesis" / "conflict-paper"
    existing_dir.mkdir(parents=True, exist_ok=True)
    write_text(existing_dir / "note.md", "# Existing\n")
    write_yaml(
        existing_dir / "metadata.yaml",
        {
            "title": "Conflict Paper",
            "status": "processed",
            "updated_at": "2026-05-14T00:00:00+00:00",
        },
    )

    source_dir = create_source_paper(
        tmp_path / "incoming",
        title="Conflict Paper",
        metadata={
            "domain": "Speech",
            "area": "Voice-Synthesis",
            "topic": "Singing-Voice-Synthesis",
        },
    )

    record = library.ingest(source_dir, domain="Speech", area="Voice-Synthesis", topic="Singing-Voice-Synthesis")

    metadata = writeback = Path(record.metadata_path)
    assert record.status == "needs-review"
    assert metadata.exists()
    assert "Target already exists" in metadata.read_text(encoding="utf-8")
    assert (existing_dir / "note.md").read_text(encoding="utf-8") == "# Existing\n"
    assert (existing_dir / "metadata.json").exists()
    assert (existing_dir / "state.json").exists()


def test_migrate_moves_source_directory_into_library(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    library = PaperLibrary(data_root)
    source_dir = create_source_paper(
        tmp_path / "Acquire" / "curated",
        title="Temporal Progressive Attention",
        metadata={"status": "curated"},
    )
    write_text(source_dir / "extra.txt", "keep me\n")

    record = library.migrate(
        source_dir,
        domain="Computer-Vision",
        area="Video-Understanding",
        topic="Action-Anticipation",
    )

    target_dir = Path(record.path)
    assert record.status == "parse-pending"
    assert record.stage == "library"
    assert record.asset_status == "pdf_ready"
    assert record.review_status == "pending"
    assert target_dir.exists()
    assert (target_dir / "paper.pdf").exists()
    assert (target_dir / "extra.txt").exists()
    assert not source_dir.exists()


def test_reject_deletes_paper_directory(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    library = PaperLibrary(data_root)
    source_dir = create_source_paper(tmp_path / "incoming", title="Reject Sample")
    record = library.ingest(source_dir, domain="Speech", area="TTS", topic="Control")

    rejected = library.reject_paper(record.paper_id)

    assert rejected.status == "rejected"
    assert not Path(rejected.path).exists()
    assert rejected.rejected is True


def test_candidate_reject_deletes_entry_and_artifacts(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    library = PaperLibrary(data_root)
    batch_dir = data_root / "Discover" / "search_batches" / "batch-a"
    batch_dir.mkdir(parents=True, exist_ok=True)
    artifact_dir = data_root / "Discover" / "landing" / "candidate-a"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    write_text(artifact_dir / "paper.pdf", "pdf\n")
    write_json(
        batch_dir / "candidates.json",
        {
            "candidates": [
                {
                    "id": "P001",
                    "title": "Candidate A",
                    "result_path": "Discover/landing/candidate-a",
                },
                {
                    "id": "P002",
                    "title": "Candidate B",
                },
            ]
        },
    )

    rejected = library.set_candidate_decision("batch-a", "P001", "reject")
    rows = read_json(batch_dir / "candidates.json")["candidates"]

    assert rejected.decision == "reject"
    assert not artifact_dir.exists()
    assert len(rows) == 1
    assert rows[0]["id"] == "P002"


def test_candidate_keep_moves_entry_to_library_and_removes_from_batch(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    library = PaperLibrary(data_root)
    batch_dir = data_root / "Discover" / "search_batches" / "batch-keep"
    batch_dir.mkdir(parents=True, exist_ok=True)
    candidate_dir = batch_dir / "results" / "candidate-a"
    candidate_dir.mkdir(parents=True, exist_ok=True)
    write_sample_pdf(candidate_dir / "paper.pdf")
    write_json(
        candidate_dir / "metadata.json",
        {
            "title": "Candidate Keep",
            "year": 2026,
            "venue": "AAAI",
            "domain": "Speech",
            "area": "Detection",
            "topic": "Deepfake",
            "relevance_reason_zh": "理由",
        },
    )
    write_json(
        batch_dir / "candidates.json",
        {
            "candidates": [
                {
                    "id": "P001",
                    "title": "Candidate Keep",
                    "year": 2026,
                    "venue": "AAAI",
                    "domain": "Speech",
                    "area": "Detection",
                    "topic": "Deepfake",
                    "result_path": "Discover/search_batches/batch-keep/results/candidate-a",
                    "landing_path": "Discover/search_batches/batch-keep/results/candidate-a/paper.pdf",
                    "relevance_reason_zh": "理由",
                }
            ]
        },
    )

    kept = library.set_candidate_decision("batch-keep", "P001", "keep")

    assert kept.decision == "keep"
    assert not batch_dir.exists()
    library_target = data_root / "01_Papers" / "Speech" / "Detection" / "Deepfake" / "candidate-keep"
    assert library_target.exists()
    assert (library_target / "paper.pdf").exists()
    assert (library_target / "metadata.yaml").exists()
    record = next(paper for paper in library.list_papers() if Path(paper.path) == library_target)
    assert record.stage == "library"
    assert record.review_status == "accepted"


def test_batch_deleted_when_no_pending_candidates_remain(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    library = PaperLibrary(data_root)
    batch_dir = data_root / "Discover" / "search_batches" / "batch-finished"
    batch_dir.mkdir(parents=True, exist_ok=True)
    write_text(batch_dir / "search.md", "# search\n")
    write_json(
        batch_dir / "candidates.json",
        {
            "candidates": [
                {
                    "id": "P001",
                    "title": "Candidate A",
                    "gate1_decision": "keep",
                },
                {
                    "id": "P002",
                    "title": "Candidate B",
                    "gate1_decision": "reject",
                },
            ]
        },
    )

    removed = library.cleanup_batch("batch-finished")

    assert removed is True
    assert not batch_dir.exists()


def test_restore_batch_candidates_rebuilds_from_search_report_and_results(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    library = PaperLibrary(data_root)
    batch_dir = data_root / "Discover" / "search_batches" / "batch-restore"
    result_dir = batch_dir / "results" / "candidate-a"
    result_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        result_dir / "metadata.json",
        {
            "title": "Candidate A",
            "authors": ["Alice"],
            "year": "2026",
            "venue": "AAAI",
            "source_type": "official-proceedings",
            "landing_status": "pdf-downloaded",
            "landing_path": "Discover/search_batches/batch-restore/results/candidate-a/paper.pdf",
        },
    )
    write_text(
        batch_dir / "search.md",
        "## Candidates\n\n"
        "| Venue | Year | Type | Title | Paper | PDF | Relevance | Local Status |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
        "| AAAI | 2026 | Benchmark | Candidate A | [paper](https://example.com/a) | [PDF](https://example.com/a.pdf) | core | PDF downloaded: Discover/search_batches/batch-restore/results/candidate-a/paper.pdf |\n"
        "| AAAI | 2025 | Method | Candidate B | [paper](https://example.com/b) | [PDF pending download](https://example.com/b.pdf) | pending | PDF pending download |\n",
    )
    write_json(batch_dir / "candidates.json", [])

    restored = library.restore_batch_candidates("batch-restore")
    rows = read_json(batch_dir / "candidates.json")

    assert len(restored) == 2
    assert len(rows) == 2
    assert rows[0]["title"] == "Candidate A"
    assert rows[0]["source_type"] == "official-proceedings"
    assert rows[1]["title"] == "Candidate B"
    assert rows[1]["landing_status"] == "metadata-only"


def test_config_health_reports_required_paths(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    library = PaperLibrary(data_root)

    health = library.config_health()

    assert health["paths"]["data_root"]["exists"] is True
    assert health["paths"]["discover_root"]["exists"] is True
    assert "parser" in health


def test_parse_pdf_fails_when_mineru_unavailable(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_root = tmp_path / "data"
    library = PaperLibrary(data_root)
    source_dir = create_source_paper(tmp_path / "incoming", title="Parse Sample")
    record = library.ingest(source_dir, domain="Speech", area="TTS", topic="Control")
    monkeypatch.delenv("RFLOW_MINERU_API_TOKEN", raising=False)
    monkeypatch.delenv("MINERU__API_TOKEN", raising=False)
    monkeypatch.delenv("MINERU_API_TOKEN", raising=False)
    monkeypatch.setattr(paper_parser, "_dotenv_payload", lambda: {})

    parsed = library.parse_pdf(record.paper_id, parser="auto", force=True)

    assert parsed.parser_status == "failed"
    assert parsed.status == "parse-failed"
    assert Path(parsed.state_path).exists()


def test_parse_pdf_missing_pdf_marks_needs_pdf(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    library = PaperLibrary(data_root)
    source_dir = create_source_paper(tmp_path / "incoming", title="Missing Pdf Sample", with_pdf=False)
    record = library.ingest(source_dir, domain="Speech", area="TTS", topic="Control")

    parsed = library.parse_pdf(record.paper_id, parser="mineru", force=True)

    assert parsed.status == "needs-pdf"


def test_record_parser_result_clears_stale_error_after_success(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    library = PaperLibrary(data_root)
    source_dir = create_source_paper(tmp_path / "incoming", title="Parser Success Sample")
    record = library.ingest(source_dir, domain="Speech", area="TTS", topic="Control")
    paper_dir = Path(record.path)
    parsed_dir = paper_dir / "parsed"
    parsed_dir.mkdir(parents=True, exist_ok=True)
    write_text(paper_dir / "refined.md", "# Parsed\n")
    write_text(parsed_dir / "text.md", "# Parsed\n")
    write_text(parsed_dir / "sections.json", "{}\n")
    library.repository.update_paper_state(paper_dir, {"error": "previous failure"})

    updated = library.repository.record_parser_result(
        record.paper_id,
        PdfParserResult(
            status="processed",
            parser="mineru",
            refined_path=str(paper_dir / "refined.md"),
            image_dir=str(paper_dir / "images"),
            text_path=str(parsed_dir / "text.md"),
            sections_path=str(parsed_dir / "sections.json"),
            error="network failure",
        ),
        started_at="2026-05-15T00:00:00+00:00",
    )

    assert updated.parser_status == "parsed"
    assert updated.error == ""
    assert updated.refined_review_status == "pending"
    assert updated.capabilities.generate_note is False
    runs = read_json(paper_dir / "parser_runs.json")
    assert runs[-1]["error"] == "network failure"
    events = library.list_paper_events(record.paper_id)
    assert [event.event for event in events][-2:] == ["parse_succeeded", "refined_generated"]


def test_refined_and_note_reviews_gate_ready_workflow(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    library = PaperLibrary(data_root)
    source_dir = create_source_paper(tmp_path / "incoming", title="Review Gate Sample", with_note=False)
    record = library.ingest(source_dir, domain="Speech", area="TTS", topic="Control")
    paper_dir = Path(record.path)
    Path(record.note_path).unlink()
    library.repository.update_paper_state(paper_dir, {"classification_status": "classified", "note_status": "missing", "note_review_status": "missing"})
    parsed_dir = paper_dir / "parsed"
    parsed_dir.mkdir(parents=True, exist_ok=True)
    write_text(paper_dir / "refined.md", "# Refined\n")
    write_text(parsed_dir / "text.md", "# Parsed\n")
    write_text(parsed_dir / "sections.json", "{}\n")

    parsed = library.repository.record_parser_result(
        record.paper_id,
        PdfParserResult(
            status="processed",
            parser="mineru",
            refined_path=str(paper_dir / "refined.md"),
            image_dir=str(paper_dir / "images"),
            text_path=str(parsed_dir / "text.md"),
            sections_path=str(parsed_dir / "sections.json"),
            error="",
        ),
        started_at="2026-05-15T00:00:00+00:00",
    )

    assert parsed.workflow_status == "refine_review_pending"
    assert parsed.capabilities.generate_note is False

    approved_refined = library.review_refined(parsed.paper_id, decision="approved")
    assert approved_refined.refined_review_status == "approved"
    assert approved_refined.workflow_status == "note_missing"
    assert approved_refined.capabilities.generate_note is True

    generated = library.generate_note_for_paper(parsed.paper_id)
    assert generated.note_status == "review_pending"
    assert generated.note_review_status == "pending"
    assert generated.workflow_status == "note_review_pending"
    assert generated.capabilities.review_note is True

    approved_note = library.review_note(parsed.paper_id, decision="approved")
    assert approved_note.note_review_status == "approved"
    assert approved_note.workflow_status == "ready"

    events = [event.event for event in library.list_paper_events(parsed.paper_id)]
    assert "refined_review_approved" in events
    assert "llm_note_generated" in events
    assert "note_review_approved" in events
    assert "workflow_ready" in events


def test_rejected_reviews_block_workflow(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    library = PaperLibrary(data_root)
    paper_dir = data_root / "Library" / "Speech" / "TTS" / "rejected-review"
    paper_dir.mkdir(parents=True, exist_ok=True)
    write_sample_pdf(paper_dir / "paper.pdf")
    write_text(paper_dir / "refined.md", "# Refined\n")
    write_text(paper_dir / "note.md", "# Note\n")
    write_yaml(
        paper_dir / "metadata.yaml",
        {
            "title": "Rejected Review",
            "asset_status": "pdf_ready",
            "parser_status": "parsed",
            "review_status": "accepted",
            "note_status": "review_pending",
            "refined_review_status": "approved",
            "note_review_status": "pending",
            "classification_status": "classified",
        },
    )
    library.repository.update_paper_state(paper_dir, {})
    record = library.get_paper("Library__Speech__TTS__rejected-review")
    assert record is not None

    rejected_note = library.review_note(record.paper_id, decision="rejected")
    assert rejected_note.workflow_status == "note_rejected"
    assert rejected_note.capabilities.review_note is True

    rejected_refined = library.review_refined(record.paper_id, decision="rejected")
    assert rejected_refined.workflow_status == "refine_rejected"
    assert rejected_refined.capabilities.generate_note is False


def test_accept_moves_acquire_paper_into_library_and_exposes_new_capabilities(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    library = PaperLibrary(data_root)
    paper_dir = data_root / "Acquire" / "curated" / "accept-sample"
    paper_dir.mkdir(parents=True, exist_ok=True)
    write_sample_pdf(paper_dir / "paper.pdf")
    write_text(paper_dir / "note.md", "---\ntitle: Accept Sample\n---\n")
    write_yaml(
        paper_dir / "metadata.yaml",
        {
            "title": "Accept Sample",
            "domain": "Speech",
            "area": "TTS",
            "topic": "Control",
            "asset_status": "pdf_ready",
            "parser_status": "parsed",
            "review_status": "pending",
            "note_status": "template",
        },
    )
    library.repository.update_paper_state(paper_dir, {})

    record = library.get_paper("Acquire__curated__accept-sample")
    assert record is not None
    assert record.capabilities.accept is True
    accepted = library.accept_paper(record.paper_id)

    assert accepted.stage == "library"
    assert accepted.review_status == "accepted"
    assert accepted.status == "processed"
    assert Path(accepted.path).exists()
    assert not paper_dir.exists()


def test_update_classification_moves_library_paper(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    library = PaperLibrary(data_root)
    paper_dir = data_root / "Library" / "unclassified" / "classification-sample"
    paper_dir.mkdir(parents=True, exist_ok=True)
    write_sample_pdf(paper_dir / "paper.pdf")
    write_text(paper_dir / "note.md", "---\ntitle: Classification Sample\n---\n")
    write_yaml(
        paper_dir / "metadata.yaml",
        {
            "title": "Classification Sample",
            "asset_status": "pdf_ready",
            "parser_status": "parsed",
            "review_status": "accepted",
        },
    )
    library.repository.update_paper_state(paper_dir, {})
    record = library.get_paper("Library__unclassified__classification-sample")
    assert record is not None

    updated = library.update_classification(
        record.paper_id,
        domain="Computer-Vision",
        area="Video-Understanding",
        topic="Action-Anticipation",
    )

    target_dir = data_root / "01_Papers" / "Computer-Vision" / "Video-Understanding" / "Action-Anticipation" / "classification-sample"
    assert updated.stage == "library"
    assert updated.status == "processed"
    assert updated.domain == "Computer-Vision"
    assert updated.area == "Video-Understanding"
    assert updated.topic == "Action-Anticipation"
    assert Path(updated.path) == target_dir
    assert target_dir.exists()
    assert not paper_dir.exists()

    cleared = library.update_classification(updated.paper_id, domain="", area="", topic="")
    cleared_dir = data_root / "01_Papers" / "unclassified" / "classification-sample"

    assert cleared.domain == ""
    assert cleared.area == ""
    assert cleared.topic == ""
    assert cleared.classification_status == "pending"
    assert Path(cleared.path) == cleared_dir
    assert cleared_dir.exists()
    assert not target_dir.exists()


def test_native_layout_reads_legacy_library_but_writes_to_01_papers(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    library = PaperLibrary(data_root)
    legacy_dir = data_root / "Library" / "Legacy" / "legacy-paper"
    legacy_dir.mkdir(parents=True, exist_ok=True)
    write_sample_pdf(legacy_dir / "paper.pdf")
    write_text(legacy_dir / "note.md", "---\ntitle: Legacy Paper\n---\n")
    write_yaml(
        legacy_dir / "metadata.yaml",
        {
            "title": "Legacy Paper",
            "asset_status": "pdf_ready",
            "parser_status": "parsed",
            "review_status": "accepted",
        },
    )
    library.repository.update_paper_state(legacy_dir, {})

    record = library.get_paper("Library__Legacy__legacy-paper")
    assert record is not None
    assert record.stage == "library"

    updated = library.update_classification(
        record.paper_id,
        domain="Computer-Vision",
        area="Tracking",
        topic="MOT",
    )

    target_dir = data_root / "01_Papers" / "Computer-Vision" / "Tracking" / "MOT" / "legacy-paper"
    assert Path(updated.path) == target_dir
    assert target_dir.exists()
    assert not legacy_dir.exists()
