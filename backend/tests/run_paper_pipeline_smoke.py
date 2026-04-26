"""Run a local Paper pipeline smoke test without network or API keys."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import sys
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient


BACKEND_ROOT = Path(__file__).resolve().parents[1]
SMOKE_ROOT = BACKEND_ROOT / "data" / "tmp" / "paper_pipeline_smoke"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.main import app  # noqa: E402
from core.config import reset_settings  # noqa: E402
from core.services.llm import llm_registry  # noqa: E402
from core.services.llm.schemas import LLMMessage, LLMRequest, LLMResponse  # noqa: E402


def _source_lines(prompt: str) -> list[str]:
    return [
        line[7:]
        for line in prompt.splitlines()
        if len(line) > 7 and line[:5].isdigit() and line[5:7] == ": "
    ]


async def fake_generate(request: LLMRequest) -> LLMResponse:
    feature = request.feature or ""
    lines = _source_lines(request.messages[0].content)
    if feature == "pdf_markdown_refine_diagnose":
        content = json.dumps(
            {
                "source_hash": "",
                "issues": [
                    {
                        "issue_id": "issue_001",
                        "type": "heading_ambiguous",
                        "start_line": 1,
                        "end_line": max(len(lines), 1),
                        "severity": "medium",
                        "confidence": 0.95,
                        "description": "Normalize local smoke markdown.",
                        "suggested_action": "replace_span",
                        "needs_pdf_context": False,
                    }
                ],
            }
        )
    elif feature == "pdf_markdown_refine_repair":
        metadata = [line for line in lines if line.startswith(("- DOI:", "- Year:"))]
        replacement = "\n\n".join(
            [
                "# Pipeline Smoke Paper",
                "\n".join(metadata),
                "## Related Work\nRW section.",
                "## Method\nMethod section.",
                "## Experiment\nExp section.",
                "## Conclusion\nLimitations.",
            ]
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
                        "end_line": max(len(lines), 1),
                        "replacement": replacement,
                        "confidence": 0.95,
                    }
                ],
            }
        )
    elif feature == "paper_note_summarizer":
        content = json.dumps(
            {
                "blocks": {
                    "research_question": "Smoke research question.",
                    "core_method": "Smoke core method.",
                    "main_contributions": "Smoke contributions.",
                    "experiment_summary": "Smoke experiment summary.",
                    "limitations": "Smoke limitations.",
                }
            }
        )
    else:
        content = json.dumps(
            {
                "source_hash": "",
                "status": "pass",
                "summary": "Smoke verifier passed.",
                "blocking_issues": [],
                "review_items": [],
            }
        )
    return LLMResponse(
        feature=feature,
        model_key="fake_paper_pipeline",
        platform="fake",
        provider="fake",
        model="fake-model",
        message=LLMMessage(role="assistant", content=content),
    )


def _require_ok(response: Any, expected_status: int = 200) -> dict[str, Any]:
    if response.status_code != expected_status:
        raise RuntimeError(
            f"Expected {expected_status}, got {response.status_code}: {response.text}"
        )
    return response.json()


def run_smoke() -> dict[str, Any]:
    run_root = SMOKE_ROOT / f"run_{uuid4().hex}"
    run_root.mkdir(parents=True, exist_ok=True)
    os.environ["RESEARCH_FLOW_ENV_FILE"] = "none"
    os.environ["RFLOW_DB_PATH"] = str(run_root / "research_flow.sqlite")
    os.environ["RFLOW_STORAGE_DIR"] = str(run_root / "storage")
    reset_settings()
    llm_registry.generate = fake_generate

    with TestClient(app) as client:
        paper = _require_ok(
            client.post(
                "/api/v1/papers",
                json={
                    "title": "Pipeline Smoke Paper",
                    "authors": ["Codex"],
                    "year": 2026,
                    "venue": "Local",
                    "doi": "10.0000/pipeline-smoke",
                },
            ),
            201,
        )["data"]
        paper_id = int(paper["paper_id"])
        pipeline = _require_ok(
            client.post(f"/api/v1/papers/{paper_id}/pipeline", json={}),
            202,
        )["data"]
        if pipeline["status"] != "succeeded":
            raise RuntimeError(f"Pipeline failed: {pipeline}")

        artifacts = _require_ok(client.get(f"/api/v1/papers/{paper_id}/artifacts"))[
            "data"
        ]
        runs = _require_ok(client.get(f"/api/v1/papers/{paper_id}/pipeline-runs"))[
            "data"
        ]
        note = _require_ok(client.get(f"/api/v1/papers/{paper_id}/note"))["data"]
        if "Smoke research question." not in note["content"]:
            raise RuntimeError("Generated note did not contain LLM summary block.")

        update = _require_ok(
            client.put(
                f"/api/v1/papers/{paper_id}/note",
                json={
                    "content": "# Manual Note\n\nManual insight stays.",
                    "base_version": note["version"],
                },
            )
        )["data"]
        merge_job = _require_ok(
            client.post(f"/api/v1/papers/{paper_id}/generate-note"),
            202,
        )["data"]
        merged_note = _require_ok(client.get(f"/api/v1/papers/{paper_id}/note"))[
            "data"
        ]
        final_paper = _require_ok(client.get(f"/api/v1/papers/{paper_id}"))["data"]

    reset_settings()
    shutil.rmtree(run_root, ignore_errors=True)
    return {
        "paper_id": paper_id,
        "pipeline_status": pipeline["status"],
        "pipeline_jobs": [job["type"] for job in pipeline["jobs"]],
        "artifact_keys": sorted(item["artifact_key"] for item in artifacts),
        "run_stages": [item["stage"] for item in runs],
        "first_note_status": pipeline["paper"]["note_status"],
        "manual_note_version": update["version"],
        "merge_job_status": merge_job["status"],
        "merge_policy": merge_job["result"]["merge_policy"],
        "final_note_status": final_paper["note_status"],
        "manual_text_preserved": "Manual insight stays." in merged_note["content"],
        "managed_block_preserved": 'RF:BLOCK_START id="research_question"'
        in merged_note["content"],
    }


def main() -> int:
    summary = run_smoke()
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
