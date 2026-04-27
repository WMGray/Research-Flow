"""Paper note generation — per-block LLM calls with figure evidence collection."""

from core.services.papers.note.runtime import generate_paper_note, render_note_markdown, extract_managed_blocks, merge_managed_note_blocks
from core.services.papers.note.visuals import collect_figure_evidence, FigureEvidence

__all__ = [
    "generate_paper_note",
    "render_note_markdown",
    "extract_managed_blocks",
    "merge_managed_note_blocks",
    "collect_figure_evidence",
    "FigureEvidence",
]
