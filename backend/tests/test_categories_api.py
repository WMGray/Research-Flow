from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from core.config import reset_settings


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    run_dir = Path(".uv-cache") / "codex-tests" / f"categories-{uuid4().hex}"
    monkeypatch.setenv("RFLOW_DB_PATH", str(run_dir / "research_flow.sqlite"))
    monkeypatch.setenv("RFLOW_STORAGE_DIR", str(run_dir / "storage"))
    monkeypatch.setenv("RESEARCH_FLOW_ENV_FILE", "none")
    reset_settings()
    with TestClient(app) as test_client:
        yield test_client
    reset_settings()


def test_category_crud_returns_tree(client: TestClient) -> None:
    root_response = client.post(
        "/api/v1/categories",
        json={"name": "LLM", "sort_order": 1},
    )
    assert root_response.status_code == 201
    root = root_response.json()["data"]

    child_response = client.post(
        "/api/v1/categories",
        json={"name": "PEFT", "parent_id": root["category_id"]},
    )
    assert child_response.status_code == 201
    child = child_response.json()["data"]
    assert child["path"] == "LLM/PEFT"

    tree_response = client.get("/api/v1/categories")
    assert tree_response.status_code == 200
    tree = tree_response.json()["data"]
    assert tree[0]["name"] == "LLM"
    assert tree[0]["children"][0]["name"] == "PEFT"

    update_response = client.patch(
        f"/api/v1/categories/{child['category_id']}",
        json={"name": "Adapters", "parent_id": None},
    )
    assert update_response.status_code == 200
    assert update_response.json()["data"]["path"] == "Adapters"

    delete_response = client.delete(f"/api/v1/categories/{child['category_id']}")
    assert delete_response.status_code == 204


def test_category_delete_rejects_in_use_category(client: TestClient) -> None:
    category = client.post("/api/v1/categories", json={"name": "NLP"}).json()["data"]
    paper_response = client.post(
        "/api/v1/papers",
        json={"title": "Categorized Paper", "category_id": category["category_id"]},
    )
    assert paper_response.status_code == 201

    delete_response = client.delete(f"/api/v1/categories/{category['category_id']}")

    assert delete_response.status_code == 409
    assert delete_response.json()["detail"]["code"] == "CATEGORY_IN_USE"


def test_category_tree_includes_global_paper_counts(client: TestClient) -> None:
    first = client.post("/api/v1/categories", json={"name": "NLP"}).json()["data"]
    second = client.post("/api/v1/categories", json={"name": "CV"}).json()["data"]
    client.post(
        "/api/v1/papers",
        json={"title": "Paper A", "category_id": first["category_id"]},
    )
    client.post(
        "/api/v1/papers",
        json={"title": "Paper B", "category_id": second["category_id"]},
    )
    client.post(
        "/api/v1/papers",
        json={"title": "Paper C", "category_id": second["category_id"]},
    )

    tree_response = client.get("/api/v1/categories")

    assert tree_response.status_code == 200
    counts = {
        category["name"]: category["paper_count"]
        for category in tree_response.json()["data"]
    }
    assert counts == {"CV": 2, "NLP": 1}
