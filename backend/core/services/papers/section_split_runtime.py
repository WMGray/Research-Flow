from __future__ import annotations

import asyncio
from dataclasses import dataclass
import re
from typing import Any, Protocol

from core.services.llm import llm_registry
from core.services.llm.schemas import LLMMessage, LLMRequest, LLMResponse
from core.services.papers.prompt_runtime import load_prompt_template, render_template
from core.services.papers.refine_parsing import extract_json_object


CANONICAL_SECTION_ORDER: tuple[tuple[str, str], ...] = (
    ("related_work", "Related Work"),
    ("method", "Method"),
    ("experiment", "Experiment"),
    ("conclusion", "Conclusion"),
)
SECTION_ALIASES: dict[str, tuple[str, ...]] = {
    "related_work": ("related work", "related works", "background"),
    "method": ("method", "our method", "methodology", "approach"),
    "experiment": ("experiment", "experiments", "empirical experiments", "evaluation"),
    "conclusion": ("conclusion", "conclusions", "conclusion and future work"),
}
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
SECTION_NUMBER_RE = re.compile(r"^(\d+(?:\.\d+)*)(?:\.)?\s+(.+)$")
APPENDIX_HEADING_RE = re.compile(r"^[a-h](?:\.\d+)?\s+.+$")


class LLMGenerateClient(Protocol):
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate an LLM response for a configured feature."""


@dataclass(frozen=True, slots=True)
class SectionSplitResult:
    blocks: dict[str, str]
    report: dict[str, Any]


def split_canonical_sections(
    content: str,
    *,
    llm_client: LLMGenerateClient = llm_registry,
) -> SectionSplitResult:
    return asyncio.run(_split_canonical_sections_async(content, llm_client=llm_client))


async def _split_canonical_sections_async(
    content: str,
    *,
    llm_client: LLMGenerateClient,
) -> SectionSplitResult:
    blocks, deterministic_report = split_sections_deterministically(content)
    report: dict[str, Any] = {
        "strategy": "deterministic",
        "used_llm": False,
        "deterministic": deterministic_report,
        "llm": None,
    }
    if not _needs_llm_split(content, blocks):
        return SectionSplitResult(blocks=blocks, report=report)

    try:
        llm_blocks, llm_report = await _llm_split_blocks(content, llm_client)
    except Exception as exc:  # noqa: BLE001 - deterministic split remains valid
        report["llm"] = {"status": "warning", "message": str(exc)}
        return SectionSplitResult(blocks=blocks, report=report)

    merged = {**blocks, **llm_blocks}
    if _is_split_improved(blocks, merged):
        report.update({"strategy": "deterministic+llm", "used_llm": True, "llm": llm_report})
        return SectionSplitResult(blocks=merged, report=report)
    report["llm"] = {**llm_report, "status": "rejected"}
    return SectionSplitResult(blocks=blocks, report=report)


def split_sections_deterministically(content: str) -> tuple[dict[str, str], dict[str, Any]]:
    section_lines: dict[str, list[str]] = {key: [] for key, _ in CANONICAL_SECTION_ORDER}
    headings: list[dict[str, Any]] = []
    current_key: str | None = None

    for line_no, line in enumerate(content.splitlines(), start=1):
        heading = _parse_heading(line, line_no)
        if heading:
            headings.append(heading)
            matched_key = _canonical_key(heading)
            if matched_key:
                current_key = matched_key
            elif _ends_current_section(heading):
                current_key = None
        if current_key is not None:
            section_lines[current_key].append(line)

    blocks = {
        key: "\n".join(lines).strip() + "\n"
        for key, lines in section_lines.items()
        if lines
    }
    return blocks, {
        "status": "pass",
        "section_keys": sorted(blocks),
        "heading_count": len(headings),
        "headings": headings[:80],
    }


def build_section_outline(content: str, *, max_headings: int = 120) -> str:
    lines = content.splitlines()
    headings = [
        heading
        for index, line in enumerate(lines, start=1)
        if (heading := _parse_heading(line, index))
    ]
    rendered = [
        "# Section Split Evidence",
        f"line_count: {len(lines)}",
        "Only headings and the first metadata lines are shown. Ranges refer to full refined.md line numbers.",
        "",
        "## Metadata Window",
    ]
    rendered.extend(f"{index:05d}: {line[:240]}" for index, line in enumerate(lines[:24], start=1) if line.strip())
    rendered.extend(["", "## Heading Outline"])
    rendered.extend(_format_heading(heading) for heading in headings[:max_headings])
    if len(headings) > max_headings:
        rendered.append(f"[truncated_headings count={len(headings) - max_headings}]")
    return "\n".join(rendered)


async def _llm_split_blocks(
    content: str,
    llm_client: LLMGenerateClient,
) -> tuple[dict[str, str], dict[str, Any]]:
    prompt = render_template(
        load_prompt_template("paper_section_split.default"),
        {"section_outline": build_section_outline(content)},
    )
    response = await llm_client.generate(
        LLMRequest(
            feature="paper_section_splitter",
            messages=[LLMMessage(role="user", content=prompt)],
            max_tokens=1536,
            extra={"response_format": {"type": "json_object"}},
        )
    )
    return _blocks_from_plan(content, extract_json_object(response.message.content))


def _blocks_from_plan(content: str, payload: dict[str, Any]) -> tuple[dict[str, str], dict[str, Any]]:
    lines = content.splitlines()
    raw_sections = payload.get("sections", [])
    if not isinstance(raw_sections, list):
        raw_sections = []

    blocks: dict[str, str] = {}
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    occupied: set[int] = set()
    allowed = {key for key, _ in CANONICAL_SECTION_ORDER}
    for item in raw_sections:
        if not isinstance(item, dict):
            continue
        record = _section_range(item, len(lines))
        reason = _range_rejection_reason(record, allowed, occupied)
        if reason:
            rejected.append({**record, "reason": reason})
            continue
        section_key = str(record["section_key"])
        start_line = int(record["start_line"])
        end_line = int(record["end_line"])
        blocks[section_key] = "\n".join(lines[start_line - 1 : end_line]).strip() + "\n"
        occupied.update(range(start_line, end_line + 1))
        accepted.append(record)
    return blocks, {"status": "pass", "accepted": accepted, "rejected": rejected, "raw_section_count": len(raw_sections)}


def _parse_heading(line: str, line_no: int) -> dict[str, Any] | None:
    match = HEADING_RE.match(line.strip())
    if not match:
        return None
    level = len(match.group(1))
    body = match.group(2).strip()
    number = ""
    label = body
    if number_match := SECTION_NUMBER_RE.match(body.lower()):
        number, label = number_match.group(1), number_match.group(2).strip()
    elif APPENDIX_HEADING_RE.match(body.lower()):
        number, label = body.split(maxsplit=1)
    return {
        "line_no": line_no,
        "level": level,
        "raw": line,
        "label": label.lower(),
        "number": number.lower(),
        "is_major": _is_major_heading(level, number),
    }


def _canonical_key(heading: dict[str, Any]) -> str | None:
    if not heading["is_major"]:
        return None
    label = str(heading["label"])
    return next(
        (
            key
            for key, aliases in SECTION_ALIASES.items()
            if any(label.startswith(alias) for alias in aliases)
        ),
        None,
    )


def _ends_current_section(heading: dict[str, Any]) -> bool:
    label = str(heading["label"])
    return bool(heading["is_major"]) or label.startswith(("references", "acknowledg", "appendix"))


def _is_major_heading(level: int, number: str) -> bool:
    return "." not in number if number else level <= 2


def _format_heading(heading: dict[str, Any]) -> str:
    return (
        f"{int(heading['line_no']):05d}: level={heading['level']} "
        f"number={heading['number'] or '-'} major={str(heading['is_major']).lower()} "
        f"label={heading['label']} raw={heading['raw']}"
    )


def _needs_llm_split(content: str, blocks: dict[str, str]) -> bool:
    if len(blocks) < 3 or any(key not in blocks for key in ("method", "experiment")):
        return True
    content_len = max(len(content.strip()), 1)
    return any(len(blocks.get(key, "")) / content_len < 0.02 for key in ("method", "experiment"))


def _is_split_improved(before: dict[str, str], after: dict[str, str]) -> bool:
    if not set(after).issuperset(before):
        return False
    return len(after) > len(before) or any(len(after[key]) > len(before.get(key, "")) * 1.2 for key in after)


def _section_range(item: dict[str, Any], line_count: int) -> dict[str, Any]:
    start_line = _bounded_line(item.get("start_line"), 1, line_count)
    end_line = _bounded_line(item.get("end_line"), start_line, line_count)
    return {
        "section_key": str(item.get("section_key") or ""),
        "start_line": start_line,
        "end_line": end_line,
        "confidence": float(item.get("confidence") or 0.0),
        "rationale": str(item.get("rationale") or ""),
    }


def _range_rejection_reason(record: dict[str, Any], allowed: set[str], occupied: set[int]) -> str | None:
    if record["section_key"] not in allowed:
        return "unknown_section_key"
    if float(record["confidence"]) < 0.65:
        return "confidence_below_threshold"
    if int(record["end_line"]) < int(record["start_line"]):
        return "invalid_line_range"
    if any(line_no in occupied for line_no in range(int(record["start_line"]), int(record["end_line"]) + 1)):
        return "overlapping_line_range"
    return None


def _bounded_line(value: object, default: int, line_count: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(1, min(parsed, max(line_count, 1)))


__all__ = [
    "CANONICAL_SECTION_ORDER",
    "SectionSplitResult",
    "build_section_outline",
    "split_canonical_sections",
    "split_sections_deterministically",
]
