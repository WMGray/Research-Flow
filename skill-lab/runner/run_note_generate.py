from __future__ import annotations

import argparse
import asyncio
from dataclasses import asdict
import json
from pathlib import Path
import re
import shutil
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from core.config import reset_settings  # noqa: E402
from core.services.llm import llm_registry  # noqa: E402
from core.services.llm.schemas import LLMRequest, LLMResponse  # noqa: E402
from core.services.papers.models import PaperRecord, utc_now  # noqa: E402
from core.services.papers.note import collect_figure_evidence, render_note_markdown  # noqa: E402
from core.services.papers.note.blocks import generate_detailed_note_blocks  # noqa: E402
from core.services.papers.note.runtime import (  # noqa: E402
    DEFAULT_NOTE_BLOCK_FEATURE,
    DEFAULT_NOTE_BLOCK_INSTRUCTION_KEY,
)


SECTION_FILES: tuple[tuple[str, str, str], ...] = (
    ("introduction", "Introduction", "01_introduction.md"),
    ("related_work", "Related Work", "02_related_work.md"),
    ("method", "Method", "03_method.md"),
    ("experiment", "Experiment", "04_experiment.md"),
    ("conclusion", "Conclusion", "05_conclusion.md"),
    ("appendix", "Appendix", "06_appendix.md"),
)


class RecordingLLMClient:
    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []

    async def generate(self, request: LLMRequest) -> LLMResponse:
        response = await llm_registry.generate(request)
        block_id = _extract_block_id(request)
        self.records.append(
            {
                "block_id": block_id,
                "feature": request.feature,
                "model_key": response.model_key,
                "provider": response.provider,
                "model": response.model,
                "content": response.message.content,
                "usage": _model_dump(response.usage),
            }
        )
        return response


