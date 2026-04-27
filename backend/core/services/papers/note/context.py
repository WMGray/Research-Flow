from __future__ import annotations

import re
from typing import Any


HEADING_RE = re.compile(r"^\s*#{1,6}\s+")
IMAGE_RE = re.compile(r"^\s*!\[[^\]]*]\([^)]+\)")
CAPTION_RE = re.compile(r"^\s*>\s*\*\*图注\*\*：")
CAUTION_RE = re.compile(r"^\s*>\[!Caution]", re.IGNORECASE)
TABLE_RE = re.compile(r"^\s*\|")
FORMULA_RE = re.compile(r"(\$\$|\\begin\{|\\end\{|equation_inline|equation block)", re.IGNORECASE)
CONTEXT_CHAR_LIMITS: dict[str, int] = {
    "paper_overview": 18_000,
    "terminology_guide": 22_000,
    "background_motivation": 24_000,
    "experimental_setup": 28_000,
    "method": 30_000,
    "experimental_results": 32_000,
}
BLOCK_KEYWORDS: dict[str, tuple[str, ...]] = {
    "paper_overview": (
        "abstract",
        "introduction",
        "contribution",
        "we propose",
        "we present",
        "result",
    ),
    "terminology_guide": (
        "task",
        "model",
        "architecture",
        "feature",
        "metric",
        "baseline",
        "dataset",
        "rank",
        "adapter",
        "prompt",
    ),
    "background_motivation": (
        "introduction",
        "related",
        "motivation",
        "challenge",
        "problem",
        "prior",
        "existing",
        "fine-tuning",
    ),
    "experimental_setup": (
        "dataset",
        "benchmark",
        "baseline",
        "training",
        "train",
        "learning rate",
        "batch",
        "epoch",
        "optimizer",
        "hyperparameter",
        "implementation",
        "evaluate",
        "evaluation",
        "roberta",
        "deberta",
        "gpt",
        "mnli",
        "sst",
        "cola",
        "qnli",
        "qqp",
        "rte",
        "sts-b",
        "wikisql",
        "samsum",
        "e2e",
        "dart",
    ),
    "method": (
        "method",
        "approach",
        "architecture",
        "matrix",
        "rank",
        "adapter",
        "transformer",
        "formula",
        "equation",
        "module",
    ),
    "experimental_results": (
        "result",
        "performance",
        "outperform",
        "ablation",
        "accuracy",
        "score",
        "comparison",
        "baseline",
        "rank",
        "validation",
        "gpt",
        "roberta",
        "deberta",
        "appendix",
        "limitation",
        "future",
        "latency",
        "memory",
        "fail",
        "constraint",
        "overhead",
        "discussion",
    ),
}


def build_block_section_context(block_id: str, sections: list[dict[str, Any]]) -> str:
    full_context = "\n\n".join(
        f"## {section['title']}\n{str(section['content']).strip()}"
        for section in sections
    )
    limit = CONTEXT_CHAR_LIMITS.get(block_id, 24_000)
    if len(full_context) <= limit:
        return full_context

    section_limit = max(4_000, limit // max(len(sections), 1))
    return "\n\n".join(
        f"## {section['title']}\n{_compact_section_content(block_id, str(section['content']), section_limit)}"
        for section in sections
    )


def _compact_section_content(block_id: str, content: str, limit: int) -> str:
    lines = content.splitlines()
    if len(content) <= limit:
        return content.strip()

    keep: set[int] = set(range(min(24, len(lines))))
    for index, line in enumerate(lines):
        if _is_high_value_line(block_id, line):
            _add_window(keep, index, len(lines), before=1, after=3)
        elif HEADING_RE.match(line):
            _add_window(keep, index, len(lines), before=0, after=4)

    rendered = _render_kept_lines(lines, keep)
    if len(rendered) <= limit:
        return rendered
    return rendered[:limit].rstrip() + "\n\n[context truncated for model budget]"


def _is_high_value_line(block_id: str, line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if (
        HEADING_RE.match(stripped)
        or IMAGE_RE.match(stripped)
        or CAPTION_RE.match(stripped)
        or CAUTION_RE.match(stripped)
        or TABLE_RE.match(stripped)
        or FORMULA_RE.search(stripped)
    ):
        return True
    lowered = stripped.lower()
    keywords = BLOCK_KEYWORDS.get(block_id, ())
    return any(keyword in lowered for keyword in keywords)


def _add_window(
    keep: set[int],
    index: int,
    line_count: int,
    *,
    before: int,
    after: int,
) -> None:
    start = max(0, index - before)
    end = min(line_count, index + after + 1)
    keep.update(range(start, end))


def _render_kept_lines(lines: list[str], keep: set[int]) -> str:
    rendered: list[str] = []
    previous = -1
    for index in sorted(keep):
        if index >= len(lines):
            continue
        if previous >= 0 and index > previous + 1:
            rendered.append("\n[... omitted lower-relevance lines ...]\n")
        rendered.append(lines[index])
        previous = index
    return "\n".join(rendered).strip()


__all__ = ["build_block_section_context"]
