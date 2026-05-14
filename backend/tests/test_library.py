from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.app.library import PaperLibrary, slugify, write_json, write_text, write_yaml


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