def _model_dump(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value


def _extract_block_id(request: LLMRequest) -> str:
    if not request.messages:
        return ""
    prompt = request.messages[-1].content
    match = re.search(r"generating only the `([^`]+)` managed block", prompt)
    if match:
        return match.group(1)
    match = re.search(r"当前只生成 note\.md 的 `([^`]+)` block", prompt)
    return match.group(1) if match else ""


def _next_run_dir(case: str, output_root: Path) -> Path:
    case_root = output_root / case
    if not case_root.exists():
        return case_root / "001"
    existing = [
        int(path.name)
        for path in case_root.iterdir()
        if path.is_dir() and path.name.isdigit()
    ]
    return case_root / f"{(max(existing) + 1) if existing else 1:03d}"


def _load_metadata(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _paper_from_metadata(metadata: dict[str, Any]) -> PaperRecord:
    now = utc_now()
    return PaperRecord(
        paper_id=0,
        asset_id=0,
        title=str(metadata.get("title") or "Untitled Paper"),
        authors=[str(author) for author in metadata.get("authors") or []],
        year=metadata.get("year"),
        venue=str(metadata.get("venue") or ""),
        venue_short=str(metadata.get("venue_short") or metadata.get("venue") or ""),
        doi=str(metadata.get("doi") or ""),
        source_url=str(metadata.get("source_url") or ""),
        pdf_url=str(metadata.get("pdf_url") or ""),
        category_id=None,
        tags=[],
        paper_stage="sectioned",
        download_status="succeeded",
        parse_status="succeeded",
        refine_status="succeeded",
        review_status="confirmed",
        note_status="empty",
        assets={},
        created_at=now,
        updated_at=now,
    )


def _load_sections(sections_dir: Path) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    for section_key, fallback_title, filename in SECTION_FILES:
        path = sections_dir / filename
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8-sig").strip()
        if not content:
            continue
        sections.append(
            {
                "section_key": section_key,
                "title": _first_heading(content) or fallback_title,
                "content": content,
                "path": str(path),
            }
        )
    if not sections:
        raise FileNotFoundError(f"No section markdown files found in {sections_dir}")
    return sections


def _first_heading(content: str) -> str:
    for line in content.splitlines():
        match = re.match(r"^\s*#{1,6}\s+(.+?)\s*$", line)
        if match:
            return match.group(1).strip()
    return ""


def _image_base_dirs(sections_dir: Path) -> list[Path]:
    return [
        sections_dir,
        sections_dir.parent,
        sections_dir.parent / "images",
    ]


def _validate_note(note_path: Path) -> dict[str, Any]:
    content = note_path.read_text(encoding="utf-8")
    block_ids = re.findall(r'<!-- RF:BLOCK_START id="([^"]+)" managed="true"', content)
    top_headings = re.findall(r"(?m)^##\s+(.+?)\s*$", content)
    return {
        "note_path": str(note_path),
        "block_count": len(block_ids),
        "blocks": block_ids,
        "top_headings": top_headings,
        "expected_top_headings_present": all(
            heading in top_headings
            for heading in ["摘要信息", "术语", "背景动机", "方法", "实验/结果", "结论局限"]
        ),
        "has_method_overview_in_method": "## 方法" in content and "### 方法总览" in content,
        "method_overview_heading_count": content.count("### 方法总览"),
        "image_markdown_count": len(re.findall(r"!\[[^\]]*]\([^)]+\)", content)),
        "caution_count": content.count(">[!Caution]"),
        "deprecated_headings": [
            heading
            for heading in top_headings
            if heading in {"文章摘要", "缩写与术语解释", "实验设置", "实验结果", "本文方法"}
        ],
    }


def _sync_source_outputs(*, run_dir: Path, source_dir: Path) -> dict[str, Any]:
    source_dir.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for filename in (
        "note.md",
        "metadata.json",
        "block_raw_responses.json",
        "summary.json",
        "validation.json",
    ):
        source_path = run_dir / filename
        if not source_path.exists():
            continue
        target_path = source_dir / filename
        shutil.copy2(source_path, target_path)
        copied.append(str(target_path))
    return {
        "enabled": True,
        "synced": True,
        "source_dir": str(source_dir),
        "copied": copied,
    }


async def _generate(args: argparse.Namespace) -> dict[str, Any]:
    case = args.case
    sources_root = Path(args.sources_root)
    sections_dir = (
        Path(args.sections_dir)
        if args.sections_dir
        else sources_root / "02-paper-sectioning" / case / "sections"
    )
    metadata_path = (
        Path(args.metadata_json)
        if args.metadata_json
        else sources_root / "03-paper-note-generate" / case / "metadata.json"
    )
    note_source_dir = Path(args.note_source_dir) if args.note_source_dir else metadata_path.parent
    output_root = Path(args.output_root)
    run_dir = Path(args.output_dir) if args.output_dir else _next_run_dir(case, output_root)
    run_dir.mkdir(parents=True, exist_ok=False)

    paper = _paper_from_metadata(_load_metadata(metadata_path))
    sections = _load_sections(sections_dir)
    note_path = run_dir / "note.md"
    figures = collect_figure_evidence(
        sections,
        note_path=note_path,
        image_base_dirs=_image_base_dirs(sections_dir),
    )

    client = RecordingLLMClient()
    blocks, block_failures = await generate_detailed_note_blocks(
        paper=paper,
        sections=sections,
        figures=figures,
        llm_client=client,
        instruction_key=args.instruction_key,
        feature=args.feature,
    )
    note_content = render_note_markdown(title=paper.title, blocks=blocks)
    note_path.write_text(note_content, encoding="utf-8")
    shutil.copy2(metadata_path, run_dir / "metadata.json")

    raw_responses_path = run_dir / "block_raw_responses.json"
    raw_responses_path.write_text(
        json.dumps(client.records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    validation = _validate_note(note_path)
    validation_path = run_dir / "validation.json"
    validation_path.write_text(
        json.dumps(validation, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    failed_block_ids = {failure.split(":", 1)[0] for failure in block_failures}
    parse_modes = {
        record.get("block_id") or f"response_{index + 1}": (
            "failed" if record.get("block_id") in failed_block_ids else "json"
        )
        for index, record in enumerate(client.records)
    }
    summary = {
        "mode": "llm",
        "source": "llm" if not block_failures else "llm_partial",
        "instruction_key": args.instruction_key,
        "feature": args.feature,
        "block_count": len(blocks),
        "figure_count": len(figures),
        "block_failures": list(block_failures),
        "parse_modes": parse_modes,
        "output_path": str(note_path),
        "char_count": len(note_content),
    }
    summary_path = run_dir / "summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    run_summary = {
        "case": case,
        "sections_dir": str(sections_dir),
        "metadata_path": str(metadata_path),
        "note": summary,
        "note_validation": validation,
        "note_run_dir": str(run_dir),
        "raw_responses_path": str(raw_responses_path),
        "note_source_dir": str(note_source_dir),
        "source_sync": {
            "enabled": args.sync_source,
            "synced": False,
            "source_dir": str(note_source_dir),
            "reason": "pending",
        },
    }
    if args.sync_source and not block_failures:
        run_summary["source_sync"] = _sync_source_outputs(
            run_dir=run_dir,
            source_dir=note_source_dir,
        )
        run_summary["source_sync"]["copied"].append(str(note_source_dir / "run_summary.json"))
    elif args.sync_source:
        run_summary["source_sync"] = {
            "enabled": True,
            "synced": False,
            "source_dir": str(note_source_dir),
            "reason": "block_failures_present",
        }
    run_summary_path = run_dir / "run_summary.json"
    run_summary_path.write_text(
        json.dumps(run_summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if args.sync_source and not block_failures:
        shutil.copy2(run_summary_path, note_source_dir / "run_summary.json")
    if args.source_output:
        source_output = Path(args.source_output)
        source_output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(run_summary_path, source_output)
    return run_summary


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="Run paper-note-generate on skill-lab section sources."
    )
    parser.add_argument("--case", required=True, help="Source case name.")
    parser.add_argument(
        "--sources-root",
        default=str(REPO_ROOT / "skill-lab" / "sources"),
        help="Skill-lab sources root.",
    )
    parser.add_argument("--sections-dir", help="Override section source directory.")
    parser.add_argument("--metadata-json", help="Override note metadata JSON path.")
    parser.add_argument("--note-source-dir", help="Override note source sync directory.")
    parser.add_argument(
        "--output-root",
        default=str(REPO_ROOT / "skill-lab" / "runs" / "paper-note-generate"),
        help="Run output root.",
    )
    parser.add_argument("--output-dir", help="Exact output directory; must not exist.")
    parser.add_argument(
        "--instruction-key",
        default=DEFAULT_NOTE_BLOCK_INSTRUCTION_KEY,
        help="Runtime instruction key.",
    )
    parser.add_argument("--feature", default=DEFAULT_NOTE_BLOCK_FEATURE, help="LLM feature.")
    parser.add_argument(
        "--source-output",
        help="Optional path to receive a copy of run_summary.json.",
    )
    parser.add_argument(
        "--no-sync-source",
        dest="sync_source",
        action="store_false",
        help="Do not sync successful outputs back to skill-lab sources.",
    )
    parser.set_defaults(sync_source=True)
    args = parser.parse_args()

    reset_settings()
    summary = asyncio.run(_generate(args))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
