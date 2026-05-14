from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from fastapi.testclient import TestClient

from backend.app.library import PaperLibrary, slugify, write_text, write_yaml
from backend.app.main import app


TMP_ROOT = Path(__file__).resolve().parents[1] / ".pytest_tmp"
TMP_ROOT.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("PYTEST_DEBUG_TEMPROOT", str(TMP_ROOT))

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


def create_source_paper(root: Path, *, title: str, with_pdf: bool = True) -> Path:
    paper_dir = root / slugify(title)
    paper_dir.mkdir(parents=True, exist_ok=True)
    write_yaml(
        paper_dir / "metadata.yaml",
        {
            "title": title,
            "year": 2024,
            "venue": "CVPR 2024",
            "status": "curated",
            "tags": ["paper"],
        },
    )
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


@contextmanager
def isolated_client(tmp_path: Path) -> Iterator[TestClient]:
    original = getattr(app.state, "library", None)
    app.state.library = PaperLibrary(tmp_path / "data")
    try:
        yield client
    finally:
        if original is None:
            delattr(app.state, "library")
            return
        app.state.library = original


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_dashboard_home_payload() -> None:
    response = client.get("/api/dashboard/home")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert "totals" in payload["data"]


def test_papers_list_and_detail() -> None:
    response = client.get("/api/papers")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["total"] >= 1

    first_item = payload["data"]["items"][0]
    detail = client.get(f"/api/papers/{first_item['paper_id']}")
    assert detail.status_code == 200
    assert detail.json()["data"]["paper_id"] == first_item["paper_id"]


def test_generate_note_template_endpoint() -> None:
    response = client.post(
        "/api/papers/generate-note",
        json={
            "title": "Example Paper",
            "year": 2026,
            "venue": "ICLR 2026",
            "domain": "Speech",
            "area": "Voice-Synthesis",
            "topic": "Flow-Matching",
        },
    )
    assert response.status_code == 200
    content = response.json()["data"]["content"]
    assert "Example Paper" in content
    assert "Flow-Matching" in content


def test_ingest_endpoint_creates_needs_pdf_record(tmp_path: Path) -> None:
    source_dir = create_source_paper(tmp_path / "incoming", title="API Ingest Sample", with_pdf=False)

    with isolated_client(tmp_path) as test_client:
        response = test_client.post(
            "/api/papers/ingest",
            json={
                "source": str(source_dir),
                "domain": "Speech",
                "area": "Voice-Synthesis",
                "topic": "Singing-Voice-Synthesis",
            },
        )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["status"] == "needs-pdf"
    assert Path(payload["note_path"]).exists()


def test_migrate_endpoint_moves_source_into_library(tmp_path: Path) -> None:
    source_dir = create_source_paper(tmp_path / "Acquire" / "curated", title="API Migrate Sample", with_pdf=True)
    write_text(source_dir / "artifact.txt", "keep me\n")

    with isolated_client(tmp_path) as test_client:
        response = test_client.post(
            "/api/papers/migrate",
            json={
                "source": str(source_dir),
                "domain": "Computer-Vision",
                "area": "Video-Understanding",
                "topic": "Action-Anticipation",
            },
        )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["status"] == "processed"
    assert Path(payload["path"]).exists()
    assert not source_dir.exists()
