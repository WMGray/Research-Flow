from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import pytest
from fastapi.testclient import TestClient

from backend.app.library import PaperLibrary, write_json, write_text, write_yaml
from backend.app.main import app


client = TestClient(app)


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


def create_research_vault(root: Path) -> Path:
    vault = root / "05_Research"
    (vault / "02_Inbox" / "01_Search" / "batch-a").mkdir(parents=True, exist_ok=True)
    (vault / "02_Inbox" / "02_Curated").mkdir(parents=True, exist_ok=True)
    (vault / "02_Inbox" / "03_Template").mkdir(parents=True, exist_ok=True)
    (vault / "01_Papers").mkdir(parents=True, exist_ok=True)
    (vault / "06_Archives").mkdir(parents=True, exist_ok=True)

    write_json(
        vault / "02_Inbox" / "01_Search" / "batch-a" / "candidates.json",
        [
            {
                "id": "P001",
                "title": "Candidate A",
                "year": "2026",
                "venue": "AAAI",
                "gate1_decision": "keep",
            }
        ],
    )

    curated_dir = vault / "02_Inbox" / "02_Curated" / "curated-paper"
    curated_dir.mkdir(parents=True, exist_ok=True)
    write_sample_pdf(curated_dir / "paper.pdf")
    write_text(curated_dir / "refined.md", "# Parsed\n")
    write_yaml(
        curated_dir / "metadata.yaml",
        {
            "title": "Curated Paper",
            "year": "2024",
            "venue": "CVPR",
            "domain": "Computer-Vision",
            "area": "Video-Understanding",
            "topic": "Action-Anticipation",
            "status": "curated",
        },
    )
    write_json(
        curated_dir / "state.json",
        {
            "ingest_status": "curated",
            "refine_status": "processed",
            "classification_status": "pending",
        },
    )

    library_dir = vault / "01_Papers" / "Computer-Vision" / "Video-Understanding" / "Action-Anticipation" / "applied-paper"
    library_dir.mkdir(parents=True, exist_ok=True)
    write_sample_pdf(library_dir / "paper.pdf")
    write_text(library_dir / "refined.md", "# Parsed\n")
    write_yaml(
        library_dir / "metadata.yaml",
        {
            "title": "Applied Paper",
            "year": "2023",
            "venue": "CVPR",
            "domain": "Computer-Vision",
            "area": "Video-Understanding",
            "topic": "Action-Anticipation",
            "status": "applied",
            "classification_status": "applied",
            "refine_status": "processed",
        },
    )
    return vault


@contextmanager
def research_vault_client(vault: Path) -> Iterator[TestClient]:
    original = getattr(app.state, "library", None)
    app.state.library = PaperLibrary(vault, data_layout="research_vault")
    try:
        yield client
    finally:
        if original is None:
            delattr(app.state, "library")
            return
        app.state.library = original


def test_research_vault_scans_batches_curated_and_library(tmp_path: Path) -> None:
    vault = create_research_vault(tmp_path)
    library = PaperLibrary(vault, data_layout="research_vault")

    batches = library.list_batches()
    papers = library.list_papers()
    curated = next(paper for paper in papers if paper.title == "Curated Paper")
    applied = next(paper for paper in papers if paper.title == "Applied Paper")

    assert len(batches) == 1
    assert batches[0].batch_id == "batch-a"
    assert curated.stage == "acquire"
    assert curated.parser_status == "parsed"
    assert curated.capabilities.accept is True
    assert applied.stage == "library"
    assert applied.review_status == "accepted"
    assert applied.status == "processed"
    assert applied.classification_status == "accepted"


def test_research_vault_accept_moves_curated_into_01_papers(tmp_path: Path) -> None:
    vault = create_research_vault(tmp_path)
    library = PaperLibrary(vault, data_layout="research_vault")
    record = next(paper for paper in library.list_papers() if paper.title == "Curated Paper")

    accepted = library.accept_paper(record.paper_id)

    target = vault / "01_Papers" / "Computer-Vision" / "Video-Understanding" / "Action-Anticipation" / "curated-paper"
    assert accepted.stage == "library"
    assert accepted.review_status == "accepted"
    assert Path(accepted.path) == target
    assert target.exists()
    assert not (vault / "02_Inbox" / "02_Curated" / "curated-paper").exists()


def test_research_vault_reject_archives_without_deleting(tmp_path: Path) -> None:
    vault = create_research_vault(tmp_path)
    library = PaperLibrary(vault, data_layout="research_vault")
    record = next(paper for paper in library.list_papers() if paper.title == "Curated Paper")

    rejected = library.reject_paper(record.paper_id)

    archive_dir = vault / "06_Archives" / "curated-paper"
    assert rejected.status == "rejected"
    assert rejected.rejected is True
    assert Path(rejected.path) == archive_dir
    assert archive_dir.exists()
    assert (archive_dir / "paper.pdf").exists()
    assert not Path(record.path).exists()


def test_research_vault_managed_paths_stay_inside_data_root(tmp_path: Path) -> None:
    vault = create_research_vault(tmp_path)
    library = PaperLibrary(vault, data_layout="research_vault")
    batch_dir = vault / "02_Inbox" / "01_Search" / "batch-a"

    assert library.repository._resolve_managed_path("../../../../outside", batch_dir) is None
    with pytest.raises(ValueError):
        library.ingest(vault / "02_Inbox" / "02_Curated" / "curated-paper", target_path="../outside")


def test_research_vault_api_config_and_dashboards(tmp_path: Path) -> None:
    vault = create_research_vault(tmp_path)

    with research_vault_client(vault) as test_client:
        config = test_client.get("/api/config")
        discover = test_client.get("/api/dashboard/discover")
        acquire = test_client.get("/api/dashboard/acquire")
        library_payload = test_client.get("/api/dashboard/library")

    assert config.status_code == 200
    config_data = config.json()["data"]
    assert config_data["data_layout"] == "research_vault"
    assert config_data["write_policy"] == "direct-archive-reject"
    assert config_data["paths"]["search_batches_root"]["exists"] is True
    assert config_data["paths"]["curated_root"]["exists"] is True
    assert config_data["paths"]["archive_root"]["exists"] is True
    assert discover.json()["data"]["summary"]["batch_total"] == 1
    assert acquire.json()["data"]["summary"]["curated_total"] == 1
    assert library_payload.json()["data"]["summary"]["library_total"] == 1
