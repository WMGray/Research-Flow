from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.api.paper_download import get_paper_download_service
from app.main import app
from core.config import reset_settings
from core.services.llm import llm_registry
from core.services.llm.schemas import LLMMessage, LLMRequest, LLMResponse


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[TestClient]:
    monkeypatch.setenv("RESEARCH_FLOW_ENV_FILE", "none")
    monkeypatch.setenv("RFLOW_DB_PATH", str(tmp_path / "research_flow.sqlite"))
    monkeypatch.setenv("RFLOW_STORAGE_DIR", str(tmp_path / "storage"))
    reset_settings()
    with TestClient(app) as test_client:
        try:
            yield test_client
        finally:
            reset_settings()
            app.dependency_overrides.clear()


@dataclass(frozen=True)
class FakeResolveRow:
    index: int
    raw_input: str
    title: str
    year: str
    venue: str
    doi: str
    resolve_method: str
    source: str
    status: str
    pdf_url: str
    landing_url: str
    final_url: str
    http_status: str
    content_type: str
    detail: str
    error_code: str
    metadata_source: str
    metadata_confidence: str
    suggested_filename: str
    target_path: str
    probe_trace: list[str]


class FakePaperDownloadService:
    def resolve(self, request):
        del request
        return FakeResolveRow(
            index=1,
            raw_input="test",
            title="Test Paper",
            year="2024",
            venue="CVPR",
            doi="10.1234/test",
            resolve_method="direct",
            source="semantic_scholar",
            status="ready_download",
            pdf_url="https://example.com/paper.pdf",
            landing_url="https://example.com/landing",
            final_url="https://example.com/final.pdf",
            http_status="200",
            content_type="application/pdf",
            detail="",
            error_code="",
            metadata_source="semantic_scholar_doi",
            metadata_confidence="high",
            suggested_filename="Test Paper__2024.pdf",
            target_path="C:/tmp/Test Paper__2024.pdf",
            probe_trace=["step-1"],
        )


def install_fake_refiner(
    monkeypatch: pytest.MonkeyPatch,
    *,
    response_content: str,
) -> list[LLMRequest]:
    requests: list[LLMRequest] = []

    async def fake_generate(request: LLMRequest) -> LLMResponse:
        requests.append(request)
        source_lines = _extract_line_numbered_markdown(request.messages[0].content)
        if request.feature == "paper_refine_parse_diagnose":
            content = json.dumps(
                {
                    "source_hash": "",
                    "issues": [
                        {
                            "issue_id": "issue_001",
                            "type": "heading_ambiguous",
                            "start_line": 1,
                            "end_line": max(len(source_lines), 1),
                            "severity": "medium",
                            "confidence": 0.95,
                            "description": "Fake test issue.",
                            "suggested_action": "replace_span",
                            "needs_pdf_context": False,
                        }
                    ],
                }
            )
        elif request.feature == "paper_refine_parse_repair":
            preserved_metadata = "\n".join(source_lines[:6])
            replacement = "\n\n".join(
                part
                for part in [
                    response_content.strip(),
                    "<!-- preserved MinerU metadata -->\n" + preserved_metadata,
                ]
                if part.strip()
            )
            content = json.dumps(
                {
                    "source_hash": "",
                    "patches": [
                        {
                            "patch_id": "patch_001",
                            "issue_id": "issue_001",
                            "op": "replace_span",
                            "start_line": 1,
                            "end_line": max(len(source_lines), 1),
                            "replacement": replacement,
                            "confidence": 0.95,
                            "rationale": "Fake test repair.",
                        }
                    ],
                }
            )
        elif request.feature == "paper_note_generate_block":
            prompt = request.messages[0].content
            if "当前只生成 note.md" in prompt:
                content = json.dumps({"content": "What problem the paper addresses."})
            else:
                content = json.dumps(
                    {
                        "blocks": {
                            "research_question": "What problem the paper addresses.",
                            "core_method": "The core method described by the parsed sections.",
                            "main_contributions": "The paper contributions.",
                            "experiment_summary": "The experiment summary.",
                            "limitations": "The limitations.",
                        }
                    }
                )
        else:
            content = json.dumps(
                {
                    "source_hash": "",
                    "status": "pass",
                    "summary": "Fake verifier passed.",
                    "blocking_issues": [],
                    "review_items": [],
                }
            )
        return LLMResponse(
            feature=request.feature or "",
            model_key="fake_markdown_refiner",
            platform="fake",
            provider="fake",
            model="fake-model",
            message=LLMMessage(role="assistant", content=content),
        )

    monkeypatch.setattr(llm_registry, "generate", fake_generate)
    return requests


