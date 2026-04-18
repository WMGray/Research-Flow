import shutil
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.services.mcp.zotero_client import zotero_client


def test_zotero_client_reads_env_and_defaults_local_mode(monkeypatch) -> None:
    temp_dir = Path(".uv-cache") / f"test-zotero-client-{uuid.uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        fake_roaming = temp_dir / "AppData" / "Roaming"
        fake_binary = fake_roaming / "uv" / "tools" / "zotero-mcp-server" / "Scripts" / "zotero-mcp.exe"
        fake_binary.parent.mkdir(parents=True, exist_ok=True)
        fake_binary.write_text("", encoding="utf-8")

        monkeypatch.setenv("APPDATA", str(fake_roaming))
        monkeypatch.setenv("ZOTERO_MCP_ENABLED", "true")
        monkeypatch.setenv("ZOTERO_MCP_COMMAND", "zotero-mcp")
        monkeypatch.setenv("ZOTERO_MCP_ARGS", "serve")
        monkeypatch.setenv("ZOTERO_LIBRARY_TYPE", "user")
        monkeypatch.setenv("ZOTERO_API_KEY", "test-key")
        monkeypatch.setenv("ZOTERO_LIBRARY_ID", "12345678")
        monkeypatch.setenv("ZOTERO_LOCAL", "local")
        monkeypatch.setenv("ZOTERO_MCP_TIMEOUT_SECONDS", "45")

        zotero_client.reset()
        summary = zotero_client.get_config_summary()

        assert summary["framework"] == "agno"
        assert summary["command"] == str(fake_binary)
        assert summary["args"] == ["serve"]
        assert summary["mode"] == "local"
        assert summary["library_id"] == "12345678"
        assert summary["timeout_seconds"] == 45
        assert "ZOTERO_API_KEY" in summary["env_keys"]
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_mcp_service_status_endpoint_exposes_zotero_summary(monkeypatch) -> None:
    monkeypatch.setenv("ZOTERO_MCP_ENABLED", "true")
    monkeypatch.setenv("ZOTERO_MCP_COMMAND", "zotero-mcp")
    monkeypatch.setenv("ZOTERO_MCP_ARGS", "serve")
    monkeypatch.setenv("ZOTERO_LOCAL", "local")
    zotero_client.reset()

    with TestClient(app) as client:
        response = client.get("/services/mcp")

    assert response.status_code == 200
    payload = response.json()
    assert payload["framework"] == "agno"
    assert payload["transport"] == "stdio"
    assert payload["args"] == ["serve"]
