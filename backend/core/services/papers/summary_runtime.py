from __future__ import annotations

import asyncio
from dataclasses import dataclass
import re
from typing import Any, Protocol
from uuid import uuid4

from core.services.llm import llm_registry
from core.services.llm.schemas import LLMMessage, LLMRequest, LLMResponse
from core.services.papers.models import PaperRecord
from core.services.papers.prompt_runtime import load_prompt_template
from core.services.papers.refine_parsing import extract_json_object


DEFAULT_NOTE_TEMPLATE_KEY = "paper_note_generate.default"
DEFAULT_NOTE_FEATURE = "paper_note_summarizer"
NOTE_BLOCK_ORDER: tuple[tuple[str, str], ...] = (
    ("research_question", "Research Question"),
    ("core_method", "Core Method"),
    ("main_contributions", "Main Contributions"),
    ("experiment_summary", "Experiment Summary"),
    ("limitations", "Limitations"),
)
MANAGED_BLOCK_RE = re.compile(
    r'<!-- RF:BLOCK_START id="(?P<id>[^"]+)" managed="true" version="[^"]+" -->'
    r".*?"
    r'<!-- RF:BLOCK_END id="(?P=id)" -->',
    re.DOTALL,
)


class LLMGenerateClient(Protocol):
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate an LLM response for a configured feature."""


@dataclass(frozen=True, slots=True)
class NoteGenerationResult:
    content: str
    source: str
    llm_run_id: str | None
    template_key: str
    feature: str
    block_count: int


def render_note_prompt(
    *,
    template_text: str,
    paper: PaperRecord,
    sections: list[dict[str, Any]],
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
    }
    rendered = template_text
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

    merged = existing.rstrip()
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


def fallback_note_blocks(sections: list[dict[str, Any]]) -> dict[str, str]:
    section_map = {
        str(section["section_key"]): str(section["content"]).strip()
        for section in sections
    }
    return {
        "research_question": section_map.get("related_work", "Pending research question synthesis."),
        "core_method": section_map.get("method", "Pending core method synthesis."),
        "main_contributions": section_map.get("method", "Pending main contribution synthesis."),
        "experiment_summary": section_map.get("experiment", "Pending experiment summary synthesis."),
        "limitations": section_map.get("conclusion", "Pending limitation synthesis."),
    }


def _note_block_text(value: Any) -> str:
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


async def _generate_note_async(
    *,
    paper: PaperRecord,
    sections: list[dict[str, Any]],
    llm_client: LLMGenerateClient,
    template_key: str,
    feature: str,
) -> NoteGenerationResult:
    template = load_prompt_template(template_key)
    prompt = render_note_prompt(template_text=template, paper=paper, sections=sections)
    response = await llm_client.generate(
        LLMRequest(
            feature=feature,
            messages=[LLMMessage(role="user", content=prompt)],
            extra={"response_format": {"type": "json_object"}},
        )
    )
    payload = extract_json_object(response.message.content)
    blocks_payload = payload.get("blocks", payload)
    if not isinstance(blocks_payload, dict):
        raise ValueError("paper note LLM response must contain an object of note blocks")
    blocks = {
        block_id: _note_block_text(blocks_payload.get(block_id))
        for block_id, _ in NOTE_BLOCK_ORDER
    }
    return NoteGenerationResult(
        content=render_note_markdown(title=paper.title, blocks=blocks),
        source="llm",
        llm_run_id=f"llm_{uuid4().hex}",
        template_key=template_key,
        feature=feature,
        block_count=len(NOTE_BLOCK_ORDER),
    )


def generate_paper_note(
    *,
    paper: PaperRecord,
    sections: list[dict[str, Any]],
    llm_client: LLMGenerateClient = llm_registry,
    template_key: str = DEFAULT_NOTE_TEMPLATE_KEY,
    feature: str = DEFAULT_NOTE_FEATURE,
) -> NoteGenerationResult:
    try:
        return asyncio.run(
            _generate_note_async(
                paper=paper,
                sections=sections,
                llm_client=llm_client,
                template_key=template_key,
                feature=feature,
            )
        )
    except Exception:
        blocks = fallback_note_blocks(sections)
        return NoteGenerationResult(
            content=render_note_markdown(title=paper.title, blocks=blocks),
            source="deterministic_fallback",
            llm_run_id=None,
            template_key=template_key,
            feature=feature,
            block_count=len(NOTE_BLOCK_ORDER),
        )


__all__ = [
    "NOTE_BLOCK_ORDER",
    "NoteGenerationResult",
    "extract_managed_blocks",
    "fallback_note_blocks",
    "generate_paper_note",
    "merge_managed_note_blocks",
    "render_note_markdown",
]
