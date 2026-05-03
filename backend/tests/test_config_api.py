from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from core.config import reset_settings


def build_test_paths() -> tuple[Path, Path]:
    run_dir = (
        Path.cwd() / ".uv-cache" / "codex-tests" / f"config-{uuid4().hex}"
    ).resolve()
    return run_dir / "research_flow.sqlite", run_dir / "storage"


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    db_path, storage_dir = build_test_paths()
    monkeypatch.setenv("RFLOW_DB_PATH", str(db_path))
    monkeypatch.setenv("RFLOW_STORAGE_DIR", str(storage_dir))
    monkeypatch.setenv("RESEARCH_FLOW_ENV_FILE", "none")
    reset_settings()
    with TestClient(app) as test_client:
        yield test_client
    reset_settings()


def test_config_agents_and_llm_status_seed_from_settings(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = client.get("/api/v1/config/agents")

    assert response.status_code == 200
    agents = response.json()["data"]
    profile_keys = {agent["profile_key"] for agent in agents}
    assert "default_chat" in profile_keys
    assert "paper_note_generate_default" in profile_keys

    update_response = client.put(
        "/api/v1/config/agents/default_chat",
        json={"enabled": False, "temperature": 0.2},
    )
    assert update_response.status_code == 200
    assert update_response.json()["data"]["enabled"] is False

    status_response = client.get("/api/v1/config/llms/status")
    assert status_response.status_code == 200
    status_map = {
        item["profile_key"]: item for item in status_response.json()["data"]
    }
    assert status_map["default_chat"]["connectivity_status"] == "disabled"

    db_path = Path(str(os.getenv("RFLOW_DB_PATH")))
    with sqlite3.connect(db_path) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    assert {"sys_agent_profile", "sys_skill_binding", "sys_llm_probe_result"} <= tables


def test_config_skill_catalog_and_binding(client: TestClient) -> None:
    catalog_response = client.get("/api/v1/config/skills/catalog")

    assert catalog_response.status_code == 200
    catalog = catalog_response.json()["data"]
    skill_names = {item["skill_name"] for item in catalog}
    assert "paper-note-generate" in skill_names

    item_response = client.get("/api/v1/config/skills/catalog/paper-note-generate")
    assert item_response.status_code == 200
    assert item_response.json()["data"]["has_runtime_instructions"] is True

    binding_response = client.get("/api/v1/config/skills/paper-note-generate")
    assert binding_response.status_code == 200
    assert binding_response.json()["data"]["agent_profile_key"] == "default_chat"

    update_response = client.put(
        "/api/v1/config/skills/paper-note-generate",
        json={
            "agent_profile_key": "paper_note_generate_default",
            "runtime_instruction_key": "paper_note_generate.default",
            "toolset": ["llm"],
        },
    )
    assert update_response.status_code == 200
    updated = update_response.json()["data"]
    assert updated["agent_profile_key"] == "paper_note_generate_default"
    assert updated["toolset"] == ["llm"]
