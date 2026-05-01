"""Run a real-network Paper flow probe against a public academic PDF.

This script intentionally uses real providers configured in backend/.env:
- gPaper/network PDF download
- MinerU extraction
- configured LLM features for refine and note generation

It writes a JSON report under backend/data/tmp/test_reports and exits non-zero
if the real flow falls back to stub data or misses a critical stage.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import sys
import time
from typing import Any
from uuid import uuid4


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = BACKEND_ROOT / "data" / "tmp" / "test_reports"
RUN_ROOT = BACKEND_ROOT / "data" / "tmp" / "real_paper_network_probe"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Real network Paper pipeline probe.")
    parser.add_argument(
        "--title",
        default="LoRA: Low-Rank Adaptation of Large Language Models",
    )
    parser.add_argument("--year", type=int, default=2021)
    parser.add_argument("--venue", default="arXiv")
    parser.add_argument("--venue-short", default="arXiv")
    parser.add_argument(
        "--authors",
        default="Edward J. Hu, Yelong Shen",
        help="Comma-separated paper authors for the created paper record.",
    )
    parser.add_argument("--doi", default="10.48550/arXiv.2106.09685")
    parser.add_argument("--source-url", default="https://arxiv.org/abs/2106.09685")
    parser.add_argument("--pdf-url", default="https://arxiv.org/pdf/2106.09685")
    parser.add_argument(
        "--refine-instruction",
        default=(
            "Use only safe, minimal Markdown structural corrections. Preserve all "
            "citations, numbers, formulas, figure captions, tables, model names, "
            "dataset names, and technical terms. Mark uncertain items for review."
        ),
    )
    return parser.parse_args()


def utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def endpoint_call(
    *,
    client: Any,
    method: str,
    path: str,
    expected_status: int,
    json_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    if json_payload is None:
        response = getattr(client, method)(path)
    else:
        response = getattr(client, method)(path, json=json_payload)
    elapsed = round(time.perf_counter() - started, 3)
    payload = response.json() if response.content else {}
    return {
        "method": method.upper(),
        "path": path,
        "status_code": response.status_code,
        "expected_status": expected_status,
        "elapsed_seconds": elapsed,
        "ok": response.status_code == expected_status,
        "payload": payload,
    }


def compact_job(call: dict[str, Any]) -> dict[str, Any]:
    data = call.get("payload", {}).get("data") or {}
    return {
        "job_id": data.get("job_id"),
        "type": data.get("type"),
        "status": data.get("status"),
        "message": data.get("message"),
        "result": data.get("result"),
        "error": data.get("error"),
        "elapsed_seconds": call.get("elapsed_seconds"),
    }


def write_report(report: dict[str, Any]) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / f"real_paper_network_probe_{utc_stamp()}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def read_artifact_text(artifact: dict[str, Any]) -> str:
    path = Path(str(artifact.get("storage_path") or ""))
    if not path.exists() or not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def count_files(path_text: str) -> int:
    path = Path(path_text)
    if not path.exists() or not path.is_dir():
        return 0
    return sum(1 for child in path.rglob("*") if child.is_file())


def main() -> int:
    args = parse_args()
    authors = [author.strip() for author in args.authors.split(",") if author.strip()]
    run_id = uuid4().hex
    run_root = RUN_ROOT / f"run_{run_id}"
    storage_dir = run_root / "storage"
    db_path = run_root / "research_flow.sqlite"

    os.environ["RFLOW_DB_PATH"] = str(db_path)
    os.environ["RFLOW_STORAGE_DIR"] = str(storage_dir)
    os.environ["PAPER_DOWNLOAD_OUTPUT_DIR"] = str(run_root / "downloads")
    os.environ["PAPER_DOWNLOAD_OVERWRITE"] = "true"
    os.environ["PAPER_DOWNLOAD_TIMEOUT"] = "60"
    os.environ["RFLOW_ENABLE_NETWORK_PAPER_DOWNLOAD"] = "1"

    from app.main import app
    from core.config import get_settings, reset_settings
    from fastapi.testclient import TestClient

    reset_settings()
    settings = get_settings()
    report: dict[str, Any] = {
        "run_id": run_id,
        "started_at": datetime.now(UTC).isoformat(),
        "run_root": str(run_root),
        "input": {
            "title": args.title,
            "authors": authors,
            "year": args.year,
            "venue": args.venue,
            "venue_short": args.venue_short,
            "doi": args.doi,
            "source_url": args.source_url,
            "pdf_url": args.pdf_url,
        },
        "configuration": {
            "network_download_enabled": True,
            "mineru_api_token_configured": bool(settings.mineru.api_token),
            "mineru_base_url": settings.mineru.base_url,
            "llm_platforms_with_key": [
                name
                for name, platform in settings.llm.platforms.items()
                if bool(platform.resolve_api_key())
            ],
            "llm_features_present": {
                key: key in settings.llm.features
                for key in [
                    "paper_refine_parse_diagnose",
                    "paper_refine_parse_repair",
                    "paper_refine_parse_verify",
                    "paper_sectioning_default",
                    "paper_note_generate_default",
                    "paper_note_generate_block",
                ]
            },
        },
        "calls": [],
        "checks": {},
    }

    exit_code = 0
    try:
        with TestClient(app) as client:
            create = endpoint_call(
                client=client,
                method="post",
                path="/api/v1/papers",
                expected_status=201,
                json_payload={
                    "title": args.title,
                    "authors": authors,
                    "year": args.year,
                    "venue": args.venue,
                    "venue_short": args.venue_short,
                    "doi": args.doi,
                    "source_url": args.source_url,
                    "pdf_url": args.pdf_url,
                    "tags": ["real-network-probe"],
                },
            )
            report["calls"].append(create)
            paper_id = int(create["payload"]["data"]["paper_id"])

            download = endpoint_call(
                client=client,
                method="post",
                path=f"/api/v1/papers/{paper_id}/download",
                expected_status=202,
            )
            report["calls"].append(download)
            parse = endpoint_call(
                client=client,
                method="post",
                path=f"/api/v1/papers/{paper_id}/parse",
                expected_status=202,
                json_payload={"parser": "mineru", "force": True},
            )
            report["calls"].append(parse)
            refine = endpoint_call(
                client=client,
                method="post",
                path=f"/api/v1/papers/{paper_id}/refine-parse",
                expected_status=202,
                json_payload={"instruction": args.refine_instruction},
            )
            report["calls"].append(refine)

            if compact_job(refine)["status"] == "succeeded":
                split = endpoint_call(
                    client=client,
                    method="post",
                    path=f"/api/v1/papers/{paper_id}/split-sections",
                    expected_status=202,
                )
                report["calls"].append(split)
                note = endpoint_call(
                    client=client,
                    method="post",
                    path=f"/api/v1/papers/{paper_id}/generate-note",
                    expected_status=202,
                )
                report["calls"].append(note)

            artifacts = endpoint_call(
                client=client,
                method="get",
                path=f"/api/v1/papers/{paper_id}/artifacts",
                expected_status=200,
            )
            runs = endpoint_call(
                client=client,
                method="get",
                path=f"/api/v1/papers/{paper_id}/pipeline-runs",
                expected_status=200,
            )
            paper = endpoint_call(
                client=client,
                method="get",
                path=f"/api/v1/papers/{paper_id}",
                expected_status=200,
            )
            report["calls"].extend([artifacts, runs, paper])

            artifact_items = artifacts["payload"]["data"]
            run_items = runs["payload"]["data"]
            download_job = compact_job(download)
            parse_job = compact_job(parse)
            refine_job = compact_job(refine)
            artifact_keys = sorted(item["artifact_key"] for item in artifact_items)
            run_stages = [item["stage"] for item in run_items]
            source_pdf = next(
                (item for item in artifact_items if item["artifact_key"] == "source_pdf"),
                {},
            )
            raw_markdown = next(
                (item for item in artifact_items if item["artifact_key"] == "raw_markdown"),
                {},
            )
            refined_markdown = next(
                (item for item in artifact_items if item["artifact_key"] == "refined_markdown"),
                {},
            )
            note_markdown = next(
                (item for item in artifact_items if item["artifact_key"] == "note_markdown"),
                {},
            )
            refine_result = refine_job.get("result") or {}
            parse_result = parse_job.get("result") or {}
            parse_artifacts = parse_result.get("artifacts") or {}
            raw_text = read_artifact_text(raw_markdown)
            refined_text = read_artifact_text(refined_markdown)
            note_text = read_artifact_text(note_markdown)
            note_job = compact_job(note) if refine_job["status"] == "succeeded" else {}
            postprocessed_figure_count = int(
                parse_artifacts.get("postprocessed_figure_count") or 0
            )
            postprocessed_figure_file_count = count_files(
                str(parse_artifacts.get("postprocessed_figure_dir") or "")
            )

            checks = {
                "download_job_succeeded": download_job["status"] == "succeeded",
                "download_used_real_network": (
                    (download_job.get("result") or {}).get("download_mode") == "gpaper"
                ),
                "source_pdf_registered": "source_pdf" in artifact_keys,
                "source_pdf_size_gt_50kb": int(source_pdf.get("file_size") or 0)
                > 50_000,
                "parse_job_succeeded": parse_job["status"] == "succeeded",
                "parse_used_mineru": (
                    (parse_job.get("result") or {}).get("parse_mode") == "mineru"
                ),
                "parse_figures_registered": "parse_figures" in artifact_keys,
                "postprocessed_figure_count_gt_0": postprocessed_figure_count > 0,
                "postprocessed_figure_files_exist": postprocessed_figure_file_count > 0,
                "raw_markdown_registered": "raw_markdown" in artifact_keys,
                "raw_markdown_size_gt_1000": int(raw_markdown.get("file_size") or 0)
                > 1_000,
                "raw_markdown_uses_postprocessed_figures": "(images/" in raw_text,
                "raw_markdown_does_not_embed_raw_images": "![](mineru/images/" not in raw_text,
                "refine_job_succeeded": refine_job["status"] == "succeeded",
                "refined_markdown_registered": "refined_markdown" in artifact_keys,
                "refined_markdown_size_gt_1000": int(refined_markdown.get("file_size") or 0)
                > 1_000,
                "refined_markdown_uses_postprocessed_figures": "(images/" in refined_text,
                "refined_markdown_uses_blockquoted_captions": "> **图注**：" in refined_text,
                "refine_deterministic_artifact_registered": (
                    "refine_deterministic_normalization" in artifact_keys
                ),
                "refine_deterministic_operation_applied": int(
                    refine_result.get("deterministic_operation_count") or 0
                )
                > 0,
                "pipeline_runs_recorded": set(run_stages).issuperset(
                    {"download", "parse", "refine"}
                ),
            }
            if refine_job["status"] == "succeeded":
                checks.update(
                    {
                        "sections_registered": {
                            "section_introduction",
                            "section_related_work",
                            "section_method",
                            "section_experiment",
                            "section_conclusion",
                            "section_appendix",
                        }.issubset(set(artifact_keys)),
                        "note_registered": "note_markdown" in artifact_keys,
                        "note_source_uses_llm": (
                            (note_job.get("result") or {}).get("summary_source")
                            in {"llm", "llm_partial"}
                        ),
                        "note_has_no_block_failures": not (
                            (note_job.get("result") or {}).get("block_failures") or []
                        ),
                        "note_markdown_size_gt_20kb": int(note_markdown.get("file_size") or 0)
                        > 20_000,
                        "note_embeds_postprocessed_figures": "(parsed/images/" in note_text
                        or "(images/" in note_text,
                        "note_uses_blockquoted_captions": "> **图注**：" in note_text,
                        "note_method_starts_with_overview": (
                            "\n## 方法\n" in note_text
                            and "### 方法总览" in note_text.split("\n## 方法\n", 1)[1]
                        ),
                        "note_uses_prompt_defined_sections": all(
                            heading in note_text
                            for heading in (
                                "## 摘要信息",
                                "## 术语",
                                "## 背景动机",
                                "## 方法",
                                "## 实验/结果",
                                "## 结论局限",
                            )
                        )
                        and "## 关键图表与视觉证据" not in note_text
                        and "## 局限性与注意事项" not in note_text,
                        "section_split_report_registered": (
                            "section_split_report" in artifact_keys
                        ),
                        "summarize_run_recorded": "summarize" in run_stages,
                    }
                )
            report["summary"] = {
                "paper_id": paper_id,
                "paper_stage": paper["payload"]["data"]["paper_stage"],
                "download": download_job,
                "parse": parse_job,
                "refine": refine_job,
                "note": note_job,
                "artifact_keys": artifact_keys,
                "run_stages": run_stages,
            }
            report["checks"] = checks
            if not all(checks.values()):
                exit_code = 2
    except Exception as exc:  # noqa: BLE001 - report real external failures
        report["exception"] = {"type": type(exc).__name__, "message": str(exc)}
        exit_code = 1
    finally:
        report["finished_at"] = datetime.now(UTC).isoformat()
        report_path = write_report(report)
        report["report_path"] = str(report_path)
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        reset_settings()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
