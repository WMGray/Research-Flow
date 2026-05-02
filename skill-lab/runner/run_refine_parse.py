from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import shutil
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from core.config import reset_settings  # noqa: E402
from core.services.papers.refine import refine_markdown  # noqa: E402


def _load_metadata(path: str | None) -> dict[str, object]:
    if path is None:
        return {}
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def _copy_to_source(output_path: Path, source_output: str | None) -> None:
    if source_output is None:
        return
    source_output_path = Path(source_output)
    source_output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(output_path, source_output_path)


def main() -> int:
    # Keep this runner thin: the backend runtime owns skill loading, LLM routing,
    # patch application, deterministic normalization, and verification artifacts.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Run the paper-refine-parse skill on a raw Markdown file.")
    parser.add_argument("--input", required=True, help="Source raw.md path.")
    parser.add_argument("--output", required=True, help="Target refined.md path.")
    parser.add_argument(
        "--source-output",
        help="Optional source fixture path to receive the final refined.md for downstream skill cases.",
    )
    parser.add_argument("--metadata-json", help="Optional JSON metadata used only for safe metadata repair.")
    parser.add_argument("--instruction", default="Keep citations, formulas, figures, captions, tables, and paper facts intact.")
    args = parser.parse_args()

    reset_settings()
    result = refine_markdown(
        markdown_path=Path(args.input),
        output_path=Path(args.output),
        skill_key="paper_refine_parse",
        instruction=args.instruction,
        metadata=_load_metadata(args.metadata_json),
    )
    if result.refined:
        _copy_to_source(Path(args.output), args.source_output)
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2, default=str))
    return 0 if result.refined else 1


if __name__ == "__main__":
    raise SystemExit(main())
