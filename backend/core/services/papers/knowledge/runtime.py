"""Evidence-grounded local Knowledge extraction for Paper notes.

This module provides a deterministic baseline so the Paper pipeline can produce
useful reviewable records before a real LLM extractor is configured. LLM-backed
extraction can later replace or augment this runtime without changing the
repository contract.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


CLAIM_PATTERNS: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (
        re.compile(r"\b(we|this paper|the paper)\s+(propose|introduce|present)s?\b", re.I),
        "core_insight",
        "核心方法主张",
    ),
    (
        re.compile(r"\b(show|demonstrate|find|observe|prove)s?\b", re.I),
        "key_conclusion",
        "关键结论",
    ),
    (
        re.compile(r"\b(outperform|improve|reduce|increase|achieve)s?\b", re.I),
        "key_conclusion",
        "实验结论",
    ),
    (
        re.compile(r"\b(limitation|challenge|fail|bottleneck|drawback|problem)s?\b", re.I),
        "method_critique",
        "局限与挑战",
    ),
    (
        re.compile(r"\b(requires?|depends?|assumes?|is defined as|refers to)\b", re.I),
        "concept_term",
        "概念定义",
    ),
)


@dataclass(frozen=True, slots=True)
class KnowledgeExtractionItem:
    knowledge_type: str
    title: str
    summary_zh: str
    original_text_en: str
    category_label: str
    source_section: str
    source_locator: str
    evidence_text: str
    confidence_score: float


@dataclass(frozen=True, slots=True)
class KnowledgeExtractionResult:
    items: list[KnowledgeExtractionItem] = field(default_factory=list)
    source: str = "deterministic_evidence"
    skipped_reason: str = ""


def extract_knowledge(
    *,
    paper_title: str,
    note: str,
    sections: list[dict[str, object]],
    max_items: int = 5,
) -> KnowledgeExtractionResult:
    """Extract citable claims and definitions from note/section evidence."""

    evidence_sources = _evidence_sources(note=note, sections=sections)
    if not evidence_sources:
        return KnowledgeExtractionResult(skipped_reason="No note or section text available.")

    items: list[KnowledgeExtractionItem] = []
    seen: set[str] = set()
    for section_key, text in evidence_sources:
        for sentence in _candidate_sentences(text):
            normalized = _sentence_key(sentence)
            if normalized in seen:
                continue
            match = _classify_sentence(sentence)
            if match is None:
                continue
            seen.add(normalized)
            category_label, title_prefix, confidence = match
            knowledge_type = "definition" if category_label == "concept_term" else "view"
            items.append(
                KnowledgeExtractionItem(
                    knowledge_type=knowledge_type,
                    title=_title_for_sentence(title_prefix, sentence),
                    summary_zh=_summary_for_sentence(title_prefix, sentence),
                    original_text_en=sentence,
                    category_label=category_label,
                    source_section=section_key,
                    source_locator="sentence",
                    evidence_text=sentence,
                    confidence_score=confidence,
                )
            )
            if len(items) >= max_items:
                return KnowledgeExtractionResult(items=items)

    if items:
        return KnowledgeExtractionResult(items=items)
    return KnowledgeExtractionResult(
        skipped_reason=f"No citable claim or definition pattern detected for {paper_title}."
    )


def _evidence_sources(
    *,
    note: str,
    sections: list[dict[str, object]],
) -> list[tuple[str, str]]:
    sources: list[tuple[str, str]] = []
    if note.strip():
        sources.append(("note", _strip_markdown_blocks(note)))
    for section in sections:
        section_key = str(section.get("section_key") or section.get("title") or "section")
        content = str(section.get("content") or "")
        if content.strip():
            sources.append((section_key, _strip_markdown_blocks(content)))
    return sources


def _candidate_sentences(text: str) -> list[str]:
    compact = re.sub(r"\s+", " ", text).strip()
    if not compact:
        return []
    parts = re.split(r"(?<=[.!?])\s+", compact)
    return [
        part.strip(" -")
        for part in parts
        if 80 <= len(part.strip()) <= 520 and not part.lstrip().startswith("|")
    ]


def _classify_sentence(sentence: str) -> tuple[str, str, float] | None:
    for pattern, category_label, title_prefix in CLAIM_PATTERNS:
        if pattern.search(sentence):
            confidence = 0.72 if category_label == "concept_term" else 0.76
            return category_label, title_prefix, confidence
    return None


def _title_for_sentence(prefix: str, sentence: str) -> str:
    clean = _clean_sentence(sentence)
    if len(clean) > 96:
        clean = clean[:93].rstrip() + "..."
    return f"{prefix}: {clean}"


def _summary_for_sentence(prefix: str, sentence: str) -> str:
    return f"{prefix}：{_clean_sentence(sentence)}"


def _clean_sentence(sentence: str) -> str:
    return re.sub(r"\s+", " ", sentence).strip()


def _sentence_key(sentence: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", sentence.lower())[:180]


def _strip_markdown_blocks(text: str) -> str:
    without_comments = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    without_code = re.sub(r"```.*?```", " ", without_comments, flags=re.S)
    return without_code.replace("#", " ")
