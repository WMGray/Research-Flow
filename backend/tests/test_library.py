from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.app.library import PaperLibrary, slugify, write_json, write_text, write_yaml
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

    existing_dir = data_root / "Library" / "Speech" / "Voice-Synthesis" / "Singing-Voice-Synthesis" / "conflict-paper"
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
    assert record.status == "processed"
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


def test_candidate_keep_moves_entry_to_acquire_and_removes_from_batch(tmp_path: Path) -> None:
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
    curated_root = data_root / "Acquire" / "curated"
    curated_dirs = [path for path in curated_root.iterdir() if path.is_dir()]
    assert len(curated_dirs) == 1
    assert (curated_dirs[0] / "paper.pdf").exists()
    assert (curated_dirs[0] / "metadata.yaml").exists()


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


def test_parse_pdf_falls_back_to_pymupdf_when_mineru_unavailable(
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

    parsed = library.parse_pdf(record.paper_id, parser="auto", force=True)

    assert parsed.status in {"processed", "parse-failed"}
    assert Path(parsed.state_path).exists()


def test_parse_pdf_missing_pdf_marks_needs_pdf(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    library = PaperLibrary(data_root)
    source_dir = create_source_paper(tmp_path / "incoming", title="Missing Pdf Sample", with_pdf=False)
    record = library.ingest(source_dir, domain="Speech", area="TTS", topic="Control")

    parsed = library.parse_pdf(record.paper_id, parser="pymupdf", force=True)

    assert parsed.status == "needs-pdf"
