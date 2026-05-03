from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from core.config import reset_settings


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[TestClient]:
    monkeypatch.setenv("RESEARCH_FLOW_ENV_FILE", "none")
    monkeypatch.setenv("RFLOW_DB_PATH", str(tmp_path / "research_flow.sqlite"))
    monkeypatch.setenv("RFLOW_STORAGE_DIR", str(tmp_path / "storage"))
    reset_settings()
    with TestClient(app) as test_client:
        yield test_client
    reset_settings()


def test_discovery_feed_conference_recommendation_and_graph(client: TestClient) -> None:
    paper_response = client.post(
        "/api/v1/papers",
        json={
            "title": "Discovery Smoke Paper",
            "abstract": "A short paper for feed smoke tests.",
            "authors": ["Ada Lovelace"],
            "year": 2026,
            "venue": "ICLR",
        },
    )
    assert paper_response.status_code == 201

    refresh_response = client.post(
        "/api/v1/feed/refresh",
        json={"source": "paper_library", "feed_date": "2026-05-03", "limit": 5},
    )
    assert refresh_response.status_code == 202
    feed_items = refresh_response.json()["data"]
    assert feed_items[0]["title"] == "Discovery Smoke Paper"

    item_id = feed_items[0]["item_id"]
    update_response = client.patch(
        f"/api/v1/feed/items/{item_id}",
        json={"status": "saved"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["data"]["status"] == "saved"

    conference_response = client.post(
        "/api/v1/conferences",
        json={
            "name": "Smoke Conference",
            "acronym": "SMOKE",
            "year": 2026,
            "rank": "CCF-A",
        },
    )
    assert conference_response.status_code == 201
    conference = conference_response.json()["data"]

    update_conference = client.patch(
        f"/api/v1/conferences/{conference['conference_id']}",
        json={"status": "submitted"},
    )
    assert update_conference.status_code == 200
    assert update_conference.json()["data"]["status"] == "submitted"

    recommendations = client.get("/api/v1/recommendations")
    assert recommendations.status_code == 200
    assert recommendations.json()["data"]

    graph = client.get("/api/v1/graph")
    assert graph.status_code == 200
    assert graph.json()["data"]["nodes"]
