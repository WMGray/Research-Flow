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


def create_project(client: TestClient) -> dict:
    response = client.post(
        "/api/v1/projects",
        json={
            "name": "Adaptive Literature Review",
            "summary": "Track paper-to-project synthesis.",
            "owner": "researcher",
        },
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["error"] is None
    return payload["data"]


def create_paper(client: TestClient) -> dict:
    response = client.post(
        "/api/v1/papers",
        json={
            "title": "LoRA: Low-Rank Adaptation of Large Language Models",
            "authors": ["Edward J. Hu"],
            "doi": "10.48550/arXiv.2106.09685",
            "source_url": "https://arxiv.org/abs/2106.09685",
        },
    )
    assert response.status_code == 201
    return response.json()["data"]


def test_project_crud_initializes_six_documents(client: TestClient) -> None:
    project = create_project(client)
    project_id = project["project_id"]

    assert project["status"] == "planning"
    assert set(project["assets"]) == {
        "overview",
        "related_work",
        "method",
        "experiment",
        "conclusion",
        "manuscript",
    }

    list_response = client.get("/api/v1/projects", params={"q": "Adaptive"})
    assert list_response.status_code == 200
    assert list_response.json()["meta"]["total"] == 1

    update_response = client.patch(
        f"/api/v1/projects/{project_id}",
        json={"status": "writing", "summary": "Drafting the paper."},
    )
    assert update_response.status_code == 200
    assert update_response.json()["data"]["status"] == "writing"

    detail_response = client.get(f"/api/v1/projects/{project_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["data"]["summary"] == "Drafting the paper."


def test_project_delete_soft_deletes_project(client: TestClient, tmp_path: Path) -> None:
    db_path = tmp_path / "research_flow.sqlite"
    project = create_project(client)
    project_id = project["project_id"]

    delete_response = client.delete(f"/api/v1/projects/{project_id}")
    assert delete_response.status_code == 204

    detail_response = client.get(f"/api/v1/projects/{project_id}")
    assert detail_response.status_code == 404

    list_response = client.get("/api/v1/projects")
    assert list_response.status_code == 200
    assert list_response.json()["meta"]["total"] == 0

    with sqlite3.connect(db_path) as conn:
        is_deleted = conn.execute(
            "SELECT is_deleted FROM asset_registry WHERE asset_id = ?",
            (project_id,),
        ).fetchone()[0]
        doc_count = conn.execute(
            "SELECT COUNT(*) FROM biz_doc_layout WHERE parent_id = ?",
            (project_id,),
        ).fetchone()[0]

    assert is_deleted == 1
    assert doc_count == 6


def test_project_rejects_legacy_status_input(client: TestClient) -> None:
    response = client.post(
        "/api/v1/projects",
        json={
            "name": "Legacy Status Project",
            "status": "active",
        },
    )

    assert response.status_code == 422


def test_project_documents_use_related_work_role(client: TestClient) -> None:
    project = create_project(client)
    project_id = project["project_id"]

    get_response = client.get(f"/api/v1/projects/{project_id}/documents/related_work")
    assert get_response.status_code == 200
    assert get_response.json()["data"]["doc_role"] == "related_work"

    update_response = client.put(
        f"/api/v1/projects/{project_id}/documents/related_work",
        json={"content": "# Related Work\n\nPaper cluster.", "base_version": 1},
    )
    assert update_response.status_code == 200
    assert update_response.json()["data"]["version"] == 2
    assert "Paper cluster." in update_response.json()["data"]["content"]

    legacy_response = client.get(f"/api/v1/projects/{project_id}/documents/related-work")
    assert legacy_response.status_code == 422


def test_project_can_link_and_unlink_existing_paper(
    client: TestClient,
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "research_flow.sqlite"
    paper = create_paper(client)
    project = create_project(client)

    link_response = client.post(
        f"/api/v1/projects/{project['project_id']}/papers:link",
        json={"paper_id": paper["paper_id"], "relation_type": "related_work"},
    )
    assert link_response.status_code == 200
    linked = link_response.json()["data"]
    assert linked[0]["paper_id"] == paper["paper_id"]
    assert linked[0]["relation_type"] == "related_work"

    list_response = client.get(f"/api/v1/projects/{project['project_id']}/papers")
    assert list_response.status_code == 200
    assert list_response.json()["data"][0]["title"].startswith("LoRA")

    unlink_response = client.delete(
        f"/api/v1/projects/{project['project_id']}/papers/{paper['paper_id']}"
    )
    assert unlink_response.status_code == 200
    assert unlink_response.json()["data"] == {
        "project_id": project["project_id"],
        "paper_id": paper["paper_id"],
    }

    empty_response = client.get(f"/api/v1/projects/{project['project_id']}/papers")
    assert empty_response.status_code == 200
    assert empty_response.json()["data"] == []

    with sqlite3.connect(db_path) as conn:
        doc_count = conn.execute(
            "SELECT COUNT(*) FROM biz_doc_layout WHERE parent_id = ?",
            (project["project_id"],),
        ).fetchone()[0]
        paper_link_count = conn.execute(
            "SELECT COUNT(*) FROM asset_link WHERE source_id = ? AND target_id = ?",
            (project["project_id"], paper["paper_id"]),
        ).fetchone()[0]

    assert doc_count == 6
    assert paper_link_count == 0


def test_project_link_legacy_route_is_removed(client: TestClient) -> None:
    paper = create_paper(client)
    project = create_project(client)

    response = client.post(
        f"/api/v1/projects/{project['project_id']}/papers/{paper['paper_id']}"
    )

    assert response.status_code == 405


def test_project_refresh_overview_writes_job_and_managed_block(
    client: TestClient,
) -> None:
    paper = create_paper(client)
    project = create_project(client)
    project_id = project["project_id"]
    link_response = client.post(
        f"/api/v1/projects/{project_id}/papers:link",
        json={"paper_id": paper["paper_id"], "relation_type": "baseline"},
    )
    assert link_response.status_code == 200

    response = client.post(
        f"/api/v1/projects/{project_id}/refresh-overview",
        json={"focus_instructions": "Summarize baseline coverage."},
    )

    assert response.status_code == 202
    job = response.json()["data"]
    assert job["type"] == "project_refresh_overview"
    assert job["status"] == "succeeded"
    assert job["resource_type"] == "Project"
    assert job["resource_id"] == project_id
    assert job["result"]["output_doc_role"] == "overview"

    document_response = client.get(f"/api/v1/projects/{project_id}/documents/overview")
    assert document_response.status_code == 200
    content = document_response.json()["data"]["content"]
    assert 'RF:BLOCK_START id="overview_stats"' in content
    assert "| Linked papers | 1 |" in content
    assert "Summarize baseline coverage." in content


def test_project_related_work_generation_preserves_locked_blocks(
    client: TestClient,
) -> None:
    paper = create_paper(client)
    project = create_project(client)
    project_id = project["project_id"]
    client.post(
        f"/api/v1/projects/{project_id}/papers:link",
        json={"paper_id": paper["paper_id"], "relation_type": "related_work"},
    )
    locked_content = "\n".join(
        [
            "# Related Work",
            "",
            '<!-- RF:BLOCK_START id="related_work_summary" managed="false" version="1" -->',
            "## Related Work Summary",
            "",
            "Human-confirmed summary.",
            '<!-- RF:BLOCK_END id="related_work_summary" -->',
        ]
    )
    update_response = client.put(
        f"/api/v1/projects/{project_id}/documents/related_work",
        json={"content": locked_content, "base_version": 1},
    )
    assert update_response.status_code == 200

    response = client.post(
        f"/api/v1/projects/{project_id}/generate-related-work",
        json={},
    )

    assert response.status_code == 202
    job = response.json()["data"]
    assert job["type"] == "project_generate_related_work"
    assert job["status"] == "succeeded"
    document_response = client.get(
        f"/api/v1/projects/{project_id}/documents/related_work"
    )
    content = document_response.json()["data"]["content"]
    assert "Human-confirmed summary." in content
    assert content.count('id="related_work_summary"') == 2
    assert 'RF:BLOCK_START id="paper_grouping" managed="true"' in content
    assert 'RF:BLOCK_START id="method_comparison" managed="true"' in content


@pytest.mark.parametrize(
    ("path", "doc_role", "block_id"),
    [
        ("generate-method", "method", "method_draft"),
        ("generate-experiment", "experiment", "experiment_plan"),
        ("generate-conclusion", "conclusion", "conclusion_summary"),
        ("generate-manuscript", "manuscript", "manuscript_abstract"),
    ],
)
def test_project_generation_task_endpoints_write_expected_documents(
    client: TestClient,
    path: str,
    doc_role: str,
    block_id: str,
) -> None:
    project = create_project(client)
    project_id = project["project_id"]

    response = client.post(f"/api/v1/projects/{project_id}/{path}", json={})

    assert response.status_code == 202
    job = response.json()["data"]
    assert job["status"] == "succeeded"
    assert job["result"]["output_doc_role"] == doc_role
    document_response = client.get(f"/api/v1/projects/{project_id}/documents/{doc_role}")
    assert document_response.status_code == 200
    assert f'RF:BLOCK_START id="{block_id}" managed="true"' in document_response.json()[
        "data"
    ]["content"]
