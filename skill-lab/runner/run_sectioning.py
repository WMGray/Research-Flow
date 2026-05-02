from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from core.config import reset_settings  # noqa: E402
from core.services.papers.split import (  # noqa: E402
    CANONICAL_SECTION_ORDER,
    section_filename,
    split_canonical_sections,
)


def _write_sections(input_path: Path, output_dir: Path) -> dict[str, object]:
    """Run the backend sectioning runtime and write reviewable section artifacts."""
    content = input_path.read_text(encoding="utf-8-sig")
    result = split_canonical_sections(content)
    output_dir.mkdir(parents=True, exist_ok=True)
    image_summary = _sync_images(input_path, output_dir)

    section_records: list[dict[str, object]] = []
    for section_key, title in CANONICAL_SECTION_ORDER:
        file_name = section_filename(section_key)
        section_content = result.blocks.get(section_key, "")
        section_content = _rewrite_section_image_links(section_content)
        output_path = output_dir / file_name
        rendered_content = section_content.rstrip()
        if rendered_content:
            rendered_content += "\n"
        output_path.write_text(rendered_content, encoding="utf-8")
        section_records.append(
            {
                "section_key": section_key,
                "title": title,
                "path": str(output_path),
                "char_count": len(rendered_content),
                "generated": bool(rendered_content.strip()),
            }
        )

    report_path = output_dir / "split_report.json"
    report_path.write_text(
        json.dumps(result.report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return {
        "input": str(input_path),
        "output_dir": str(output_dir),
        "report_path": str(report_path),
        "sections": section_records,
        "strategy": result.report.get("strategy"),
        "used_llm": result.report.get("used_llm"),
        "images": image_summary,
    }


def _sync_images(input_path: Path, output_dir: Path) -> dict[str, object]:
    """Copy source images beside section outputs so section Markdown can render."""
    source_dir = input_path.parent / "images"
    target_dir = output_dir.parent / "images"
    if not source_dir.exists():
        return {"copied": False, "source_dir": str(source_dir), "target_dir": str(target_dir), "count": 0}
    shutil.copytree(source_dir, target_dir, dirs_exist_ok=True)
    return {
        "copied": True,
        "source_dir": str(source_dir),
        "target_dir": str(target_dir),
        "count": sum(1 for path in target_dir.iterdir() if path.is_file()),
    }


def _rewrite_section_image_links(markdown_text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        alt = match.group("alt")
        target = match.group("target").strip()
        normalized_target = target[2:] if target.startswith("./") else target
        if normalized_target.startswith(("images/", "figures/")):
            target = f"../{normalized_target}"
        return f"![{alt}]({target})"

    return re.sub(r"!\[(?P<alt>[^\]]*)]\((?P<target>[^)\s]+)\)", replace, markdown_text)


def main() -> int:
    # Keep this runner thin: backend code owns skill loading, LLM routing,
    # range validation, deterministic fallback, and canonical file naming.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Run the paper-sectioning skill on a refined Markdown file.")
    parser.add_argument("--input", required=True, help="Source refined.md path.")
    parser.add_argument(
        "--output-dir",
        help="Target section output directory. Defaults to <input-dir>/sections.",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output_dir) if args.output_dir else input_path.parent / "sections"

    reset_settings()
    summary = _write_sections(input_path, output_dir)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
