from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from core.config import reset_settings  # noqa: E402
from core.services.llm import llm_registry  # noqa: E402
from core.services.llm.schemas import LLMMessage, LLMRequest  # noqa: E402
from core.services.papers.refine.parsing import extract_json_object  # noqa: E402
from core.services.papers.skill_runtime import (  # noqa: E402
    load_skill_runtime_instructions,
    render_skill_instructions,
)


SECTION_FILES: tuple[tuple[str, str, str, int], ...] = (
    ("experiment", "Experiment", "04_experiment.md", 4000),
    ("related_work", "Related Work", "02_related_work.md", 2400),
    ("introduction", "Introduction", "01_introduction.md", 1600),
)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig").strip()


def _compact(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    lines: list[str] = []
    total = 0
    for line in text.splitlines():
        next_total = total + len(line) + 1
        if next_total > limit:
            break
        lines.append(line)
        total = next_total
    return "\n".join(lines).rstrip() + "\n\n[context truncated]"


def _section_context(sections_dir: Path) -> str:
    parts: list[str] = []
    for section_key, title, filename, budget in SECTION_FILES:
        path = sections_dir / filename
        if not path.exists():
            continue
        content = _compact(_read_text(path), budget)
        if content:
            parts.append(f"## {title} ({section_key})\n{content}")
    return "\n\n".join(parts)


def _validate(payload: dict[str, Any]) -> dict[str, Any]:
    items = payload.get("items")
    if not isinstance(items, list):
        items = []
    missing_required: list[dict[str, Any]] = []
    required = {"dataset_name", "source_section", "evidence_text", "confidence_score"}
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            missing_required.append({"index": index, "missing": sorted(required)})
            continue
        missing = sorted(key for key in required if key not in item)
        if missing:
            missing_required.append({"index": index, "missing": missing})
    return {
        "item_count": len(items),
        "missing_required": missing_required,
    }


async def _run(args: argparse.Namespace) -> dict[str, Any]:
    case = args.case
    sources_root = Path(args.sources_root)
    sections_dir = Path(args.sections_dir) if args.sections_dir else sources_root / "02-paper-sectioning" / case / "sections"
    metadata_path = Path(args.metadata_json) if args.metadata_json else sources_root / "03-paper-note-generate" / case / "metadata.json"
    source_dir = Path(args.source_dir) if args.source_dir else sources_root / "05-paper-dataset-mining" / case
    output_root = Path(args.output_root)
    run_dir = Path(args.output_dir) if args.output_dir else _next_run_dir(case, output_root)
    run_dir.mkdir(parents=True, exist_ok=False)

    metadata_json = json.dumps(json.loads(metadata_path.read_text(encoding="utf-8-sig")), ensure_ascii=False, indent=2)
    section_context = _section_context(sections_dir)
    prompt = render_skill_instructions(
        load_skill_runtime_instructions(args.instruction_key),
        {
            "metadata_json": metadata_json,
            "section_context": section_context,
        },
    )
    prompt_path = run_dir / "prompt.md"
    prompt_path.write_text(prompt, encoding="utf-8")

    response = await llm_registry.generate(
        LLMRequest(
            feature=args.feature,
            messages=[LLMMessage(role="user", content=prompt)],
            max_tokens=args.max_tokens,
            max_completion_tokens=args.max_tokens,
            extra={"response_format": {"type": "json_object"}},
        )
    )
    raw_response = {
        "model_key": response.model_key,
        "provider": response.provider,
        "model": response.model,
        "content": response.message.content,
    }
    raw_response_path = run_dir / "raw_response.json"
    raw_response_path.write_text(json.dumps(raw_response, ensure_ascii=False, indent=2), encoding="utf-8")

    payload = extract_json_object(response.message.content)
    datasets_path = run_dir / "datasets.json"
    datasets_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    metadata_out = run_dir / "metadata.json"
    metadata_out.write_text(metadata_json, encoding="utf-8")
    section_context_path = run_dir / "section_context.md"
    section_context_path.write_text(section_context, encoding="utf-8")

    validation = _validate(payload)
    validation_path = run_dir / "validation.json"
    validation_path.write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = {
        "source": "llm",
        "instruction_key": args.instruction_key,
        "feature": args.feature,
        "provider": response.provider,
        "model_key": response.model_key,
        "item_count": validation["item_count"],
        "output_path": str(datasets_path),
        "prompt_path": str(prompt_path),
        "section_context_char_count": len(section_context),
        "llm_called": True,
    }
    summary_path = run_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    run_summary = {
        "case": case,
        "sections_dir": str(sections_dir),
        "metadata_path": str(metadata_path),
        "dataset_mining": summary,
        "dataset_validation": validation,
        "dataset_run_dir": str(run_dir),
        "dataset_source_dir": str(source_dir),
        "source_sync": {
            "enabled": args.sync_source,
            "synced": False,
            "source_dir": str(source_dir),
        },
    }
    run_summary_path = run_dir / "run_summary.json"
    run_summary_path.write_text(json.dumps(run_summary, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.sync_source:
        source_dir.mkdir(parents=True, exist_ok=True)
        for filename in (
            "datasets.json",
            "metadata.json",
            "prompt.md",
            "raw_response.json",
            "section_context.md",
            "summary.json",
            "validation.json",
        ):
            (source_dir / filename).write_bytes((run_dir / filename).read_bytes())
        (source_dir / "run_summary.json").write_text(
            json.dumps(
                {
                    **run_summary,
                    "source_sync": {
                        "enabled": True,
                        "synced": True,
                        "source_dir": str(source_dir),
                    },
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    return run_summary


def _next_run_dir(case: str, output_root: Path) -> Path:
    case_root = output_root / case
    if not case_root.exists():
        return case_root / "001"
    existing = [int(path.name) for path in case_root.iterdir() if path.is_dir() and path.name.isdigit()]
    return case_root / f"{(max(existing) + 1) if existing else 1:03d}"


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Run paper-dataset-mining on skill-lab sources.")
    parser.add_argument("--case", required=True)
    parser.add_argument("--sources-root", default=str(REPO_ROOT / "skill-lab" / "sources"))
    parser.add_argument("--sections-dir")
    parser.add_argument("--metadata-json")
    parser.add_argument("--source-dir")
    parser.add_argument("--output-root", default=str(REPO_ROOT / "skill-lab" / "runs" / "paper-dataset-mining"))
    parser.add_argument("--output-dir")
    parser.add_argument("--instruction-key", default="paper_dataset_mining.default")
    parser.add_argument("--feature", default="default_chat")
    parser.add_argument("--max-tokens", type=int, default=5000)
    parser.add_argument("--no-sync-source", dest="sync_source", action="store_false")
    parser.set_defaults(sync_source=True)
    args = parser.parse_args()
    reset_settings()
    print(json.dumps(asyncio.run(_run(args)), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
