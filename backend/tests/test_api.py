from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from fastapi.testclient import TestClient

from backend.app.library import PaperLibrary, slugify, write_text, write_yaml
from backend.app.main import app
from backend.core.services.papers.parser import PdfParserResult


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
        paper_dir = Path(ingest.json()["data"]["path"])
        parsed_dir = paper_dir / "parsed"
        parsed_dir.mkdir(parents=True, exist_ok=True)
        write_text(paper_dir / "refined.md", "# Refined\n")
        write_text(parsed_dir / "text.md", "# Parsed\n")
        write_text(parsed_dir / "sections.json", "{}\n")
        app.state.library.repository.update_paper_state(
            paper_dir,
            {
                "parser_status": "parsed",
                "refined_review_status": "approved",
                "note_status": "missing",
                "note_review_status": "missing",
            },
        )
        response = test_client.post(f"/api/papers/{paper_id}/generate-note", json={"overwrite": False})

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["note_path"]
    assert Path(payload["note_path"]).exists()
    assert payload["note_review_status"] == "pending"


def test_import_title_only_refresh_metadata_and_content_endpoints(tmp_path: Path) -> None:
    with isolated_client(tmp_path) as test_client:
        response = test_client.post(
            "/api/papers/import",
            json={
                "title": "LoRA: Low-Rank Adaptation of Large Language Models",
                "authors": ["Edward Hu"],
                "url": "https://arxiv.org/abs/2106.09685",
                "refresh_metadata": True,
            },
        )
        payload = response.json()["data"]
        paper_id = payload["paper_id"]
        content = test_client.get(f"/api/papers/{paper_id}/content")
        sources = test_client.get(f"/api/papers/{paper_id}/metadata/sources")

    assert response.status_code == 200
    assert payload["title"] == "LoRA: Low-Rank Adaptation of Large Language Models"
    assert payload["asset_status"] == "missing_pdf"
    assert payload["stage"] == "library"
    assert payload["review_status"] == "accepted"
    assert payload["authors"] == ["Edward Hu"]
    assert payload["arxiv_id"] == "2106.09685"
    assert Path(payload["metadata_json_path"]).exists()
    paper_dir = Path(payload["path"])
    assert (paper_dir / "metadata_sources.json").exists()
    assert (paper_dir / "metadata_refresh.jsonl").exists()
    assert content.status_code == 200
    assert content.json()["data"]["note_preview"]
    assert sources.status_code == 200
    assert sources.json()["data"]["field_provenance"]["arxiv_id"] == "local-refresh"


def test_update_metadata_star_and_research_logs_endpoints(tmp_path: Path) -> None:
    with isolated_client(tmp_path) as test_client:
        imported = test_client.post("/api/papers/import", json={"title": "Metadata API Sample"})
        paper_id = imported.json()["data"]["paper_id"]
        metadata = test_client.patch(
            f"/api/papers/{paper_id}/metadata",
            json={"abstract": "Real abstract.", "summary": "Real summary.", "tags": ["paper", "api"]},
        )
        starred = test_client.patch(f"/api/papers/{paper_id}/star", json={"starred": True})
        log = test_client.post(
            f"/api/papers/{paper_id}/research-logs",
            json={"title": "阅读记录", "bullets": ["记录真实结论"], "next_steps": ["复看实验"]},
        )
        logs = test_client.get(f"/api/papers/{paper_id}/research-logs")
        detail = test_client.get(f"/api/papers/{paper_id}")

    assert metadata.status_code == 200
    assert metadata.json()["data"]["abstract"] == "Real abstract."
    assert metadata.json()["data"]["summary"] == "Real summary."
    assert starred.status_code == 200
    assert starred.json()["data"]["starred"] is True
    assert log.status_code == 200
    assert log.json()["data"]["bullets"] == ["记录真实结论"]
    assert logs.status_code == 200
    assert logs.json()["data"]["total"] == 1
    assert detail.json()["data"]["starred"] is True


