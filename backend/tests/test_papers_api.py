from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[TestClient]:
    monkeypatch.setenv("RFLOW_DB_PATH", str(tmp_path / "research_flow.sqlite"))
    monkeypatch.setenv("RFLOW_STORAGE_DIR", str(tmp_path / "storage"))
    with TestClient(app) as test_client:
        yield test_client


def create_sample_paper(client: TestClient) -> dict:
    response = client.post(
        "/api/v1/papers",
        json={
            "title": "LoRA: Low-Rank Adaptation of Large Language Models",
            "authors": ["Edward J. Hu", "Yelong Shen"],
            "year": 2021,
            "venue": "arXiv",
            "venue_short": "arXiv",
            "doi": "10.48550/arXiv.2106.09685",
            "url": "https://arxiv.org/abs/2106.09685",
            "pdf_url": "https://arxiv.org/pdf/2106.09685",
            "category_id": 10,
            "tags": ["LLM", "PEFT"],
        },
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["error"] is None
    return payload["data"]


def test_paper_crud_flow(client: TestClient) -> None:
    paper = create_sample_paper(client)
    paper_id = paper["paper_id"]

    detail_response = client.get(f"/api/v1/papers/{paper_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["data"]["title"].startswith("LoRA")

    list_response = client.get("/api/v1/papers", params={"q": "LoRA"})
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload["meta"]["total"] == 1
    assert list_payload["data"][0]["paper_id"] == paper_id

    update_response = client.patch(
        f"/api/v1/papers/{paper_id}",
        json={"venue": "ICLR", "tags": ["LLM", "Adapter"]},
    )
    assert update_response.status_code == 200
    assert update_response.json()["data"]["venue"] == "ICLR"
    assert update_response.json()["data"]["tags"] == ["LLM", "Adapter"]

    delete_response = client.delete(f"/api/v1/papers/{paper_id}")
    assert delete_response.status_code == 204

    missing_response = client.get(f"/api/v1/papers/{paper_id}")
    assert missing_response.status_code == 404


def test_paper_uses_layered_table_design(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "research_flow.sqlite"
    monkeypatch.setenv("RFLOW_DB_PATH", str(db_path))
    monkeypatch.setenv("RFLOW_STORAGE_DIR", str(tmp_path / "storage"))

    with TestClient(app) as test_client:
        paper = create_sample_paper(test_client)

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
        physical_count = conn.execute("SELECT COUNT(*) FROM physical_item").fetchone()[
            0
        ]

    assert paper_asset["asset_type"] == "Paper"
    assert paper_asset["title"].startswith("LoRA")
    assert [row["doc_role"] for row in doc_rows] == ["human", "llm"]
    assert all(row["asset_type"] == "Markdown" for row in doc_rows)
    assert link_count == 2
    assert physical_count == 3


def test_paper_create_rejects_duplicate_doi(client: TestClient) -> None:
    create_sample_paper(client)
    duplicate_response = client.post(
        "/api/v1/papers",
        json={
            "title": "Duplicate LoRA",
            "doi": "10.48550/arXiv.2106.09685",
        },
    )

    assert duplicate_response.status_code == 409
    assert duplicate_response.json()["detail"]["code"] == "PAPER_DUPLICATE"


def test_paper_documents_support_versioned_human_notes(client: TestClient) -> None:
    paper = create_sample_paper(client)
    paper_id = paper["paper_id"]

    get_response = client.get(f"/api/v1/papers/{paper_id}/documents/human")
    assert get_response.status_code == 200
    document = get_response.json()["data"]
    assert document["version"] == 1
    assert "人工笔记" in document["content"]

    update_response = client.put(
        f"/api/v1/papers/{paper_id}/documents/human",
        json={"content": "# Notes\n\nReviewed.", "base_version": 1},
    )
    assert update_response.status_code == 200
    updated = update_response.json()["data"]
    assert updated["version"] == 2
    assert "Reviewed." in updated["content"]

    conflict_response = client.put(
        f"/api/v1/papers/{paper_id}/documents/human",
        json={"content": "stale", "base_version": 1},
    )
    assert conflict_response.status_code == 409
    assert conflict_response.json()["detail"]["code"] == "DOCUMENT_VERSION_CONFLICT"


def test_paper_parse_creates_queryable_job(client: TestClient) -> None:
    paper = create_sample_paper(client)
    paper_id = paper["paper_id"]

    parse_response = client.post(f"/api/v1/papers/{paper_id}/parse", json={})
    assert parse_response.status_code == 202
    job = parse_response.json()["data"]
    assert job["type"] == "paper_parse"
    assert job["status"] == "queued"

    job_response = client.get(f"/api/v1/jobs/{job['job_id']}")
    assert job_response.status_code == 200
    assert job_response.json()["data"]["resource_id"] == paper_id

    paper_response = client.get(f"/api/v1/papers/{paper_id}")
    assert paper_response.json()["data"]["status"] == "parse_queued"


def test_create_paper_can_queue_parse_after_import(client: TestClient) -> None:
    response = client.post(
        "/api/v1/papers",
        json={
            "title": "Queued Paper",
            "parse_after_import": True,
        },
    )

    assert response.status_code == 201
    paper = response.json()["data"]
    assert paper["status"] == "parse_queued"
    assert paper["parse_job_id"].startswith("job_")


def test_parsed_content_returns_llm_document_summary(client: TestClient) -> None:
    paper = create_sample_paper(client)
    paper_id = paper["paper_id"]

    response = client.get(f"/api/v1/papers/{paper_id}/parsed-content")

    assert response.status_code == 200
    parsed = response.json()["data"]
    assert parsed["paper_id"] == paper_id
    assert parsed["char_count"] > 0
    assert "LoRA" in parsed["excerpt"]
