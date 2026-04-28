from __future__ import annotations

import asyncio
from dataclasses import dataclass
import re
from typing import Any, Protocol

from core.services.llm import llm_registry
from core.services.llm.schemas import LLMMessage, LLMRequest, LLMResponse
from core.services.papers.skill_runtime import load_skill_runtime_instructions, render_skill_instructions
from core.services.papers.refine.parsing import extract_json_object
from .heuristics import (
    CANONICAL_SECTION_ORDER,
    assign_lines_deterministically,
    build_section_outline,
    excluded_line_numbers,
    section_filename,
    split_sections_deterministically,
)


DEFAULT_SECTIONING_INSTRUCTION_KEY = "paper_sectioning.default"
DEFAULT_SECTIONING_FEATURE = "paper_sectioning_default"


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
    fallback_blocks, deterministic_report = split_sections_deterministically(content)
    report: dict[str, Any] = {
        "strategy": "llm_semantic",
        "used_llm": True,
        "deterministic_fallback": deterministic_report,
        "llm": None,
    }
    try:
        llm_blocks, llm_report = await _llm_split_blocks(content, llm_client)
    except Exception as exc:  # noqa: BLE001 - deterministic fallback keeps pipeline usable
        report.update(
            {
                "strategy": "deterministic_fallback",
                "used_llm": False,
                "llm": {"status": "warning", "message": str(exc)},
            }
        )
        return SectionSplitResult(blocks=fallback_blocks, report=report)

    if llm_blocks:
        report["llm"] = llm_report
        return SectionSplitResult(blocks=llm_blocks, report=report)

    report.update(
        {
            "strategy": "deterministic_fallback",
            "used_llm": False,
            "llm": {**llm_report, "status": "empty_or_rejected"},
        }
    )
    return SectionSplitResult(blocks=fallback_blocks, report=report)


async def _llm_split_blocks(
    content: str,
    llm_client: LLMGenerateClient,
) -> tuple[dict[str, str], dict[str, Any]]:
    prompt = render_skill_instructions(
        load_skill_runtime_instructions(DEFAULT_SECTIONING_INSTRUCTION_KEY),
        {"section_outline": build_section_outline(content)},
    )
    response = await llm_client.generate(
        LLMRequest(
            feature=DEFAULT_SECTIONING_FEATURE,
            messages=[LLMMessage(role="user", content=prompt)],
            max_tokens=4096,
            max_completion_tokens=4096,
            extra={"response_format": {"type": "json_object"}},
        )
    )
    return _blocks_from_plan(content, extract_json_object(response.message.content))


def _blocks_from_plan(content: str, payload: dict[str, Any]) -> tuple[dict[str, str], dict[str, Any]]:
    lines = content.splitlines()
    excluded = excluded_line_numbers(lines)
    raw_sections = payload.get("sections", [])
    if not isinstance(raw_sections, list):
        raw_sections = []

    block_lines: dict[str, list[str]] = {}
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    occupied: dict[int, set[str]] = {}
    allowed = {key for key, _ in CANONICAL_SECTION_ORDER}
    for item in raw_sections:
        if not isinstance(item, dict):
            continue
        record = _section_range(item, len(lines))
        reason = _range_rejection_reason(record, allowed, occupied)
        if reason:
            rejected.append({**record, "reason": reason})
            continue
        selected_lines = _selected_lines(lines, excluded, record)
        if not any(line.strip() for line in selected_lines):
            rejected.append({**record, "reason": "empty_after_excluding_non_paper_content"})
            continue
        section_key = str(record["section_key"])
        for line_no in range(int(record["start_line"]), int(record["end_line"]) + 1):
            occupied.setdefault(line_no, set()).add(section_key)
        accepted.append({**record, "source": "llm"})

    coverable = _coverable_lines(lines, excluded)
    initial_uncovered = _uncovered_lines(coverable, occupied)
    filled_ranges: list[dict[str, Any]] = []
    if accepted and initial_uncovered:
        assignments, _ = assign_lines_deterministically(content)
        filled_ranges = _coverage_fill_ranges(initial_uncovered, assignments, occupied)
        accepted.extend(filled_ranges)

    for record in sorted(
        accepted,
        key=lambda item: (
            int(item["start_line"]),
            int(item["end_line"]),
            str(item["section_key"]),
        ),
    ):
        section_key = str(record["section_key"])
        selected_lines = _selected_lines(lines, excluded, record)
        if not any(line.strip() for line in selected_lines):
            continue
        block_lines.setdefault(section_key, [])
        if block_lines[section_key] and block_lines[section_key][-1].strip():
            block_lines[section_key].append("")
        block_lines[section_key].extend(selected_lines)

    final_uncovered = _uncovered_lines(coverable, occupied)
    blocks = {
        key: "\n".join(lines_).strip() + "\n"
        for key, lines_ in block_lines.items()
        if any(line.strip() for line in lines_)
    }
    return blocks, {
        "status": "pass",
        "accepted": accepted,
        "rejected": rejected,
        "raw_section_count": len(raw_sections),
        "excluded_line_count": len(excluded),
        "coverage": {
            "coverable_line_count": len(coverable),
            "initial_uncovered_line_count": len(initial_uncovered),
            "filled_line_count": sum(
                int(record["end_line"]) - int(record["start_line"]) + 1
                for record in filled_ranges
            ),
            "filled_range_count": len(filled_ranges),
            "final_uncovered_line_count": len(final_uncovered),
        },
    }


