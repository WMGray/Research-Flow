from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any
from uuid import uuid4

from core.services.llm import llm_registry
from core.services.llm.schemas import LLMMessage, LLMRequest
from core.services.papers.models import PaperRecord
from core.services.papers.refine.parsing import extract_json_object
from core.services.papers.skill_runtime import load_skill_runtime_instructions
from .blocks import (
    LLMGenerateClient,
    NOTE_BLOCK_ORDER,
    blocks_from_payload,
    fallback_note_blocks,
    generate_detailed_note_blocks,
)
from .visuals import (
    FigureEvidence,
    collect_figure_evidence,
    render_figure_context,
)


DEFAULT_NOTE_INSTRUCTION_KEY = "paper_note_generate.default"
DEFAULT_NOTE_FEATURE = "paper_note_generate_default"
DEFAULT_NOTE_BLOCK_INSTRUCTION_KEY = "paper_note_generate.block"
DEFAULT_NOTE_BLOCK_FEATURE = "paper_note_generate_block"
DEPRECATED_NOTE_BLOCK_IDS = {"visual_evidence", "limitations", "experimental_setup"}
MANAGED_BLOCK_RE = re.compile(
    r'<!-- RF:BLOCK_START id="(?P<id>[^"]+)" managed="true" version="[^"]+" -->'
    r".*?"
    r'<!-- RF:BLOCK_END id="(?P=id)" -->',
    re.DOTALL,
)


@dataclass(frozen=True, slots=True)
class NoteGenerationResult:
    content: str
    source: str
    llm_run_id: str | None
    instruction_key: str
    feature: str
    block_count: int
    figure_count: int = 0
    block_failures: tuple[str, ...] = ()


def render_note_prompt(
    *,
    instructions: str,
    paper: PaperRecord,
    sections: list[dict[str, Any]],
    figures: list[FigureEvidence] | None = None,
) -> str:
    section_context = "\n\n".join(
        f"## {section['title']}\n{str(section['content']).strip()}"
        for section in sections
    )
    values = {
        "title": paper.title,
        "authors": ", ".join(paper.authors),
        "year": "" if paper.year is None else str(paper.year),
        "venue": paper.venue,
        "doi": paper.doi,
        "section_context": section_context,
        "figure_context": render_figure_context(figures or []),
    }
    rendered = instructions
    for key, value in values.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", value)
    return rendered


def render_note_markdown(
    *,
    title: str,
    blocks: dict[str, str],
) -> str:
    rendered_blocks: list[str] = []
    for block_id, block_title in NOTE_BLOCK_ORDER:
        content = (blocks.get(block_id) or f"Pending {block_title.lower()} synthesis.").strip()
        content = _normalize_block_headings(content, block_title)
        rendered_blocks.append(
            "\n".join(
                [
                    f'<!-- RF:BLOCK_START id="{block_id}" managed="true" version="1" -->',
                    f"## {block_title}",
                    "",
                    content,
                    f'<!-- RF:BLOCK_END id="{block_id}" -->',
                ]
            )
        )
    return f"# {title}\n\n" + "\n\n".join(rendered_blocks) + "\n"


def _normalize_block_headings(content: str, block_title: str) -> str:
    lines = content.strip().splitlines()
    normalized: list[str] = []
    first_content_seen = False
    for line in lines:
        match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line.strip())
        if not match:
            normalized.append(line)
            if line.strip():
                first_content_seen = True
            continue
        heading_text = match.group(2).strip()
        if not first_content_seen and _same_heading_title(heading_text, block_title):
            first_content_seen = True
            continue
        if _same_heading_title(heading_text, block_title):
            continue
        hashes = match.group(1)
        level = max(3, len(hashes))
        normalized.append(f"{'#' * min(level, 6)} {heading_text}")
        first_content_seen = True
    return "\n".join(normalized).strip()


def _same_heading_title(left: str, right: str) -> bool:
    return re.sub(r"\s+", "", left).strip("：:") == re.sub(r"\s+", "", right).strip("：:")


def extract_managed_blocks(markdown: str) -> dict[str, str]:
    return {
        str(match.group("id")): match.group(0).strip()
        for match in MANAGED_BLOCK_RE.finditer(markdown)
    }


def merge_managed_note_blocks(*, existing: str, generated: str) -> str:
    """Update managed RF blocks while preserving user-authored note text."""

    if not existing.strip():
        return generated.rstrip() + "\n"

    generated_blocks = extract_managed_blocks(generated)
    if not generated_blocks:
        return existing.rstrip() + "\n"

    merged = _remove_deprecated_managed_blocks(existing.rstrip())
    missing_blocks: list[str] = []
    for block_id, _ in NOTE_BLOCK_ORDER:
        replacement = generated_blocks.get(block_id)
        if replacement is None:
            continue
        block_pattern = re.compile(
            rf'<!-- RF:BLOCK_START id="{re.escape(block_id)}" '
            rf'managed="true" version="[^"]+" -->.*?'
            rf'<!-- RF:BLOCK_END id="{re.escape(block_id)}" -->',
            re.DOTALL,
        )
        merged, replace_count = block_pattern.subn(replacement, merged, count=1)
        if replace_count == 0:
            missing_blocks.append(replacement)

    if missing_blocks:
        merged = merged.rstrip() + "\n\n" + "\n\n".join(missing_blocks)
    return merged.rstrip() + "\n"


