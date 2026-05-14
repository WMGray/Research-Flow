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


def test_generate_paper_note_endpoint_creates_missing_note(tmp_path: Path) -> None:
    source_dir = create_source_paper(tmp_path / "incoming", title="API Note Sample")

    with isolated_client(tmp_path) as test_client:
        ingest = test_client.post(
            "/api/papers/ingest",
            json={
                "source": str(source_dir),
                "domain": "Speech",
                "area": "Voice-Synthesis",
                "topic": "Singing-Voice-Synthesis",
            },
        )
        paper_id = ingest.json()["data"]["paper_id"]
        note_path = Path(ingest.json()["data"]["note_path"])
        note_path.unlink()
        response = test_client.post(f"/api/papers/{paper_id}/generate-note", json={"overwrite": False})

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["note_path"]
    assert Path(payload["note_path"]).exists()


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


def test_config_endpoint(tmp_path: Path) -> None:
    with isolated_client(tmp_path) as test_client:
        response = test_client.get("/api/config")

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["paths"]["data_root"]["exists"] is True
    assert "parser" in payload


def test_parse_and_parser_runs_endpoints(tmp_path: Path) -> None:
    source_dir = create_source_paper(tmp_path / "incoming", title="API Parse Sample", with_pdf=False)

    with isolated_client(tmp_path) as test_client:
        ingest = test_client.post(
            "/api/papers/ingest",
            json={
                "source": str(source_dir),
                "domain": "Speech",
                "area": "Voice-Synthesis",
                "topic": "Singing-Voice-Synthesis",
            },
        )
        paper_id = ingest.json()["data"]["paper_id"]
        parse_response = test_client.post(
            f"/api/papers/{paper_id}/parse-pdf",
            json={"force": True, "parser": "pymupdf"},
        )
        runs_response = test_client.get(f"/api/papers/{paper_id}/parser-runs")

    assert parse_response.status_code == 200
    assert parse_response.json()["data"]["status"] == "needs-pdf"
    assert runs_response.status_code == 200
    assert runs_response.json()["data"]["total"] == 1


def test_mark_and_reject_endpoints(tmp_path: Path) -> None:
    source_dir = create_source_paper(tmp_path / "incoming", title="API Mark Sample")

    with isolated_client(tmp_path) as test_client:
        ingest = test_client.post(
            "/api/papers/ingest",
            json={
                "source": str(source_dir),
                "domain": "Speech",
                "area": "Voice-Synthesis",
                "topic": "Singing-Voice-Synthesis",
            },
        )
        paper_id = ingest.json()["data"]["paper_id"]
        review = test_client.post(f"/api/papers/{paper_id}/mark-review")
        processed = test_client.post(f"/api/papers/{paper_id}/mark-processed")
        rejected = test_client.post(f"/api/papers/{paper_id}/reject")

    assert review.json()["data"]["status"] == "needs-review"
    assert processed.json()["data"]["status"] == "processed"
    assert rejected.json()["data"]["status"] == "rejected"
    assert not Path(rejected.json()["data"]["path"]).exists()


def test_candidate_decision_endpoint(tmp_path: Path) -> None:
    with isolated_client(tmp_path) as test_client:
        batch_dir = tmp_path / "data" / "Discover" / "search_batches" / "batch-a"
        batch_dir.mkdir(parents=True, exist_ok=True)
        artifact_dir = tmp_path / "data" / "Discover" / "landing" / "candidate-a"
        artifact_dir.mkdir(parents=True, exist_ok=True)
        (artifact_dir / "paper.pdf").write_text("pdf\n", encoding="utf-8")
        (batch_dir / "candidates.json").write_text(
            '{\n'
            '  "candidates": [\n'
            '    {"id": "P001", "title": "Candidate", "year": 2026, "venue": "AAAI", "result_path": "Discover/landing/candidate-a"},\n'
            '    {"id": "P002", "title": "Candidate B"}\n'
            "  ]\n"
            "}\n",
            encoding="utf-8",
        )
        keep_response = test_client.post(
            "/api/discover/batches/batch-a/candidates/P001/decision",
            json={"decision": "keep"},
        )
        reject_response = test_client.post(
            "/api/discover/batches/batch-a/candidates/P002/decision",
            json={"decision": "reject"},
        )

    assert keep_response.status_code == 200
    assert keep_response.json()["data"]["decision"] == "keep"
    assert reject_response.status_code == 200
    assert reject_response.json()["data"]["decision"] == "reject"
    assert not artifact_dir.exists()
    assert not batch_dir.exists()


def test_batch_deleted_after_last_pending_candidate_is_resolved(tmp_path: Path) -> None:
    with isolated_client(tmp_path) as test_client:
        batch_dir = tmp_path / "data" / "Discover" / "search_batches" / "batch-finished"
        batch_dir.mkdir(parents=True, exist_ok=True)
        (batch_dir / "search.md").write_text("# search\n", encoding="utf-8")
        (batch_dir / "candidates.json").write_text(
            '{\n'
            '  "candidates": [\n'
            '    {"id": "P001", "title": "Candidate A"},\n'
            '    {"id": "P002", "title": "Candidate B", "gate1_decision": "reject"}\n'
            "  ]\n"
            "}\n",
            encoding="utf-8",
        )
        response = test_client.post(
            "/api/discover/batches/batch-finished/candidates/P001/decision",
            json={"decision": "keep"},
        )

    assert response.status_code == 200
    assert response.json()["data"]["decision"] == "keep"
    assert batch_dir.exists() is False
