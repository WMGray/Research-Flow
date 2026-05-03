"""Run a local LoRA confirm-pipeline demo with durable output artifacts."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3
import sys
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient


BACKEND_ROOT = Path(__file__).resolve().parents[1]
DEMO_ROOT = BACKEND_ROOT / "data" / "tmp" / "lora_confirm_demo"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.main import app  # noqa: E402
from core.config import reset_settings  # noqa: E402
from core.services.llm import llm_registry  # noqa: E402
from core.services.llm.schemas import LLMMessage, LLMRequest, LLMResponse  # noqa: E402


LORA_REFINED_MARKDOWN = """# LoRA: Low-Rank Adaptation of Large Language Models

## Related Work

Large language models are commonly adapted by full fine-tuning, adapter layers,
and prompt-based methods. LoRA freezes the pretrained model weights and injects
trainable low-rank matrices into selected Transformer projections.

## Method

LoRA represents weight updates with a low-rank decomposition. The paper argues
that adaptation updates have low intrinsic rank, so training only the injected
matrices can preserve quality while reducing trainable parameters.

## Experiment

The paper evaluates LoRA on RoBERTa, DeBERTa, GPT-2, and GPT-3. Experiments
include GLUE, WikiSQL, MultiNLI, SAMSum, E2E NLG Challenge, WebNLG, and DART
benchmark datasets. LoRA matches or exceeds fine-tuning baselines while greatly
reducing trainable parameters.

## Conclusion

LoRA reduces adaptation cost and deployment latency by keeping pretrained
weights frozen and merging the learned low-rank update at inference time.
"""

LORA_RAW_MARKDOWN = """# LoRA: Low-Rank Adaptation of Large Language Models

Authors: Edward J. Hu, Yelong Shen, Phillip Wallis, Zeyuan Allen-Zhu, Yuanzhi Li,
Shean Wang, Lu Wang, and Weizhu Chen.

Abstract: LoRA freezes the pretrained model weights and injects trainable
low-rank decomposition matrices into each layer of the Transformer architecture,
greatly reducing the number of trainable parameters for downstream adaptation.

Related Work: Large language models are commonly adapted by full fine-tuning,
adapter layers, and prompt-based methods. LoRA focuses on parameter-efficient
fine-tuning while avoiding additional inference latency.

Method: LoRA represents weight updates with a low-rank decomposition. The paper
argues that adaptation updates have low intrinsic rank, so training only the
injected matrices can preserve quality while reducing trainable parameters.

Experiments: The paper evaluates LoRA on RoBERTa, DeBERTa, GPT-2, and GPT-3.
Experiments include GLUE, WikiSQL, MultiNLI, SAMSum, E2E NLG Challenge, WebNLG,
and DART benchmark datasets. LoRA matches or exceeds fine-tuning baselines while
greatly reducing trainable parameters.