def _remove_deprecated_managed_blocks(markdown: str) -> str:
    cleaned = markdown
    for block_id in DEPRECATED_NOTE_BLOCK_IDS:
        cleaned = re.sub(
            rf'\n*<!-- RF:BLOCK_START id="{re.escape(block_id)}" '
            rf'managed="true" version="[^"]+" -->.*?'
            rf'<!-- RF:BLOCK_END id="{re.escape(block_id)}" -->\n*',
            "\n\n",
            cleaned,
            flags=re.DOTALL,
        )
    return cleaned.rstrip()


async def _generate_note_async(
    *,
    paper: PaperRecord,
    sections: list[dict[str, Any]],
    figures: list[FigureEvidence],
    llm_client: LLMGenerateClient,
    instruction_key: str,
    feature: str,
) -> NoteGenerationResult:
    instructions = load_skill_runtime_instructions(instruction_key)
    prompt = render_note_prompt(
        instructions=instructions,
        paper=paper,
        sections=sections,
        figures=figures,
    )
    response = await llm_client.generate(
        LLMRequest(
            feature=feature,
            messages=[LLMMessage(role="user", content=prompt)],
            max_tokens=12000,
            max_completion_tokens=12000,
            extra={"response_format": {"type": "json_object"}},
        )
    )
    payload = extract_json_object(response.message.content)
    blocks_payload = payload.get("blocks", payload)
    if not isinstance(blocks_payload, dict):
        raise ValueError("paper note LLM response must contain an object of note blocks")
    blocks = blocks_from_payload(blocks_payload, figures)
    return NoteGenerationResult(
        content=render_note_markdown(title=paper.title, blocks=blocks),
        source="llm",
        llm_run_id=f"llm_{uuid4().hex}",
        instruction_key=instruction_key,
        feature=feature,
        block_count=len(NOTE_BLOCK_ORDER),
        figure_count=len(figures),
    )


async def _generate_detailed_note_async(
    *,
    paper: PaperRecord,
    sections: list[dict[str, Any]],
    figures: list[FigureEvidence],
    llm_client: LLMGenerateClient,
    instruction_key: str,
    feature: str,
    block_instruction_key: str,
    block_feature: str,
) -> NoteGenerationResult:
    blocks, block_failures = await generate_detailed_note_blocks(
        paper=paper,
        sections=sections,
        figures=figures,
        llm_client=llm_client,
        instruction_key=block_instruction_key,
        feature=block_feature,
    )
    return NoteGenerationResult(
        content=render_note_markdown(title=paper.title, blocks=blocks),
        source="llm" if not block_failures else "llm_partial",
        llm_run_id=f"llm_{uuid4().hex}",
        instruction_key=block_instruction_key,
        feature=block_feature,
        block_count=len(NOTE_BLOCK_ORDER),
        figure_count=len(figures),
        block_failures=block_failures,
    )


def generate_paper_note(
    *,
    paper: PaperRecord,
    sections: list[dict[str, Any]],
    llm_client: LLMGenerateClient = llm_registry,
    instruction_key: str = DEFAULT_NOTE_INSTRUCTION_KEY,
    feature: str = DEFAULT_NOTE_FEATURE,
    block_instruction_key: str = DEFAULT_NOTE_BLOCK_INSTRUCTION_KEY,
    block_feature: str = DEFAULT_NOTE_BLOCK_FEATURE,
    note_path: Path | None = None,
    image_base_dirs: list[Path] | None = None,
) -> NoteGenerationResult:
    figures = collect_figure_evidence(
        sections,
        note_path=note_path,
        image_base_dirs=image_base_dirs or [],
    )
    try:
        if llm_client is llm_registry:
            return asyncio.run(
                _generate_detailed_note_async(
                    paper=paper,
                    sections=sections,
                    figures=figures,
                    llm_client=llm_client,
                    instruction_key=instruction_key,
                    feature=feature,
                    block_instruction_key=block_instruction_key,
                    block_feature=block_feature,
                )
            )
        return asyncio.run(
            _generate_note_async(
                paper=paper,
                sections=sections,
                figures=figures,
                llm_client=llm_client,
                instruction_key=instruction_key,
                feature=feature,
            )
        )
    except Exception:
        blocks = fallback_note_blocks(sections, figures=figures)
        return NoteGenerationResult(
            content=render_note_markdown(title=paper.title, blocks=blocks),
            source="deterministic_fallback",
            llm_run_id=None,
            instruction_key=instruction_key,
            feature=feature,
            block_count=len(NOTE_BLOCK_ORDER),
            figure_count=len(figures),
        )


__all__ = [
    "NOTE_BLOCK_ORDER",
    "FigureEvidence",
    "NoteGenerationResult",
    "collect_figure_evidence",
    "extract_managed_blocks",
    "fallback_note_blocks",
    "generate_paper_note",
    "merge_managed_note_blocks",
    "render_figure_context",
    "render_note_markdown",
]
