from __future__ import annotations

from .models import ParsedPaperContent
from .sections import ParsedPaperSection


SECTION_CONTEXT_PRIORITY = ["introduction", "method", "experiment", "result", "conclusion"]


def build_parsed_content_llm_context(
    parsed_content: ParsedPaperContent,
    *,
    context_chars: int,
    section_chars: int,
) -> str:
    if parsed_content.sections:
        return build_section_context(
            parsed_content.sections,
            context_chars=context_chars,
            section_chars=section_chars,
        )
    return build_fallback_context(parsed_content.text, context_chars=context_chars)


def build_section_context(
    sections: list[ParsedPaperSection],
    *,
    context_chars: int,
    section_chars: int,
) -> str:
    available_chars = context_chars
    blocks: list[str] = []
    ordered_sections = [section for key in SECTION_CONTEXT_PRIORITY for section in sections if section.key == key]

    for section in ordered_sections:
        if available_chars <= 200:
            break
        max_section_chars = min(section_chars, available_chars)
        clipped_text = clip_text(section.text, max_section_chars)
        if not clipped_text:
            continue
        block = f"[Section: {section.title}]\n{clipped_text}"
        blocks.append(block)
        available_chars -= len(block) + 2

    return "\n\n".join(blocks).strip()


def build_fallback_context(text: str, *, context_chars: int) -> str:
    text = text.strip()
    if len(text) <= context_chars:
        return text
    head_chars = int(context_chars * 0.7)
    tail_chars = context_chars - head_chars
    head = text[:head_chars].rstrip()
    tail = text[-tail_chars:].lstrip()
    return f"{head}\n\n[... truncated ...]\n\n{tail}"


def clip_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    clipped = text[: max_chars - 18].rstrip()
    return f"{clipped}\n[... truncated ...]"