Conclusion: LoRA reduces adaptation cost and deployment latency by keeping
pretrained weights frozen and merging the learned low-rank update at inference
time.
"""


def _source_lines(prompt: str) -> list[str]:
    return [
        line[7:]
        for line in prompt.splitlines()
        if len(line) > 7 and line[:5].isdigit() and line[5:7] == ": "
    ]


async def fake_generate(request: LLMRequest) -> LLMResponse:
    feature = request.feature or ""
    lines = _source_lines(request.messages[0].content)
    if feature == "paper_refine_parse_diagnose":
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
                        "description": "Normalize LoRA demo markdown.",
                        "suggested_action": "replace_span",
                        "needs_pdf_context": False,
                    }
                ],
            }
        )
    elif feature == "paper_refine_parse_repair":
        preserved_metadata = "\n".join(lines[:6])
        replacement_parts = [LORA_REFINED_MARKDOWN.strip()]
        if preserved_metadata:
            replacement_parts.append(
                "<!-- preserved source metadata -->\n" + preserved_metadata
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
                        "replacement": "\n\n".join(replacement_parts),
                        "confidence": 0.95,
                    }
                ],
            }
        )
    elif feature == "paper_note_generate_block":
        content = json.dumps(
            {
                "content": (
                    "LoRA adapts large language models by training low-rank "
                    "updates while freezing the base model."
                )
            }
        )
    else:
        content = json.dumps(
            {
                "source_hash": "",
                "status": "pass",
                "summary": "LoRA demo verifier passed.",
                "blocking_issues": [],
                "review_items": [],
            }
        )
    return LLMResponse(
        feature=feature,
        model_key="fake_lora_confirm_demo",
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


def run_demo() -> dict[str, Any]:
    run_root = DEMO_ROOT / f"run_{uuid4().hex}"
    storage_dir = run_root / "storage"
    db_path = run_root / "research_flow.sqlite"
    os.environ["RESEARCH_FLOW_ENV_FILE"] = "none"
    os.environ["RFLOW_DB_PATH"] = str(db_path)
    os.environ["RFLOW_STORAGE_DIR"] = str(storage_dir)
    reset_settings()
    llm_registry.generate = fake_generate

    with TestClient(app) as client:
        paper = _require_ok(
            client.post(
                "/api/v1/papers",
                json={
                    "title": "LoRA: Low-Rank Adaptation of Large Language Models",
                    "abstract": (
                        "LoRA freezes pretrained model weights and trains "
                        "low-rank adaptation matrices."
                    ),
                    "authors": [
                        "Edward J. Hu",
                        "Yelong Shen",
                        "Phillip Wallis",
                        "Zeyuan Allen-Zhu",
                        "Yuanzhi Li",
                        "Shean Wang",
                        "Lu Wang",
                        "Weizhu Chen",
                    ],
                    "year": 2021,
                    "venue": "ICLR",
                    "doi": "10.48550/arXiv.2106.09685",
                    "source_url": "https://arxiv.org/abs/2106.09685",
                    "pdf_url": "https://arxiv.org/pdf/2106.09685",
                    "source_kind": "manual",
                },
            ),
            201,
        )["data"]
        paper_id = int(paper["paper_id"])
        for path, body, expected in (
            (f"/api/v1/papers/{paper_id}/download", None, 202),
            (f"/api/v1/papers/{paper_id}/parse", {}, 202),
        ):
            response = client.post(path, json=body) if body is not None else client.post(path)
            _require_ok(response, expected)
        with sqlite3.connect(db_path) as conn:
            paper_dir = conn.execute(
                """
                SELECT pi.storage_path
                FROM asset_registry ar
                JOIN physical_item pi ON pi.item_id = ar.item_id
                WHERE ar.asset_id = ?
                """,
                (paper_id,),
            ).fetchone()[0]
        raw_path = Path(paper_dir) / "parsed" / "raw.md"
        raw_path.write_text(LORA_RAW_MARKDOWN, encoding="utf-8")
        _require_ok(client.post(f"/api/v1/papers/{paper_id}/refine-parse", json={}), 202)
        _require_ok(client.post(f"/api/v1/papers/{paper_id}/submit-review"), 200)
        confirm = _require_ok(
            client.post(f"/api/v1/papers/{paper_id}/confirm-review"),
            202,
        )["data"]
        final_paper = _require_ok(client.get(f"/api/v1/papers/{paper_id}"))["data"]
        artifacts = _require_ok(client.get(f"/api/v1/papers/{paper_id}/artifacts"))[
            "data"
        ]
        sections = _require_ok(
            client.get(f"/api/v1/papers/{paper_id}/parsed/sections")
        )["data"]

    with sqlite3.connect(db_path) as conn:
        knowledge_count = conn.execute(
            "SELECT COUNT(*) FROM biz_knowledge WHERE source_paper_asset_id = ?",
            (paper_id,),
        ).fetchone()[0]
        dataset_names = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM biz_dataset ORDER BY name ASC"
            ).fetchall()
        ]

    metadata_path = next(
        Path(item["storage_path"])
        for item in artifacts
        if item["artifact_key"] == "metadata_json"
    )
    return {
        "run_root": str(run_root),
        "paper_id": paper_id,
        "paper_slug": final_paper["paper_slug"],
        "paper_stage": final_paper["paper_stage"],
        "confirm_job_status": confirm["job"]["status"],
        "metadata_path": str(metadata_path),
        "paper_dir": str(metadata_path.parent),
        "section_keys": [item["section_key"] for item in sections if item["generated"]],
        "knowledge_count": knowledge_count,
        "dataset_names": dataset_names,
        "artifact_keys": sorted(item["artifact_key"] for item in artifacts),
    }


def main() -> int:
    summary = run_demo()
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
