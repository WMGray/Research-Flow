"""Paper section splitting — LLM semantic planning with deterministic heuristics fallback."""

from core.services.papers.split.runtime import split_canonical_sections, SectionSplitResult
from core.services.papers.split.heuristics import (
    split_sections_deterministically,
    build_section_outline,
    excluded_line_numbers,
    CANONICAL_SECTION_ORDER,
    SECTION_ALIASES,
)

__all__ = [
    "split_canonical_sections",
    "SectionSplitResult",
    "split_sections_deterministically",
    "build_section_outline",
    "excluded_line_numbers",
    "CANONICAL_SECTION_ORDER",
    "SECTION_ALIASES",
]