def test_search_agent_settings_and_search_batch_endpoints(tmp_path: Path) -> None:
    with isolated_client(tmp_path) as test_client:
        default_settings = test_client.get("/api/settings/search-agent")
        invalid_settings = test_client.patch("/api/settings/search-agent", json={"prompt_template": "missing placeholder"})
        settings = test_client.patch(
            "/api/settings/search-agent",
            json={
                "command_template": "codex --exec \"{keywords}\"",
                "prompt_template": "Search papers for {keywords} in {venue}",
                "max_results": 7,
                "default_source": "arxiv",
            },
        )
        batch = test_client.post(
            "/api/discover/search-batches",
            json={"keywords": "test-time scaling", "venue": "ICLR", "year_start": 2024, "year_end": 2026},
        )
        job_id = batch.json()["data"]["job"]["job_id"]
        job = test_client.get(f"/api/discover/search-jobs/{job_id}")
        discover = test_client.get("/api/dashboard/discover")

    assert default_settings.status_code == 200
    assert "{keywords}" in default_settings.json()["data"]["prompt_template"]
    assert invalid_settings.status_code == 400
    assert settings.status_code == 200
    assert settings.json()["data"]["max_results"] == 7
    assert batch.status_code == 200
    batch_data = batch.json()["data"]
    assert batch_data["batch"]["candidate_total"] == 1
    assert batch_data["candidates"][0]["title"] == "test-time scaling"
    assert Path(batch_data["batch"]["path"], "candidates.json").exists()
    assert job.status_code == 200
    assert "test-time scaling" in job.json()["data"]["rendered_prompt"]
    assert discover.json()["data"]["summary"]["batch_total"] == 1


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
    assert payload["status"] == "parse-pending"
    assert payload["asset_status"] == "pdf_ready"
    assert payload["review_status"] == "pending"
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
            json={"force": True, "parser": "mineru"},
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


def test_update_classification_endpoint_moves_library_paper(tmp_path: Path) -> None:
    with isolated_client(tmp_path) as test_client:
        paper_dir = tmp_path / "data" / "Library" / "unclassified" / "classify-api-sample"
        paper_dir.mkdir(parents=True, exist_ok=True)
        write_sample_pdf(paper_dir / "paper.pdf")
        write_text(paper_dir / "note.md", "---\ntitle: Classify API Sample\n---\n")
        write_yaml(
            paper_dir / "metadata.yaml",
            {
                "title": "Classify API Sample",
                "asset_status": "pdf_ready",
                "parser_status": "parsed",
                "review_status": "accepted",
                "note_status": "template",
            },
        )
        app.state.library.repository.update_paper_state(paper_dir, {})
        record = app.state.library.get_paper("Library__unclassified__classify-api-sample")
        assert record is not None

        response = test_client.patch(
            f"/api/papers/{record.paper_id}/classification",
            json={
                "domain": "Speech",
                "area": "Voice-Synthesis",
                "topic": "Singing-Voice-Synthesis",
            },
        )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["domain"] == "Speech"
    assert payload["area"] == "Voice-Synthesis"
    assert payload["topic"] == "Singing-Voice-Synthesis"
    assert payload["paper_id"].endswith("Speech__Voice-Synthesis__Singing-Voice-Synthesis__classify-api-sample")
    assert Path(payload["path"]).exists()
    assert not paper_dir.exists()

    with isolated_client(tmp_path) as test_client:
        clear_response = test_client.patch(
            f"/api/papers/{payload['paper_id']}/classification",
            json={"domain": "", "area": "", "topic": ""},
        )

    assert clear_response.status_code == 200
    cleared = clear_response.json()["data"]
    assert cleared["domain"] == ""
    assert cleared["area"] == ""
    assert cleared["topic"] == ""
    assert cleared["paper_id"].endswith("01_Papers__unclassified__classify-api-sample")


