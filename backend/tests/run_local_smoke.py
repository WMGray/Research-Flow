"""本地最小闭环 smoke 脚本。

该脚本不访问网络、不需要 API key，只通过 FastAPI TestClient 验证
health、Paper CRUD、Paper 文档、parse job、Project 创建和 Paper 关联。
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import sys
from typing import Any

from fastapi.testclient import TestClient


BACKEND_ROOT = Path(__file__).resolve().parents[1]
SMOKE_TEMP_ROOT = BACKEND_ROOT / "data" / "tmp" / "local_smoke"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.main import app  # noqa: E402


def require_ok(response: Any, expected_status: int = 200) -> dict[str, Any]:
    """校验 HTTP 状态码并返回 JSON 响应体。"""

    if response.status_code != expected_status:
        raise RuntimeError(
            f"Expected {expected_status}, got {response.status_code}: {response.text}"
        )
    if response.status_code == 204:
        return {}
    payload = response.json()
    if payload.get("error") is not None:
        raise RuntimeError(f"Unexpected API error: {payload['error']}")
    return payload


def run_smoke(client: TestClient) -> dict[str, Any]:
    """执行本地 Paper + Project 最小链路。"""

    health = require_ok(client.get("/health"))["status"]

    paper_payload = {
        "title": "Local Smoke Paper",
        "authors": ["Research Flow"],
        "year": 2026,
        "venue": "Local",
        "doi": "10.0000/local-smoke",
        "tags": ["smoke"],
        "parse_after_import": True,
    }
    paper = require_ok(client.post("/api/v1/papers", json=paper_payload), 201)["data"]
    paper_id = paper["paper_id"]

    papers = require_ok(client.get("/api/v1/papers", params={"q": "Smoke"}))
    document = require_ok(client.get(f"/api/v1/papers/{paper_id}/documents/human"))["data"]
    updated_document = require_ok(
        client.put(
            f"/api/v1/papers/{paper_id}/documents/human",
            json={"content": "# Local Smoke\n\nReviewed.", "base_version": document["version"]},
        )
    )["data"]
    job = require_ok(client.get(f"/api/v1/jobs/{paper['parse_job_id']}"))["data"]

    project = require_ok(
        client.post(
            "/api/v1/projects",
            json={
                "name": "Local Smoke Project",
                "summary": "本地 smoke 测试项目。",
                "owner": "tester",
            },
        ),
        201,
    )["data"]
    project_id = project["project_id"]
    linked_papers = require_ok(client.post(f"/api/v1/projects/{project_id}/papers/{paper_id}"))["data"]
    project_document = require_ok(client.get(f"/api/v1/projects/{project_id}/documents/overview"))["data"]

    return {
        "health": health,
        "paper_id": paper_id,
        "paper_status": paper["status"],
        "paper_count": papers["meta"]["total"],
        "human_doc_version": updated_document["version"],
        "job_id": job["job_id"],
        "job_status": job["status"],
        "project_id": project_id,
        "linked_paper_count": len(linked_papers),
        "project_overview_version": project_document["version"],
    }


def main() -> int:
    """创建临时数据目录并运行 smoke。"""

    if SMOKE_TEMP_ROOT.exists():
        shutil.rmtree(SMOKE_TEMP_ROOT)
    SMOKE_TEMP_ROOT.mkdir(parents=True, exist_ok=True)
    os.environ["RESEARCH_FLOW_ENV_FILE"] = "none"
    os.environ["RFLOW_DB_PATH"] = str(SMOKE_TEMP_ROOT / "research_flow.sqlite")
    os.environ["RFLOW_STORAGE_DIR"] = str(SMOKE_TEMP_ROOT / "storage")
    with TestClient(app) as client:
        summary = run_smoke(client)
    shutil.rmtree(SMOKE_TEMP_ROOT, ignore_errors=True)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