def _selected_lines(
    lines: list[str],
    excluded: set[int],
    record: dict[str, Any],
) -> list[str]:
    return [
        lines[line_no - 1]
        for line_no in range(int(record["start_line"]), int(record["end_line"]) + 1)
        if line_no not in excluded
    ]


def _coverable_lines(lines: list[str], excluded: set[int]) -> set[int]:
    return {
        line_no
        for line_no, line in enumerate(lines, start=1)
        if line_no not in excluded and line.strip()
    }


def _uncovered_lines(coverable: set[int], occupied: dict[int, set[str]]) -> list[int]:
    return sorted(line_no for line_no in coverable if not occupied.get(line_no))


def _coverage_fill_ranges(
    uncovered_lines: list[int],
    assignments: dict[int, str],
    occupied: dict[int, set[str]],
) -> list[dict[str, Any]]:
    ranges: list[dict[str, Any]] = []
    start_line: int | None = None
    end_line: int | None = None
    section_key = "introduction"

    def flush() -> None:
        nonlocal start_line, end_line, section_key
        if start_line is None or end_line is None:
            return
        record = {
            "section_key": section_key,
            "start_line": start_line,
            "end_line": end_line,
            "confidence": 1.0,
            "rationale": "Coverage fill for non-reference paper content omitted by the LLM section plan.",
            "source": "coverage_fill",
        }
        ranges.append(record)
        for line_no in range(start_line, end_line + 1):
            occupied.setdefault(line_no, set()).add(section_key)
        start_line = None
        end_line = None

    for line_no in uncovered_lines:
        assigned_key = assignments.get(line_no, "introduction")
        if start_line is None:
            start_line = line_no
            end_line = line_no
            section_key = assigned_key
            continue
        if line_no == int(end_line) + 1 and assigned_key == section_key:
            end_line = line_no
            continue
        flush()
        start_line = line_no
        end_line = line_no
        section_key = assigned_key
    flush()
    return ranges


def _section_range(item: dict[str, Any], line_count: int) -> dict[str, Any]:
    start_line = _bounded_line(item.get("start_line"), 1, line_count)
    end_line = _bounded_line(item.get("end_line"), start_line, line_count)
    return {
        "section_key": _canonical_section_key(item.get("section_key")),
        "start_line": start_line,
        "end_line": end_line,
        "confidence": float(item.get("confidence") or 0.0),
        "rationale": str(item.get("rationale") or ""),
    }


def _range_rejection_reason(
    record: dict[str, Any],
    allowed: set[str],
    occupied: dict[int, set[str]],
) -> str | None:
    section_key = str(record["section_key"])
    if section_key not in allowed:
        return "unknown_section_key"
    if float(record["confidence"]) < 0.65:
        return "confidence_below_threshold"
    if int(record["end_line"]) < int(record["start_line"]):
        return "invalid_line_range"
    for line_no in range(int(record["start_line"]), int(record["end_line"]) + 1):
        existing_keys = occupied.get(line_no, set())
        if section_key in existing_keys:
            return "overlapping_line_range"
        if existing_keys and not _is_allowed_overlap(section_key, existing_keys):
            return "overlapping_line_range"
    return None


def _is_allowed_overlap(section_key: str, existing_keys: set[str]) -> bool:
    return section_key not in existing_keys


def _bounded_line(value: object, default: int, line_count: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(1, min(parsed, max(line_count, 1)))


def _canonical_section_key(value: object) -> str:
    key = re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")
    aliases = {
        "background": "related_work",
        "background_and_related_work": "related_work",
        "abstract": "introduction",
        "intro": "introduction",
        "introduction": "introduction",
        "motivation": "introduction",
        "contribution": "introduction",
        "intro_related_work": "related_work",
        "related": "related_work",
        "related_work": "related_work",
        "related_works": "related_work",
        "approach": "method",
        "framework": "method",
        "methodology": "method",
        "methods": "method",
        "proof": "method",
        "theory": "method",
        "algorithm": "method",
        "algorithms": "method",
        "results": "experiment",
        "evaluation": "experiment",
        "experiments": "experiment",
        "empirical": "experiment",
        "ablation": "experiment",
        "ablations": "experiment",
        "analysis": "experiment",
        "dataset": "experiment",
        "datasets": "experiment",
        "appendices": "appendix",
        "supplementary": "appendix",
        "supplementary_material": "appendix",
        "discussion": "conclusion",
        "future_work": "conclusion",
        "conclusions": "conclusion",
    }
    return aliases.get(key, key)


__all__ = [
    "CANONICAL_SECTION_ORDER",
    "SectionSplitResult",
    "build_section_outline",
    "section_filename",
    "split_canonical_sections",
    "split_sections_deterministically",
]
