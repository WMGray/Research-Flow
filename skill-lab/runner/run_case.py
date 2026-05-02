from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from core.config import reset_settings  # noqa: E402
from core.services.llm import llm_registry  # noqa: E402
from core.services.llm.schemas import LLMMessage, LLMRequest  # noqa: E402
from core.services.papers.skill_runtime import (  # noqa: E402
    load_skill_runtime_instructions,
    render_skill_instructions,
)


def _load_case_values(case_path: Path) -> tuple[dict[str, str], list[str]]:
    """Load a lab case and expand file-backed source fixtures into prompt fields."""
    raw_values = json.loads(case_path.read_text(encoding="utf-8"))
    source_specs = raw_values.pop("source_files", [])
    values = {
        key: value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2)
        for key, value in raw_values.items()
    }
    sources: list[str] = []

    # Keep large paper excerpts outside case JSON so each skill can reuse stable source fixtures.
    for spec in source_specs:
        field = spec["field"]
        source_path = (case_path.parent / spec["path"]).resolve()
        if not source_path.is_file():
            raise FileNotFoundError(f"Source fixture not found: {source_path}")
        values[field] = source_path.read_text(encoding="utf-8-sig")
        sources.append(str(source_path))

    return values, sources


async def run_case(args: argparse.Namespace) -> dict[str, object]:
    case_path = Path(args.case).resolve()
    values, sources = _load_case_values(case_path)
    instructions = load_skill_runtime_instructions(args.instruction_key)
    prompt = render_skill_instructions(instructions, values)
    if args.dry_run:
        return {
            "case": str(case_path),
            "instruction_key": args.instruction_key,
            "feature": args.feature,
            "sources": sources,
            "prompt": prompt,
        }

    # The runner intentionally reuses backend/config/settings.toml feature routing.
    # Skill Lab edits stay local, while provider/model behavior remains production-like.
    response = await llm_registry.generate(
        LLMRequest(
            feature=args.feature,
            messages=[LLMMessage(role="user", content=prompt)],
            max_tokens=args.max_tokens,
            extra={"response_format": {"type": "json_object"}},
        )
    )
    return {
        "case": str(case_path),
        "instruction_key": args.instruction_key,
        "feature": args.feature,
        "sources": sources,
        "model_key": response.model_key,
        "provider": response.provider,
        "content": response.message.content,
    }


def main() -> int:
    # Windows PowerShell may default to GBK; force UTF-8 so paper text can be printed safely.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Run one skill-lab case with backend LLM provider.")
    parser.add_argument("--case", required=True, help="Path to case JSON.")
    parser.add_argument("--instruction-key", required=True, help="Runtime instruction key.")
    parser.add_argument("--feature", required=True, help="LLM feature from backend/config/settings.toml.")
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--out", help="Optional output JSON path.")
    parser.add_argument("--dry-run", action="store_true", help="Render the prompt without calling LLM.")
    args = parser.parse_args()

    reset_settings()
    result = asyncio.run(run_case(args))
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
