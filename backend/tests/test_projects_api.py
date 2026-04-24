"""Project P0 API 回归测试。

测试覆盖 Project 创建、六模块初始化、文档版本控制和 Paper 关联。
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[TestClient]:
    """创建隔离的测试客户端，每个测试使用独立数据库和存储目录。"""

    monkeypatch.setenv("RFLOW_DB_PATH", str(tmp_path / "research_flow.sqlite"))
    monkeypatch.setenv("RFLOW_STORAGE_DIR", str(tmp_path / "storage"))
    with TestClient(app) as test_client:
        yield test_client


def create_project(client: TestClient) -> dict:
    """通过 API 创建一个示例 Project。"""

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
    """通过 API 创建一个可被 Project 关联的示例 Paper。"""

    response = client.post(
        "/api/v1/papers",
        json={
            "title": "LoRA: Low-Rank Adaptation of Large Language Models",
            "authors": ["Edward J. Hu"],
            "doi": "10.48550/arXiv.2106.09685",
        },
    )
    assert response.status_code == 201
    return response.json()["data"]


def test_project_crud_initializes_six_documents(client: TestClient) -> None:
    """验证 Project CRUD 与六个默认模块文档初始化。"""

    project = create_project(client)
    project_id = project["project_id"]

    assert project["status"] == "active"
    assert set(project["assets"]) == {
        "overview",
        "related-work",
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
        json={"status": "paused", "summary": "Paused for review."},
    )
    assert update_response.status_code == 200
    assert update_response.json()["data"]["status"] == "paused"

    detail_response = client.get(f"/api/v1/projects/{project_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["data"]["summary"] == "Paused for review."


def test_project_documents_are_versioned(client: TestClient) -> None:
    """验证 Project 模块文档读写和乐观版本冲突检测。"""

    project = create_project(client)
    project_id = project["project_id"]

    get_response = client.get(f"/api/v1/projects/{project_id}/documents/method")
    assert get_response.status_code == 200
    document = get_response.json()["data"]
    assert document["version"] == 1
    assert document["content"].startswith("# Method")

    update_response = client.put(
        f"/api/v1/projects/{project_id}/documents/method",
        json={"content": "# Method\n\nNew idea.", "base_version": 1},
    )
    assert update_response.status_code == 200
    updated = update_response.json()["data"]
    assert updated["version"] == 2
    assert "New idea." in updated["content"]

    conflict_response = client.put(
        f"/api/v1/projects/{project_id}/documents/method",
        json={"content": "stale", "base_version": 1},
    )
    assert conflict_response.status_code == 409
    assert (
        conflict_response.json()["detail"]["code"]
        == "PROJECT_DOCUMENT_VERSION_CONFLICT"
    )


def test_project_can_link_existing_paper(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """验证 Project 可以关联已有 Paper，并写入 asset_link。"""

    db_path = tmp_path / "research_flow.sqlite"
    monkeypatch.setenv("RFLOW_DB_PATH", str(db_path))
    monkeypatch.setenv("RFLOW_STORAGE_DIR", str(tmp_path / "storage"))

    paper = create_paper(client)
    project = create_project(client)

    link_response = client.post(
        f"/api/v1/projects/{project['project_id']}/papers/{paper['paper_id']}"
    )
    assert link_response.status_code == 200
    linked = link_response.json()["data"]
    assert linked[0]["paper_id"] == paper["paper_id"]
    assert linked[0]["relation_type"] == "REFERENCES"

    list_response = client.get(f"/api/v1/projects/{project['project_id']}/papers")
    assert list_response.status_code == 200
    assert list_response.json()["data"][0]["title"].startswith("LoRA")

    with sqlite3.connect(db_path) as conn:
        doc_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM biz_doc_layout
            WHERE parent_id = ?
            """,
            (project["project_id"],),
        ).fetchone()[0]
        paper_link_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM asset_link
            WHERE source_id = ? AND target_id = ? AND relation_type = 'REFERENCES'
            """,
            (project["project_id"], paper["paper_id"]),
        ).fetchone()[0]

    assert doc_count == 6
    assert paper_link_count == 1
