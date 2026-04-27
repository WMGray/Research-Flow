"""Paper refine pipeline — diagnose → repair → verify with deterministic fallback."""

from core.services.papers.refine.runtime import refine_markdown
from core.services.papers.refine.normalization import normalize_markdown_structure
from core.services.papers.refine.parsing import (
    build_line_index,
    build_line_numbered_markdown,
    build_structural_evidence_markdown,
    extract_json_object,
    DeterministicNormalizationOperation,
    DeterministicNormalizationReport,
    LineIndex,
    RefineDiagnosis,
    RefineIssue,
    RefinePatch,
    RefineVerifyReport,
)

__all__ = [
    "refine_markdown",
    "normalize_markdown_structure",
    "build_line_index",
    "build_line_numbered_markdown",
    "build_structural_evidence_markdown",
    "extract_json_object",
    "DeterministicNormalizationOperation",
    "DeterministicNormalizationReport",
    "LineIndex",
    "RefineDiagnosis",
    "RefineIssue",
    "RefinePatch",
    "RefineVerifyReport",
]
