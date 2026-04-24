from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path

from core.services.pdf_parser.sections import ParsedPaperSection


ParserProgressCallback = Callable[[str, str], Awaitable[None] | None]


class PDFParserError(RuntimeError):
    """PDF parsing stage error with status code and structured error code."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int = 500,
        error_code: str = "PDF_PARSE_ERROR",
        raw_error_detail: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.raw_error_detail = raw_error_detail


@dataclass(slots=True)
class ParsedPaperContent:
    text: str
    page_count: int
    char_count: int
    excerpt: str
    sections: list[ParsedPaperSection] = field(default_factory=list)
    artifact_markdown_path: Path | None = None
    artifact_image_dir: Path | None = None
    artifact_section_dir: Path | None = None

    def section_outline(self) -> list[dict[str, object]]:
        return [
            {
                "key": section.key,
                "title": section.title,
                "char_count": section.char_count,
            }
            for section in self.sections
        ]


@dataclass(slots=True)
class MinerUExtractionResult:
    markdown_text: str
    markdown_path: Path
    image_dir: Path
    page_count: int
    content_list_path: Path | None = None
