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
    build_section_outline,
    excluded_line_numbers,
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
        selected_lines = [
            lines[line_no - 1]
            for line_no in range(start_line, end_line + 1)
            if line_no not in excluded
        ]
        if not any(line.strip() for line in selected_lines):
            rejected.append({**record, "reason": "empty_after_excluding_non_paper_content"})
            continue
        block_lines.setdefault(section_key, [])
        if block_lines[section_key] and block_lines[section_key][-1].strip():
            block_lines[section_key].append("")
        block_lines[section_key].extend(selected_lines)
        occupied.update(range(start_line, end_line + 1))
        accepted.append(record)
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
    }


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


def _canonical_section_key(value: object) -> str:
    key = re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")
    aliases = {
        "background": "related_work",
        "background_and_related_work": "related_work",
        "introduction": "related_work",
        "intro_related_work": "related_work",
        "related": "related_work",
        "related_work": "related_work",
        "related_works": "related_work",
        "approach": "method",
        "framework": "method",
        "methodology": "method",
        "methods": "method",
        "results": "experiment",
        "evaluation": "experiment",
        "experiments": "experiment",
        "empirical": "experiment",
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
    "split_canonical_sections",
    "split_sections_deterministically",
]
