from __future__ import annotations

import argparse
import asyncio
from dataclasses import asdict, is_dataclass
import json
from pathlib import Path
import sys
from typing import Any


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from core.config import get_settings
from app.schemas.paper_download import PaperDownloadRequest
from core.services.papers.download import PaperDownloadService
from core.services.papers.parse import PDFParserService


# Default: run full pipeline. Use --download-only to skip parsing.
RUN_PARSE_PIPELINE = True

# Add one dict per paper. Each dict must contain exactly one of source_url / doi / title.
PAPER_QUERIES: list[dict[str, str]] = [
    {"source_url": "https://arxiv.org/abs/1706.03762"},
]

OUTPUT_DIR = Path("data/papers/service_smoke")
OVERWRITE = True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manual smoke test for paper download / parse services.")
    parser.add_argument(
        "--download-only",
        action="store_true",
        help="Only test download service and skip PDF parsing.",
    )
    return parser.parse_args()


def validate_paper_query(query: dict[str, str], index: int) -> dict[str, str]:
    allowed_keys = {"source_url", "doi", "title"}
    unknown_keys = set(query) - allowed_keys
    if unknown_keys:
        raise ValueError(
            f"Only source_url / doi / title are allowed in PAPER_QUERIES[{index}], got: {sorted(unknown_keys)}"
        )

    provided = {key: value for key, value in query.items() if value}
    if len(provided) != 1:
        raise ValueError(
            f"PAPER_QUERIES[{index}] must provide exactly one of source_url / doi / title, got: {sorted(provided)}"
        )
    return provided


def indexed_output_dir(base_output_dir: Path, index: int) -> Path:
    return base_output_dir / f"{index + 1:02d}"


def to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def resolve_backend_path(path_value: str) -> Path:
    path = Path(path_value)
    return path if path.is_absolute() else BACKEND_ROOT / path


async def parse_pdf(pdf_path: Path) -> dict[str, Any]:
    progress_events: list[dict[str, str]] = []

    async def progress_callback(step: str, message: str) -> None:
        progress_events.append({"step": step, "message": message})
        print(f"[{step}] {message}")

    parsed = await PDFParserService(get_settings()).parse_pdf(
        pdf_path,
        progress_callback=progress_callback,
    )
    section_files = []
    if parsed.artifact_section_dir and parsed.artifact_section_dir.exists():
        section_files = sorted(path.name for path in parsed.artifact_section_dir.iterdir() if path.is_file())

    return {
        "char_count": parsed.char_count,
        "page_count": parsed.page_count,
        "excerpt": parsed.excerpt,
        "sections": parsed.section_outline(),
        "section_files": section_files,
        "artifact_markdown_path": str(parsed.artifact_markdown_path) if parsed.artifact_markdown_path else "",
        "artifact_image_dir": str(parsed.artifact_image_dir) if parsed.artifact_image_dir else "",
        "artifact_section_dir": str(parsed.artifact_section_dir) if parsed.artifact_section_dir else "",
        "progress_events": progress_events,
    }


async def run_case(query: dict[str, str], index: int) -> dict[str, Any]:
    selected_query = validate_paper_query(query, index)
    case_output_dir = indexed_output_dir(OUTPUT_DIR, index)
    request_payload = {
        **selected_query,
        "output_dir": str(case_output_dir),
        "overwrite": OVERWRITE,
    }
    request = PaperDownloadRequest.model_validate(request_payload)
    row, download_result = PaperDownloadService().download(request)

    summary: dict[str, Any] = {
        "case_index": index,
        "query": selected_query,
        "output_dir": str((BACKEND_ROOT / case_output_dir).resolve()),
        "resolution": to_jsonable(row),
        "download": to_jsonable(download_result),
        "parse": None,
    }

    file_path_value = str(download_result.get("file_path") or "")
    if not file_path_value:
        return summary

    pdf_path = resolve_backend_path(file_path_value)
    summary["file_exists"] = pdf_path.exists()
    if RUN_PARSE_PIPELINE and pdf_path.exists():
        summary["parse"] = await parse_pdf(pdf_path)
    return summary


async def main_async(run_parse_pipeline: bool) -> int:
    print(f"RUN_PARSE_PIPELINE={run_parse_pipeline}")
    summaries = []
    for index, query in enumerate(PAPER_QUERIES):
        summaries.append(await run_case(query, index) if run_parse_pipeline else await run_case_download_only(query, index))

    print(json.dumps(summaries, ensure_ascii=False, indent=2))
    if run_parse_pipeline:
        return 0 if all(summary.get("parse") is not None for summary in summaries) else 1
    return 0 if all(summary.get("file_exists") for summary in summaries) else 1


async def run_case_download_only(query: dict[str, str], index: int) -> dict[str, Any]:
    selected_query = validate_paper_query(query, index)
    case_output_dir = indexed_output_dir(OUTPUT_DIR, index)
    request_payload = {
        **selected_query,
        "output_dir": str(case_output_dir),
        "overwrite": OVERWRITE,
    }
    request = PaperDownloadRequest.model_validate(request_payload)
    row, download_result = PaperDownloadService().download(request)

    summary: dict[str, Any] = {
        "case_index": index,
        "query": selected_query,
        "output_dir": str((BACKEND_ROOT / case_output_dir).resolve()),
        "resolution": to_jsonable(row),
        "download": to_jsonable(download_result),
        "parse": None,
    }

    file_path_value = str(download_result.get("file_path") or "")
    if not file_path_value:
        return summary

    pdf_path = resolve_backend_path(file_path_value)
    summary["file_exists"] = pdf_path.exists()
    return summary


def main() -> int:
    args = parse_args()
    return asyncio.run(main_async(run_parse_pipeline=not args.download_only))


if __name__ == "__main__":
    raise SystemExit(main())