def test_review_endpoints_and_events(tmp_path: Path) -> None:
    with isolated_client(tmp_path) as test_client:
        paper_dir = tmp_path / "data" / "Library" / "Speech" / "TTS" / "review-api-sample"
        paper_dir.mkdir(parents=True, exist_ok=True)
        write_sample_pdf(paper_dir / "paper.pdf")
        write_text(paper_dir / "refined.md", "# Refined\n")
        write_yaml(
            paper_dir / "metadata.yaml",
            {
                "title": "Review API Sample",
                "domain": "Speech",
                "area": "TTS",
                "topic": "Control",
                "asset_status": "pdf_ready",
                "parser_status": "parsed",
                "review_status": "accepted",
                "note_status": "missing",
                "refined_review_status": "pending",
                "classification_status": "classified",
            },
        )
        app.state.library.repository.update_paper_state(paper_dir, {})
        record = app.state.library.get_paper("Library__Speech__TTS__review-api-sample")
        assert record is not None

        refined = test_client.post(f"/api/papers/{record.paper_id}/review-refined", json={"decision": "approved"})
        generated = test_client.post(f"/api/papers/{record.paper_id}/generate-note", json={})
        note = test_client.post(f"/api/papers/{record.paper_id}/review-note", json={"decision": "approved"})
        events = test_client.get(f"/api/papers/{record.paper_id}/events")
        invalid = test_client.post(f"/api/papers/{record.paper_id}/review-note", json={"decision": "maybe"})
        missing = test_client.post("/api/papers/missing-paper/review-refined", json={"decision": "approved"})

    assert refined.status_code == 200
    assert refined.json()["data"]["capabilities"]["generate_note"] is True
    assert generated.status_code == 200
    assert generated.json()["data"]["note_review_status"] == "pending"
    assert note.status_code == 200
    assert note.json()["data"]["workflow_status"] == "ready"
    assert events.status_code == 200
    event_names = [item["event"] for item in events.json()["data"]["items"]]
    assert "refined_review_approved" in event_names
    assert "llm_note_generated" in event_names
    assert "note_review_approved" in event_names
    assert invalid.status_code == 400
    assert missing.status_code == 404


def test_dashboard_endpoints_tolerate_invalid_note_front_matter(tmp_path: Path) -> None:
    source_dir = create_source_paper(tmp_path / "incoming", title="PALM: Predicting Actions through Language Models")
    write_text(
        source_dir / "note.md",
        "---\n"
        "title: PALM: Predicting Actions through Language Models\n"
        "year: 2024\n"
        "venue: arXiv\n"
        "---\n\n"
        "# 摘要\n",
    )

    with isolated_client(tmp_path) as test_client:
        ingest = test_client.post(
            "/api/papers/ingest",
            json={
                "source": str(source_dir),
                "domain": "Agents",
                "area": "Planning",
                "topic": "Action Prediction",
            },
        )
        assert ingest.status_code == 200

        discover = test_client.get("/api/dashboard/discover")
        papers_dashboard = test_client.get("/api/dashboard/papers")
        papers = test_client.get("/api/papers")

    assert discover.status_code == 200
    assert papers_dashboard.status_code == 200
    assert papers.status_code == 200


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


def test_candidate_batch_decision_physically_deletes_candidates(tmp_path: Path) -> None:
    with isolated_client(tmp_path) as test_client:
        batch_dir = tmp_path / "data" / "Discover" / "search_batches" / "batch-delete"
        batch_dir.mkdir(parents=True, exist_ok=True)
        artifact_a = batch_dir / "results" / "candidate-a"
        artifact_b = batch_dir / "results" / "candidate-b"
        artifact_a.mkdir(parents=True, exist_ok=True)
        artifact_b.mkdir(parents=True, exist_ok=True)
        write_text(artifact_a / "metadata.json", '{"title": "A"}\n')
        write_text(artifact_b / "metadata.json", '{"title": "B"}\n')
        write_text(
            batch_dir / "candidates.json",
            '{\n'
            '  "candidates": [\n'
            '    {"id": "A", "title": "A", "result_path": "Discover/search_batches/batch-delete/results/candidate-a"},\n'
            '    {"id": "B", "title": "B", "result_path": "Discover/search_batches/batch-delete/results/candidate-b"}\n'
            "  ]\n"
            "}\n",
        )
        response = test_client.post(
            "/api/discover/batches/batch-delete/candidates/batch-decision",
            json={"decision": "reject", "candidate_ids": ["A", "B"]},
        )

    assert response.status_code == 200
    assert response.json()["data"]["total"] == 2
    assert not artifact_a.exists()
    assert not artifact_b.exists()
    assert not batch_dir.exists()