def _extract_line_numbered_markdown(prompt: str) -> list[str]:
    lines: list[str] = []
    for line in prompt.splitlines():
        if len(line) > 7 and line[:5].isdigit() and line[5:7] == ": ":
            lines.append(line[7:])
    return lines


def create_sample_paper(client: TestClient, **overrides: object) -> dict:
    payload = {
        "title": "LoRA: Low-Rank Adaptation of Large Language Models",
        "authors": ["Edward J. Hu", "Yelong Shen"],
        "year": 2021,
        "venue": "arXiv",
        "venue_short": "arXiv",
        "doi": "10.48550/arXiv.2106.09685",
        "source_url": "https://arxiv.org/abs/2106.09685",
        "pdf_url": "https://arxiv.org/pdf/2106.09685",
        "category_id": 10,
        "tags": ["LLM", "PEFT"],
    }
    payload.update(overrides)
    response = client.post("/api/v1/papers", json=payload)
    assert response.status_code == 201
    return response.json()["data"]


def test_paper_crud_flow(client: TestClient) -> None:
    paper = create_sample_paper(client)
    paper_id = paper["paper_id"]

    assert paper["paper_stage"] == "metadata_ready"
    assert paper["note_status"] == "empty"
    assert paper["source_url"] == "https://arxiv.org/abs/2106.09685"

    detail_response = client.get(f"/api/v1/papers/{paper_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["data"]["title"].startswith("LoRA")

    list_response = client.get(
        "/api/v1/papers",
        params={"q": "LoRA", "paper_stage": "metadata_ready"},
    )
    assert list_response.status_code == 200
    assert list_response.json()["meta"]["total"] == 1

    update_response = client.patch(
        f"/api/v1/papers/{paper_id}",
        json={
            "venue": "ICLR",
            "tags": ["LLM", "Adapter"],
            "source_url": "https://example.com/lora",
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["data"]["venue"] == "ICLR"
    assert update_response.json()["data"]["tags"] == ["LLM", "Adapter"]

    delete_response = client.delete(f"/api/v1/papers/{paper_id}")
    assert delete_response.status_code == 204

    missing_response = client.get(f"/api/v1/papers/{paper_id}")
    assert missing_response.status_code == 404


def test_paper_rejects_legacy_url_input(client: TestClient) -> None:
    response = client.post(
        "/api/v1/papers",
        json={"title": "Legacy URL Paper", "url": "https://example.com/legacy"},
    )
    assert response.status_code == 422


def test_paper_uses_single_note_and_refined_documents(
    client: TestClient,
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "research_flow.sqlite"
    paper = create_sample_paper(client)
    paper_id = paper["paper_id"]

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        paper_asset = conn.execute(
            """
            SELECT ar.*, bp.title
            FROM asset_registry ar
            JOIN biz_paper bp ON bp.asset_id = ar.asset_id
            WHERE ar.asset_id = ?
            """,
            (paper_id,),
        ).fetchone()
        doc_rows = conn.execute(
            """
            SELECT bdl.*, ar.asset_type
            FROM biz_doc_layout bdl
            JOIN asset_registry ar ON ar.asset_id = bdl.doc_id
            WHERE bdl.parent_id = ?
            ORDER BY bdl.doc_role
            """,
            (paper_id,),
        ).fetchall()
        link_count = conn.execute(
            "SELECT COUNT(*) FROM asset_link WHERE source_id = ? AND relation_type = 'CONTAINS'",
            (paper_id,),
        ).fetchone()[0]
        physical_count = conn.execute("SELECT COUNT(*) FROM physical_item").fetchone()[0]

    assert paper_asset["asset_type"] == "Paper"
    assert [row["doc_role"] for row in doc_rows] == ["note", "refined"]
    assert all(row["asset_type"] == "Markdown" for row in doc_rows)
    assert link_count == 2
    assert physical_count == 3


def test_paper_create_rejects_duplicate_doi(client: TestClient) -> None:
    create_sample_paper(client)
    duplicate_response = client.post(
        "/api/v1/papers",
        json={"title": "Duplicate LoRA", "doi": "10.48550/arXiv.2106.09685"},
    )
    assert duplicate_response.status_code == 409
    assert duplicate_response.json()["detail"]["code"] == "PAPER_DUPLICATE"


def test_paper_note_updates_mark_user_modified(client: TestClient) -> None:
    paper = create_sample_paper(client)
    paper_id = paper["paper_id"]

    get_response = client.get(f"/api/v1/papers/{paper_id}/note")
    assert get_response.status_code == 200
    note = get_response.json()["data"]
    assert note["doc_role"] == "note"

    update_response = client.put(
        f"/api/v1/papers/{paper_id}/note",
        json={"content": "# Note\n\nUpdated summary.", "base_version": note["version"]},
    )
    assert update_response.status_code == 200
    updated = update_response.json()["data"]
    assert updated["version"] == 2
    assert "Updated summary." in updated["content"]

    paper_response = client.get(f"/api/v1/papers/{paper_id}")
    assert paper_response.status_code == 200
    assert paper_response.json()["data"]["note_status"] == "user_modified"


def test_refined_document_supports_versioning(client: TestClient) -> None:
    paper = create_sample_paper(client)
    paper_id = paper["paper_id"]

    get_response = client.get(f"/api/v1/papers/{paper_id}/parsed/refined")
    assert get_response.status_code == 200
    refined = get_response.json()["data"]
    assert refined["doc_role"] == "refined"

    update_response = client.put(
        f"/api/v1/papers/{paper_id}/parsed/refined",
        json={"content": "# Refined\n\nManual review.", "base_version": refined["version"]},
    )
    assert update_response.status_code == 200
    updated = update_response.json()["data"]
    assert updated["version"] == 2

    conflict_response = client.put(
        f"/api/v1/papers/{paper_id}/parsed/refined",
        json={"content": "stale", "base_version": refined["version"]},
    )
    assert conflict_response.status_code == 409
    assert conflict_response.json()["detail"]["code"] == "DOCUMENT_VERSION_CONFLICT"


def test_download_parse_and_sections_flow(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    paper = create_sample_paper(client)
    paper_id = paper["paper_id"]

    download_response = client.post(f"/api/v1/papers/{paper_id}/download")
    assert download_response.status_code == 202
    assert download_response.json()["data"]["status"] == "succeeded"

    parse_response = client.post(f"/api/v1/papers/{paper_id}/parse", json={})
    assert parse_response.status_code == 202
    job = parse_response.json()["data"]
    assert job["type"] == "paper_parse"
    assert job["status"] == "succeeded"

    paper_response = client.get(f"/api/v1/papers/{paper_id}")
    payload = paper_response.json()["data"]
    assert payload["paper_stage"] == "parsed"
    assert payload["download_status"] == "succeeded"
    assert payload["parse_status"] == "succeeded"
    assert payload["refine_status"] == "pending"

    install_fake_refiner(
        monkeypatch,
        response_content="\n".join(
            [
                "# Refined",
                "",
                "## Related Work",
                "Related work section.",
                "",
                "## Method",
                "Method section.",
                "",
                "## Experiment",
                "Experiment section.",
                "",
                "## Conclusion",
                "Conclusion section.",
            ]
        ),
    )
    refine_response = client.post(f"/api/v1/papers/{paper_id}/refine-parse", json={})
    assert refine_response.status_code == 202
    assert refine_response.json()["data"]["status"] == "succeeded"

    split_response = client.post(f"/api/v1/papers/{paper_id}/split-sections")
    assert split_response.status_code == 202
    assert split_response.json()["data"]["status"] == "succeeded"

    parsed_response = client.get(f"/api/v1/papers/{paper_id}/parsed")
    assert parsed_response.status_code == 200
    assert parsed_response.json()["data"]["char_count"] > 0

    sections_response = client.get(f"/api/v1/papers/{paper_id}/parsed/sections")
    assert sections_response.status_code == 200
    section_keys = [item["section_key"] for item in sections_response.json()["data"]]
    assert section_keys == [
        "introduction",
        "related_work",
        "method",
        "experiment",
        "conclusion",
        "appendix",
    ]

    with sqlite3.connect(tmp_path / "research_flow.sqlite") as conn:
        artifact_keys = {
            row[0]
            for row in conn.execute(
                """
                SELECT artifact_key
                FROM biz_paper_artifact
                WHERE paper_id = ?
                """,
                (paper_id,),
            )
        }
        run_stages = [
            row[0]
            for row in conn.execute(
                """
                SELECT stage
                FROM biz_paper_pipeline_run
                WHERE paper_id = ?
                ORDER BY created_at
                """,
                (paper_id,),
            )
        ]

    assert {"source_pdf", "raw_markdown", "refined_markdown", "section_method"} <= artifact_keys
    assert {"download", "parse", "refine", "split"} <= set(run_stages)


def test_parse_uses_postprocessed_figures_for_refined_markdown(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    paper = create_sample_paper(client)
    paper_id = paper["paper_id"]
    db_path = tmp_path / "research_flow.sqlite"

    with sqlite3.connect(db_path) as conn:
        paper_dir = Path(
            conn.execute(
                """
                SELECT pi.storage_path
                FROM asset_registry ar
                JOIN physical_item pi ON pi.item_id = ar.item_id
                WHERE ar.asset_id = ?
                """,
                (paper_id,),
            ).fetchone()[0]
        )
    mineru_dir = paper_dir / "parsed" / "mineru"
    mineru_image_dir = mineru_dir / "images"
    mineru_image_dir.mkdir(parents=True)
    (mineru_dir / "full.md").write_text(
        "\n".join(
            [
                "# Visual Paper",
                "",
                "## 4 Method",
                "Method context line one.",
                "Method context line two.",
                "Method context line three.",
                "![](images/fig1.jpg)",
                "Figure 1: Method overview.",
            ]
        ),
        encoding="utf-8",
    )
    Image.new("RGB", (120, 80), (20, 120, 220)).save(mineru_image_dir / "fig1.jpg")
    (mineru_dir / "content_list_v2.json").write_text(
        json.dumps(
            [
                [
                    {
                        "type": "image",
                        "bbox": [10, 20, 130, 100],
                        "content": {
                            "image_source": {"path": "images/fig1.jpg"},
                            "image_caption": [
                                {"type": "text", "content": "Figure 1: Method overview."}
                            ],
                            "image_footnote": [],
                        },
                    }
                ]
            ]
        ),
        encoding="utf-8",
    )

    parse_response = client.post(f"/api/v1/papers/{paper_id}/parse", json={})

    assert parse_response.status_code == 202
    assert parse_response.json()["data"]["status"] == "succeeded"
    parse_job = parse_response.json()["data"]
    assert (paper_dir / "parsed" / "images" / "figure_1.png").exists()
    assert parse_job["result"]["artifacts"]["postprocessed_figure_count"] == "1"
    assert "![](images/figure_1.png)" in (
        paper_dir / "parsed" / "raw.md"
    ).read_text(encoding="utf-8")

    with sqlite3.connect(db_path) as conn:
        artifact_keys = {
            row[0]
            for row in conn.execute(
                """
                SELECT artifact_key
                FROM biz_paper_artifact
                WHERE paper_id = ?
                """,
                (paper_id,),
            )
        }
        parse_metrics = json.loads(
            conn.execute(
                """
                SELECT metrics
                FROM biz_paper_pipeline_run
                WHERE paper_id = ? AND stage = 'parse'
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (paper_id,),
            ).fetchone()[0]
        )
    assert "parse_figures" in artifact_keys
    assert parse_metrics["figure_count"] == 1

    install_fake_refiner(
        monkeypatch,
        response_content="\n".join(
            [
                "# Refined",
                "",
                "## Method",
                "![](images/figure_1.png)",
                "Figure 1: Method overview.",
                "",
                "## Experiment",
                "Experiment section.",
                "",
                "## Conclusion",
                "Conclusion section.",
            ]
        ),
    )
    refine_response = client.post(f"/api/v1/papers/{paper_id}/refine-parse", json={})

    assert refine_response.status_code == 202
    assert refine_response.json()["data"]["status"] == "succeeded"
    refined_text = (paper_dir / "parsed" / "refined.md").read_text(encoding="utf-8")
    assert "![](images/figure_1.png)" in refined_text
    assert (paper_dir / "parsed" / "images" / "figure_1.png").exists()


def test_review_and_note_generation_flow(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    paper = create_sample_paper(client)
    paper_id = paper["paper_id"]
    client.post(f"/api/v1/papers/{paper_id}/parse", json={})
    requests = install_fake_refiner(
        monkeypatch,
        response_content="\n".join(
            [
                "# Refined",
                "",
                "## Related Work",
                "Related work section.",
                "",
                "## Method",
                "Method section.",
                "",
                "## Experiment",
                "Experiment section.",
                "",
                "## Conclusion",
                "Conclusion section.",
            ]
        ),
    )
    refine_response = client.post(
        f"/api/v1/papers/{paper_id}/refine-parse",
        json={"instruction": "Prefer clean canonical section titles."},
    )
    assert refine_response.status_code == 202
    assert refine_response.json()["data"]["result"]["skill_key"] == "paper_refine_parse"
    assert refine_response.json()["data"]["result"]["llm_run_id"].startswith("llm_")
    assert "Prefer clean canonical section titles." in requests[0].messages[0].content

    submit_response = client.post(f"/api/v1/papers/{paper_id}/submit-review")
    assert submit_response.status_code == 200
    assert submit_response.json()["data"]["review_status"] == "waiting_review"

    confirm_response = client.post(f"/api/v1/papers/{paper_id}/confirm-review")
    assert confirm_response.status_code == 200
    assert confirm_response.json()["data"]["paper_stage"] == "review_confirmed"

    split_response = client.post(f"/api/v1/papers/{paper_id}/split-sections")
    assert split_response.status_code == 202
    assert split_response.json()["data"]["status"] == "succeeded"

    note_response = client.post(f"/api/v1/papers/{paper_id}/generate-note")
    assert note_response.status_code == 202
    assert note_response.json()["data"]["type"] == "paper_generate_note"

    paper_response = client.get(f"/api/v1/papers/{paper_id}")
    assert paper_response.json()["data"]["paper_stage"] == "noted"
    assert paper_response.json()["data"]["note_status"] == "clean_generated"

    note_document = client.get(f"/api/v1/papers/{paper_id}/note")
    assert note_document.status_code == 200
    assert 'RF:BLOCK_START id="paper_overview"' in note_document.json()["data"]["content"]
    assert "What problem the paper addresses." in note_document.json()["data"]["content"]

    with sqlite3.connect(tmp_path / "research_flow.sqlite") as conn:
        note_artifact = conn.execute(
            """
            SELECT artifact_key, stage
            FROM biz_paper_artifact
            WHERE paper_id = ? AND artifact_key = 'note_markdown'
            """,
            (paper_id,),
        ).fetchone()
        summarize_run = conn.execute(
            """
            SELECT stage, status
            FROM biz_paper_pipeline_run
            WHERE paper_id = ? AND stage = 'summarize'
            """,
            (paper_id,),
        ).fetchone()

    assert note_artifact == ("note_markdown", "summarize")
    assert summarize_run == ("summarize", "succeeded")


def test_generate_note_preserves_user_modified_note(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paper = create_sample_paper(client)
    paper_id = paper["paper_id"]
    client.post(f"/api/v1/papers/{paper_id}/parse", json={})
    install_fake_refiner(
        monkeypatch,
        response_content="\n".join(
            [
                "# Refined",
                "",
                "## Related Work",
                "Related work section.",
                "",
                "## Method",
                "Method section.",
                "",
                "## Experiment",
                "Experiment section.",
                "",
                "## Conclusion",
                "Conclusion section.",
            ]
        ),
    )
    client.post(f"/api/v1/papers/{paper_id}/refine-parse", json={})
    client.post(f"/api/v1/papers/{paper_id}/split-sections")

    note = client.get(f"/api/v1/papers/{paper_id}/note").json()["data"]
    update_response = client.put(
        f"/api/v1/papers/{paper_id}/note",
        json={
            "content": "# Manual Note\n\nManual insight stays.",
            "base_version": note["version"],
        },
    )
    assert update_response.status_code == 200

    note_response = client.post(f"/api/v1/papers/{paper_id}/generate-note")

    assert note_response.status_code == 202
    assert note_response.json()["data"]["status"] == "succeeded"
    assert note_response.json()["data"]["result"]["merge_policy"] == "merged"
    content = client.get(f"/api/v1/papers/{paper_id}/note").json()["data"]["content"]
    assert "Manual insight stays." in content
    assert 'RF:BLOCK_START id="paper_overview"' in content
    assert "What problem the paper addresses." in content
    paper_response = client.get(f"/api/v1/papers/{paper_id}")
    assert paper_response.json()["data"]["note_status"] == "merged"


def test_extract_actions_write_final_jobs(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paper = create_sample_paper(client)
    paper_id = paper["paper_id"]
    client.post(f"/api/v1/papers/{paper_id}/parse", json={})
    install_fake_refiner(
        monkeypatch,
        response_content="\n".join(
            [
                "# Refined",
                "",
                "## Related Work",
                "Related work section.",
                "",
                "## Method",
                "Method section.",
                "",
                "## Experiment",
                "Experiment section.",
                "",
                "## Conclusion",
                "Conclusion section.",
            ]
        ),
    )
    client.post(f"/api/v1/papers/{paper_id}/refine-parse", json={})
    client.post(f"/api/v1/papers/{paper_id}/split-sections")
    client.post(f"/api/v1/papers/{paper_id}/generate-note")

    knowledge_response = client.post(f"/api/v1/papers/{paper_id}/extract-knowledge")
    assert knowledge_response.status_code == 202
    assert knowledge_response.json()["data"]["status"] == "succeeded"

    datasets_response = client.post(f"/api/v1/papers/{paper_id}/extract-datasets")
    assert datasets_response.status_code == 202
    assert datasets_response.json()["data"]["status"] == "succeeded"

    paper_response = client.get(f"/api/v1/papers/{paper_id}")
    assert paper_response.json()["data"]["paper_stage"] == "completed"


def test_cancel_rejects_finished_job(client: TestClient) -> None:
    paper = create_sample_paper(client)
    parse_response = client.post(f"/api/v1/papers/{paper['paper_id']}/parse", json={})
    job_id = parse_response.json()["data"]["job_id"]

    cancel_response = client.post(f"/api/v1/jobs/{job_id}/cancel")
    assert cancel_response.status_code == 409
    assert cancel_response.json()["detail"]["code"] == "JOB_CANCEL_NOT_ALLOWED"


def test_create_paper_can_parse_after_import(client: TestClient) -> None:
    response = client.post(
        "/api/v1/papers",
        json={"title": "Queued Paper", "parse_after_import": True},
    )

    assert response.status_code == 201
    paper = response.json()["data"]
    assert paper["paper_stage"] == "parsed"
    assert paper["download_status"] == "succeeded"
    assert paper["parse_status"] == "succeeded"
    assert paper["download_job_id"].startswith("job_")
    assert paper["parse_job_id"].startswith("job_")


def test_create_paper_can_download_after_import(client: TestClient) -> None:
    response = client.post(
        "/api/v1/papers",
        json={"title": "Downloaded Paper", "download_pdf": True},
    )

    assert response.status_code == 201
    paper = response.json()["data"]
    assert paper["paper_stage"] == "downloaded"
    assert paper["download_status"] == "succeeded"
    assert paper["parse_status"] == "pending"
    assert paper["download_job_id"].startswith("job_")
    assert paper["parse_job_id"] is None


def test_run_paper_pipeline_reaches_note_and_exposes_audit_records(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paper = create_sample_paper(client)
    paper_id = paper["paper_id"]
    install_fake_refiner(
        monkeypatch,
        response_content="\n".join(
            [
                "# Refined",
                "",
                "## Related Work",
                "Related work section.",
                "",
                "## Method",
                "Method section.",
                "",
                "## Experiment",
                "Experiment section.",
                "",
                "## Conclusion",
                "Conclusion section.",
            ]
        ),
    )

    response = client.post(f"/api/v1/papers/{paper_id}/pipeline", json={})

    assert response.status_code == 202
    payload = response.json()["data"]
    assert payload["status"] == "succeeded"
    assert [job["type"] for job in payload["jobs"]] == [
        "paper_download",
        "paper_parse",
        "paper_refine_parse",
        "paper_split_sections",
        "paper_generate_note",
    ]
    assert payload["paper"]["paper_stage"] == "noted"

    artifacts_response = client.get(f"/api/v1/papers/{paper_id}/artifacts")
    assert artifacts_response.status_code == 200
    artifact_keys = {item["artifact_key"] for item in artifacts_response.json()["data"]}
    assert {"source_pdf", "raw_markdown", "refined_markdown", "note_markdown"} <= artifact_keys

    runs_response = client.get(f"/api/v1/papers/{paper_id}/pipeline-runs")
    assert runs_response.status_code == 200
    stages = [item["stage"] for item in runs_response.json()["data"]]
    assert stages[-5:] == ["download", "parse", "refine", "split", "summarize"]


def test_refine_parse_requires_raw_markdown(client: TestClient) -> None:
    paper = create_sample_paper(client)

    response = client.post(
        f"/api/v1/papers/{paper['paper_id']}/refine-parse",
        json={},
    )

    assert response.status_code == 202
    payload = response.json()["data"]
    assert payload["status"] == "failed"
    assert payload["error"]["code"] == "PAPER_RAW_MARKDOWN_MISSING"


def test_split_sections_requires_refined_markdown(client: TestClient) -> None:
    paper = create_sample_paper(client)
    client.post(f"/api/v1/papers/{paper['paper_id']}/parse", json={})

    response = client.post(f"/api/v1/papers/{paper['paper_id']}/split-sections")

    assert response.status_code == 202
    payload = response.json()["data"]
    assert payload["status"] == "failed"
    assert payload["error"]["code"] == "PAPER_REFINED_MARKDOWN_MISSING"


def test_assets_endpoint_returns_document_asset_ids(client: TestClient) -> None:
    paper = create_sample_paper(client)
    response = client.get(f"/api/v1/papers/{paper['paper_id']}/assets")
    assert response.status_code == 200
    assert set(response.json()["data"]) == {"note", "refined"}


def test_paper_resolve_endpoint_accepts_title(client: TestClient) -> None:
    app.dependency_overrides[get_paper_download_service] = lambda: (
        FakePaperDownloadService()
    )

    response = client.post("/api/v1/papers/resolve", json={"title": "Test Paper"})

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["title"] == "Test Paper"
    assert payload["status"] == "ready_download"
    assert payload["probe_trace"] == ["step-1"]


def test_paper_resolve_rejects_legacy_name_input(client: TestClient) -> None:
    app.dependency_overrides[get_paper_download_service] = lambda: (
        FakePaperDownloadService()
    )

    response = client.post("/api/v1/papers/resolve", json={"name": "Test Paper"})

    assert response.status_code == 422


def test_legacy_parsed_content_route_is_removed(client: TestClient) -> None:
    paper = create_sample_paper(client)
    response = client.get(f"/api/v1/papers/{paper['paper_id']}/parsed-content")
    assert response.status_code == 404
