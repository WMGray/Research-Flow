from __future__ import annotations

import re
from typing import Any, Protocol

from core.services.llm.schemas import LLMMessage, LLMRequest, LLMResponse
from core.services.papers.models import PaperRecord
from core.services.papers.refine.parsing import extract_json_object
from core.services.papers.skill_runtime import load_skill_runtime_instructions, render_skill_instructions
from .context import build_block_section_context
from .visuals import (
    FigureEvidence,
    attach_figures_to_note_blocks,
    render_figure_context,
)
from .schema import (
    LEGACY_BLOCK_MAP,
    NOTE_BLOCK_ORDER,
    NOTE_BLOCK_SPECS,
    note_block_max_tokens,
    note_block_section_keys,
    note_block_spec,
)


METHOD_OVERVIEW_HEADING = "### 方法总览"


class LLMGenerateClient(Protocol):
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate an LLM response for a configured feature."""


def fallback_note_blocks(
    sections: list[dict[str, Any]],
    *,
    figures: list[FigureEvidence] | None = None,
) -> dict[str, str]:
    section_map = {
        str(section["section_key"]): str(section["content"]).strip()
        for section in sections
    }
    blocks = {
        "paper_overview": section_map.get("introduction", "Not stated in the parsed paper."),
        "terminology_guide": "Not stated in the parsed paper.",
        "background_motivation": "\n\n".join(
            part
            for part in [
                section_map.get("introduction", ""),
                section_map.get("related_work", ""),
            ]
            if part.strip()
        )
        or "Not stated in the parsed paper.",
        "method": section_map.get("method", "Not stated in the parsed paper."),
        "experimental_results": "\n\n".join(
            part
            for part in [
                section_map.get("experiment", ""),
                section_map.get("appendix", ""),
            ]
            if part.strip()
        )
        or "Not stated in the parsed paper.",
        "conclusion_limitations": "\n\n".join(
            part
            for part in [
                section_map.get("conclusion", ""),
                section_map.get("appendix", ""),
            ]
            if part.strip()
        )
        or "Not stated in the parsed paper.",
    }
    return _finalize_note_blocks(blocks, figures or [])


def note_block_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return "\n".join(
            f"- {text}"
            for item in value
            if (text := _note_inline_text(item))
        )
    if isinstance(value, dict):
        return "\n".join(
            f"- {str(key).replace('_', ' ').title()}: {text}"
            for key, item in value.items()
            if (text := _note_inline_text(item))
        )
    return str(value).strip()


def blocks_from_payload(
    blocks_payload: dict[str, Any],
    figures: list[FigureEvidence],
) -> dict[str, str]:
    blocks: dict[str, str] = {}
    for block_id, _ in NOTE_BLOCK_ORDER:
        value = blocks_payload.get(block_id)
        if value is None and block_id in LEGACY_BLOCK_MAP:
            value = blocks_payload.get(LEGACY_BLOCK_MAP[block_id])
        blocks[block_id] = note_block_text(value)
    return _finalize_note_blocks(blocks, figures)


async def generate_detailed_note_blocks(
    *,
    paper: PaperRecord,
    sections: list[dict[str, Any]],
    figures: list[FigureEvidence],
    llm_client: LLMGenerateClient,
    instruction_key: str,
    feature: str,
) -> tuple[dict[str, str], tuple[str, ...]]:
    blocks: dict[str, str] = {}
    failures: list[str] = []
    fallback_blocks = fallback_note_blocks(sections, figures=figures)
    for spec in NOTE_BLOCK_SPECS:
        try:
            blocks[spec.block_id] = await _generate_single_note_block(
                paper=paper,
                sections=sections,
                figures=figures,
                llm_client=llm_client,
                instruction_key=instruction_key,
                feature=feature,
                block_id=spec.block_id,
            )
        except Exception as exc:  # noqa: BLE001 - isolate external LLM failures per block
            failures.append(f"{spec.block_id}: {type(exc).__name__}: {str(exc)[:160]}")
            blocks[spec.block_id] = _fallback_text_for_block(spec.block_id, fallback_blocks)
    return _finalize_note_blocks(blocks, figures), tuple(failures)


def _note_inline_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return "; ".join(text for item in value if (text := _note_inline_text(item)))
    if isinstance(value, dict):
        return "; ".join(
            f"{str(key).replace('_', ' ')}: {text}"
            for key, item in value.items()
            if (text := _note_inline_text(item))
        )
    return str(value).strip()


def _finalize_note_blocks(
    blocks: dict[str, str],
    figures: list[FigureEvidence],
) -> dict[str, str]:
    updated = attach_figures_to_note_blocks(blocks, figures)
    if "method" in updated:
        updated["method"] = _ensure_method_overview(updated.get("method", ""))
    return updated


def _ensure_method_overview(text: str) -> str:
    cleaned = text.strip()
    if not cleaned:
        return METHOD_OVERVIEW_HEADING + "\n\n解析内容未提供直接的方法证据。"

    first_line = _first_meaningful_line(cleaned)
    if first_line and re.match(r"^#{3,6}\s+(方法总览|方法概览|总体方法|方法总述)\s*$", first_line):
        return cleaned

    headings = _method_module_headings(cleaned)
    if headings:
        overview = (
            "解析结果显示，本文方法部分后续围绕 "
            + "、".join(headings[:6])
            + " 展开；阅读时应先把这些小节理解为同一方法链条中的组成部分，"
            "再分别检查各模块的背景、原理、公式和作用。"
        )
    else:
        overview = (
            "解析结果没有稳定给出方法模块标题；以下内容保留已抽取的方法证据，"
            "阅读时需要人工核对原文方法章节以确认模块边界。"
        )
    return f"{METHOD_OVERVIEW_HEADING}\n\n{overview}\n\n{cleaned}"


def _first_meaningful_line(text: str) -> str:
    return next((line.strip() for line in text.splitlines() if line.strip()), "")


def _method_module_headings(text: str) -> list[str]:
    headings: list[str] = []
    excluded_prefixes = ("关键方法图表", "Figure", "Table", "图表", "方法总览", "方法概览")
    for line in text.splitlines():
        match = re.match(r"^#{3,6}\s+(.+?)\s*$", line.strip())
        if match is None:
            continue
        title = match.group(1).strip()
        if title.startswith(excluded_prefixes):
            continue
        headings.append(title)
    return headings


async def _generate_single_note_block(
    *,
    paper: PaperRecord,
    sections: list[dict[str, Any]],
    figures: list[FigureEvidence],
    llm_client: LLMGenerateClient,
    instruction_key: str,
    feature: str,
    block_id: str,
) -> str:
    spec = note_block_spec(block_id)
    prompt = render_skill_instructions(
        load_skill_runtime_instructions(instruction_key),
        {
            "block_id": block_id,
            "block_title": spec.title,
            "min_chars": str(spec.min_chars),
            "block_instruction": spec.instruction,
            "title": paper.title,
            "authors": ", ".join(paper.authors),
            "year": "" if paper.year is None else str(paper.year),
            "venue": paper.venue,
            "doi": paper.doi,
            "figure_context": render_figure_context(figures),
            "section_context": _section_context_for_block(block_id, sections),
        },
    )
    response = await llm_client.generate(
        LLMRequest(
            feature=feature,
            messages=[LLMMessage(role="user", content=prompt)],
            max_tokens=note_block_max_tokens(block_id),
            max_completion_tokens=note_block_max_tokens(block_id),
            extra={"response_format": {"type": "json_object"}},
        )
    )
    payload = extract_json_object(response.message.content)
    content = note_block_text(payload.get("content"))
    if not content:
        raise ValueError(f"empty note block: {block_id}")
    return content

def _section_context_for_block(block_id: str, sections: list[dict[str, Any]]) -> str:
    wanted = note_block_section_keys(block_id) or frozenset(
        str(section.get("section_key") or "") for section in sections
    )
    selected = [
        section
        for section in sections
        if str(section.get("section_key") or "") in wanted
    ]
    return build_block_section_context(block_id, selected)


def _fallback_text_for_block(block_id: str, fallback_blocks: dict[str, str]) -> str:
    source_excerpt = _compact_fallback_excerpt(fallback_blocks.get(block_id, ""))
    return "\n".join(
        [
            ">[!Caution]",
            f"> LLM 未能稳定生成 `{block_id}` 的深度中文分析，需要人工复核对应 section。",
            "",
            "解析内容未说明。下面仅保留经过截断的原始证据摘录，不能视为最终分析：",
            "",
            source_excerpt,
        ]
    ).strip()


def _compact_fallback_excerpt(text: str, *, limit: int = 1600) -> str:
    if not text.strip():
        return "Not stated in the parsed paper."
    if len(text) <= limit:
        return text.strip()
    return text[:limit].rstrip() + "\n\n[raw evidence truncated]"


__all__ = [
    "LLMGenerateClient",
    "NOTE_BLOCK_ORDER",
    "blocks_from_payload",
    "fallback_note_blocks",
    "generate_detailed_note_blocks",
    "note_block_text",
]