def test_keep_parse_accept_flow_moves_candidate_into_library(tmp_path: Path, monkeypatch) -> None:
    with isolated_client(tmp_path) as test_client:
        batch_dir = tmp_path / "data" / "Discover" / "search_batches" / "batch-flow"
        batch_dir.mkdir(parents=True, exist_ok=True)
        candidate_dir = batch_dir / "results" / "candidate-flow"
        candidate_dir.mkdir(parents=True, exist_ok=True)
        write_sample_pdf(candidate_dir / "paper.pdf")
        write_text(candidate_dir / "note.md", "---\ntitle: Flow Candidate\n---\n")
        write_yaml(
            candidate_dir / "metadata.yaml",
            {
                "title": "Flow Candidate",
                "year": 2026,
                "venue": "ICLR 2026",
                "domain": "Speech",
                "area": "Voice-Synthesis",
                "topic": "Singing-Voice-Synthesis",
            },
        )
        write_text(
            batch_dir / "candidates.json",
            '{\n'
            '  "candidates": [\n'
            '    {\n'
            '      "id": "P001",\n'
            '      "title": "Flow Candidate",\n'
            '      "year": 2026,\n'
            '      "venue": "ICLR 2026",\n'
            '      "domain": "Speech",\n'
            '      "area": "Voice-Synthesis",\n'
            '      "topic": "Singing-Voice-Synthesis",\n'
            '      "result_path": "Discover/search_batches/batch-flow/results/candidate-flow"\n'
            "    }\n"
            "  ]\n"
            "}\n",
        )

        keep_response = test_client.post(
            "/api/discover/batches/batch-flow/candidates/P001/decision",
            json={"decision": "keep"},
        )

        assert keep_response.status_code == 200
        assert keep_response.json()["data"]["decision"] == "keep"

        papers_payload = test_client.get("/api/dashboard/papers")
        assert papers_payload.status_code == 200
        library_data = papers_payload.json()["data"]
        library_papers = library_data["papers"]
        assert library_data["paths"]["library_root"].endswith("01_Papers")
        assert len(library_papers) == 1
        paper_id = library_papers[0]["paper_id"]
        library_path = Path(library_papers[0]["path"])
        assert library_papers[0]["stage"] == "library"
        assert library_papers[0]["review_status"] == "accepted"
        assert library_path.exists()

        paper_dir = Path(app.state.library.repository.get_paper_dir(paper_id) or "")
        parsed_dir = paper_dir / "parsed"
        parsed_dir.mkdir(parents=True, exist_ok=True)
        write_text(paper_dir / "refined.md", "# Parsed\n")
        write_text(parsed_dir / "text.md", "# Parsed\n")
        write_text(parsed_dir / "sections.json", "{}\n")

        def fake_parse_pdf(*args, **kwargs) -> PdfParserResult:  # noqa: ANN002, ANN003
            del args, kwargs
            return PdfParserResult(
                status="processed",
                parser="mineru",
                refined_path=str(paper_dir / "refined.md"),
                image_dir=str(paper_dir / "images"),
                text_path=str(parsed_dir / "text.md"),
                sections_path=str(parsed_dir / "sections.json"),
                error="",
            )

        monkeypatch.setattr("backend.core.services.papers.service.parse_pdf", fake_parse_pdf)

        parse_response = test_client.post(
            f"/api/papers/{paper_id}/parse-pdf",
            json={"force": True, "parser": "mineru"},
        )
        assert parse_response.status_code == 200
        parsed_paper = parse_response.json()["data"]
        assert parsed_paper["parser_status"] == "parsed"
        assert parsed_paper["error"] == ""

        papers_payload = test_client.get("/api/dashboard/papers")
        assert papers_payload.status_code == 200
        library_papers = papers_payload.json()["data"]["papers"]
        assert any(paper["paper_id"] == paper_id for paper in library_papers)


