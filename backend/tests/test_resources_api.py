from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from core.config import reset_settings


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[TestClient]:
    monkeypatch.setenv("RFLOW_DB_PATH", str(tmp_path / "research_flow.sqlite"))
    monkeypatch.setenv("RFLOW_STORAGE_DIR", str(tmp_path / "storage"))
    monkeypatch.setenv("RESEARCH_FLOW_ENV_FILE", "none")
    reset_settings()
    with TestClient(app) as test_client:
        try:
            yield test_client
        finally:
            app.dependency_overrides.clear()
            reset_settings()


def create_project(client: TestClient) -> dict:
    response = client.post(
        "/api/v1/projects",
        json={
            "name": "Resource Linked Project",
            "summary": "Project for resource API tests.",
        },
    )
    assert response.status_code == 201
    return response.json()["data"]


def create_paper(client: TestClient) -> dict:
    response = client.post(
        "/api/v1/papers",
        json={
            "title": "Resource Extraction Paper",
            "doi": "10.1234/resource-extraction",
        },
    )
    assert response.status_code == 201
    return response.json()["data"]


def test_dataset_crud_and_project_link(client: TestClient) -> None:
    project = create_project(client)

    create_response = client.post(
        "/api/v1/datasets",
        json={
            "name": "MMLU",
            "aliases": ["Massive Multitask Language Understanding"],
            "task_type": "benchmark",
            "description": "Knowledge benchmark.",
        },
    )
    assert create_response.status_code == 201
    dataset = create_response.json()["data"]

    list_response = client.get("/api/v1/datasets", params={"q": "MMLU"})
    assert list_response.status_code == 200
    assert list_response.json()["meta"]["total"] == 1

    update_response = client.patch(
        f"/api/v1/datasets/{dataset['dataset_id']}",
        json={"scale": "large"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["data"]["scale"] == "large"

    link_response = client.post(
        f"/api/v1/projects/{project['project_id']}/datasets:link",
        json={"dataset_id": dataset["dataset_id"], "relation_type": "USES_DATASET"},
    )
    assert link_response.status_code == 200
    assert link_response.json()["data"][0]["resource_id"] == dataset["dataset_id"]

    list_links = client.get(f"/api/v1/projects/{project['project_id']}/datasets")
    assert list_links.status_code == 200
    assert list_links.json()["data"][0]["display_name"] == "MMLU"

    unlink_response = client.delete(
        f"/api/v1/projects/{project['project_id']}/datasets/{dataset['dataset_id']}"
    )
    assert unlink_response.status_code == 200
    assert client.get(f"/api/v1/projects/{project['project_id']}/datasets").json()[
        "data"
    ] == []


def test_knowledge_crud_search_and_paper_project_links(
    client: TestClient,
) -> None:
    paper = create_paper(client)
    project = create_project(client)

    create_response = client.post(
        "/api/v1/knowledge",
        json={
            "knowledge_type": "view",
            "title": "Low-rank adapters reduce trainable parameters",
            "summary_zh": "LoRA freezes base weights and trains low-rank adapters.",
            "source_paper_asset_id": paper["paper_id"],
            "confidence_score": 0.8,
        },
    )
    assert create_response.status_code == 201
    knowledge = create_response.json()["data"]

    paper_knowledge = client.get(f"/api/v1/papers/{paper['paper_id']}/knowledge")
    assert paper_knowledge.status_code == 200
    assert paper_knowledge.json()["data"][0]["resource_id"] == knowledge["knowledge_id"]

    search_response = client.get("/api/v1/knowledge/search", params={"q": "adapters"})
    assert search_response.status_code == 200
    assert search_response.json()["meta"]["total"] == 1

    update_response = client.patch(
        f"/api/v1/knowledge/{knowledge['knowledge_id']}",
        json={"review_status": "accepted"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["data"]["review_status"] == "accepted"

    link_response = client.post(
        f"/api/v1/projects/{project['project_id']}/knowledge:link",
        json={
            "knowledge_id": knowledge["knowledge_id"],
            "relation_type": "USES_KNOWLEDGE",
        },
    )
    assert link_response.status_code == 200

    list_links = client.get(f"/api/v1/projects/{project['project_id']}/knowledge")
    assert list_links.status_code == 200
    assert list_links.json()["data"][0]["display_name"].startswith("Low-rank")

    unlink_response = client.delete(
        f"/api/v1/projects/{project['project_id']}/knowledge/{knowledge['knowledge_id']}"
    )
    assert unlink_response.status_code == 200


def test_presentation_flow_and_project_link(client: TestClient) -> None:
    project = create_project(client)

    create_response = client.post(
        "/api/v1/presentations",
        json={"title": "Weekly Reading Report", "scene_type": "group_meeting"},
    )
    assert create_response.status_code == 201
    presentation = create_response.json()["data"]
    presentation_id = presentation["presentation_id"]
    assert set(presentation["assets"]) == {"outline", "slides", "speaker_notes"}

    link_response = client.post(
        f"/api/v1/projects/{project['project_id']}/presentations:link",
        json={"presentation_id": presentation_id},
    )
    assert link_response.status_code == 200
    detail_response = client.get(f"/api/v1/presentations/{presentation_id}")
    assert detail_response.json()["data"]["project_asset_id"] == project["project_id"]

    outline_response = client.get(
        f"/api/v1/presentations/{presentation_id}/documents/outline"
    )
    assert outline_response.status_code == 200
    outline = outline_response.json()["data"]

    update_response = client.put(
        f"/api/v1/presentations/{presentation_id}/documents/outline",
        json={"content": "# Outline\n\n- Manual agenda.", "base_version": 1},
    )
    assert update_response.status_code == 200
    assert update_response.json()["data"]["version"] == outline["version"] + 1

    conflict_response = client.put(
        f"/api/v1/presentations/{presentation_id}/documents/outline",
        json={"content": "stale", "base_version": 1},
    )
    assert conflict_response.status_code == 409

    generate_response = client.post(
        f"/api/v1/presentations/{presentation_id}/generate-outline"
    )
    assert generate_response.status_code == 202
    assert generate_response.json()["data"]["status"] == "succeeded"

    slides_response = client.post(
        f"/api/v1/presentations/{presentation_id}/generate-slides"
    )
    assert slides_response.status_code == 202

    export_response = client.post(f"/api/v1/presentations/{presentation_id}/export")
    assert export_response.status_code == 202
    assert export_response.json()["data"]["result"]["export_format"] == "pptx"

    unlink_response = client.delete(
        f"/api/v1/projects/{project['project_id']}/presentations/{presentation_id}"
    )
    assert unlink_response.status_code == 200
    detail_response = client.get(f"/api/v1/presentations/{presentation_id}")
    assert detail_response.json()["data"]["project_asset_id"] is None


def test_project_generation_filters_linked_resources(client: TestClient) -> None:
    project = create_project(client)

    knowledge_ids = []
    for title in ("Finding A", "Finding B"):
        response = client.post("/api/v1/knowledge", json={"title": title})
        assert response.status_code == 201
        knowledge_ids.append(response.json()["data"]["knowledge_id"])
        client.post(
            f"/api/v1/projects/{project['project_id']}/knowledge:link",
            json={"knowledge_id": knowledge_ids[-1]},
        )

    dataset_ids = []
    for name in ("Dataset A", "Dataset B"):
        response = client.post("/api/v1/datasets", json={"name": name})
        assert response.status_code == 201
        dataset_ids.append(response.json()["data"]["dataset_id"])
        client.post(
            f"/api/v1/projects/{project['project_id']}/datasets:link",
            json={"dataset_id": dataset_ids[-1]},
        )

    response = client.post(
        f"/api/v1/projects/{project['project_id']}/refresh-overview",
        json={
            "included_knowledge_ids": [knowledge_ids[0]],
            "included_dataset_ids": [dataset_ids[0]],
        },
    )
    assert response.status_code == 202
    result = response.json()["data"]["result"]
    assert result["linked_knowledge_count"] == 1
    assert result["linked_dataset_count"] == 1

    document = client.get(
        f"/api/v1/projects/{project['project_id']}/documents/overview"
    )
    content = document.json()["data"]["content"]
    assert "| Linked Knowledge | 1 |" in content
    assert "| Linked datasets | 1 |" in content


def test_paper_extracts_evidence_grounded_resources(client: TestClient) -> None:
    paper = create_paper(client)
    paper_id = paper["paper_id"]
    note_response = client.put(
        f"/api/v1/papers/{paper_id}/note",
        json={
            "content": (
                "# Resource Extraction Paper\n\n"
                "We propose a low-rank adapter method that improves parameter "
                "efficiency when evaluated on the MMLU benchmark dataset for "
                "language reasoning tasks."
            ),
            "base_version": 1,
        },
    )
    assert note_response.status_code == 200

    knowledge_response = client.post(f"/api/v1/papers/{paper_id}/extract-knowledge")
    assert knowledge_response.status_code == 202
    assert knowledge_response.json()["data"]["result"]["item_count"] == 1

    datasets_response = client.post(f"/api/v1/papers/{paper_id}/extract-datasets")
    assert datasets_response.status_code == 202
    assert datasets_response.json()["data"]["result"]["item_count"] == 1

    paper_knowledge = client.get(f"/api/v1/papers/{paper_id}/knowledge")
    assert paper_knowledge.status_code == 200
    assert "placeholder" not in paper_knowledge.json()["data"][0]["display_name"]

    paper_datasets = client.get(f"/api/v1/papers/{paper_id}/datasets")
    assert paper_datasets.status_code == 200
    assert paper_datasets.json()["data"][0]["display_name"] == "MMLU"