def test_candidate_decision_handles_note_and_landing_paths_without_result_path(tmp_path: Path) -> None:
    with isolated_client(tmp_path) as test_client:
        batch_dir = tmp_path / "data" / "Discover" / "search_batches" / "batch-b"
        batch_dir.mkdir(parents=True, exist_ok=True)
        artifact_dir = tmp_path / "data" / "02_Inbox" / "01_Search" / "batch-b" / "results" / "candidate-b"
        artifact_dir.mkdir(parents=True, exist_ok=True)
        write_text(artifact_dir / "note.md", "---\ntitle: Candidate B\n---\n")
        write_text(artifact_dir / "metadata.json", '{\n  "title": "Candidate B"\n}\n')
        write_text(artifact_dir / "pdf_analysis.json", '{\n  "ok": true\n}\n')
        (artifact_dir / "paper.pdf").write_text("pdf\n", encoding="utf-8")
        (batch_dir / "candidates.json").write_text(
            '{\n'
            '  "candidates": [\n'
            '    {\n'
            '      "id": "P010",\n'
            '      "title": "Candidate B",\n'
            '      "year": 2026,\n'
            '      "venue": "AAAI",\n'
            '      "note_path": "02_Inbox/01_Search/batch-b/results/candidate-b/note.md",\n'
            '      "metadata_path": "02_Inbox/01_Search/batch-b/results/candidate-b/metadata.json",\n'
            '      "pdf_analysis_path": "02_Inbox/01_Search/batch-b/results/candidate-b/pdf_analysis.json",\n'
            '      "landing_path": "02_Inbox/01_Search/batch-b/results/candidate-b/paper.pdf"\n'
            '    }\n'
            "  ]\n"
            "}\n",
            encoding="utf-8",
        )
        keep_response = test_client.post(
            "/api/discover/batches/batch-b/candidates/P010/decision",
            json={"decision": "keep"},
        )

    assert keep_response.status_code == 200
    assert keep_response.json()["data"]["decision"] == "keep"
    assert not artifact_dir.exists()
    promoted = tmp_path / "data" / "01_Papers" / "unclassified" / "candidate-b"
    assert promoted.exists()
    assert (promoted / "paper.pdf").exists()
    assert (promoted / "note.md").exists()


def test_candidate_reject_removes_artifact_dir_without_result_path(tmp_path: Path) -> None:
    with isolated_client(tmp_path) as test_client:
        batch_dir = tmp_path / "data" / "Discover" / "search_batches" / "batch-c"
        batch_dir.mkdir(parents=True, exist_ok=True)
        artifact_dir = tmp_path / "data" / "02_Inbox" / "01_Search" / "batch-c" / "results" / "candidate-c"
        artifact_dir.mkdir(parents=True, exist_ok=True)
        write_text(artifact_dir / "note.md", "---\ntitle: Candidate C\n---\n")
        write_text(artifact_dir / "metadata.json", '{\n  "title": "Candidate C"\n}\n')
        (artifact_dir / "paper.pdf").write_text("pdf\n", encoding="utf-8")
        (batch_dir / "candidates.json").write_text(
            '{\n'
            '  "candidates": [\n'
            '    {\n'
            '      "id": "P011",\n'
            '      "title": "Candidate C",\n'
            '      "note_path": "02_Inbox/01_Search/batch-c/results/candidate-c/note.md",\n'
            '      "metadata_path": "02_Inbox/01_Search/batch-c/results/candidate-c/metadata.json",\n'
            '      "landing_path": "02_Inbox/01_Search/batch-c/results/candidate-c/paper.pdf"\n'
            '    }\n'
            "  ]\n"
            "}\n",
            encoding="utf-8",
        )
        reject_response = test_client.post(
            "/api/discover/batches/batch-c/candidates/P011/decision",
            json={"decision": "reject"},
        )

    assert reject_response.status_code == 200
    assert reject_response.json()["data"]["decision"] == "reject"
    assert not artifact_dir.exists()


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


def test_create_library_folder_endpoint(tmp_path: Path) -> None:
    with isolated_client(tmp_path) as test_client:
        response = test_client.post(
            "/api/papers/library-folders",
            json={"path": "Computer-Vision/Video-Understanding/New-Topic"},
        )
        outside_response = test_client.post(
            "/api/papers/library-folders",
            json={"path": "../outside"},
        )
        dashboard_response = test_client.get("/api/dashboard/papers")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["relative_path"] == "Computer-Vision/Video-Understanding/New-Topic"
    assert Path(data["path"]).exists()
    assert outside_response.status_code == 400
    assert dashboard_response.status_code == 200
    assert "Computer-Vision/Video-Understanding/New-Topic" in dashboard_response.json()["data"]["folders"]
