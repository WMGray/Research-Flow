from __future__ import annotations

from collections.abc import Callable
import re
from typing import Protocol, TypeVar

from .parsing import DeterministicNormalizationOperation


class LineEntryLike(Protocol):
    line_no: int
    text: str


TLine = TypeVar("TLine", bound=LineEntryLike)
OperationFactory = Callable[
    [str, int, str, str, str, int],
    DeterministicNormalizationOperation,
]
LineFactory = Callable[[int, str], TLine]
IMAGE_RE = re.compile(r"^\s*!\[[^\]]*]\([^)]+\)")
CAPTION_RE = re.compile(
    r"^\s*(?:>\s*)?(?:\*\*图注\*\*[:：]\s*)?"
    r"(?:fig(?:ure)?|table)\s*[A-Za-z]?\d+(?:\.\d+)*\s*[:.：]?",
    re.IGNORECASE,
)
CAUTION_RE = re.compile(r"^\s*>\[!caution]\s*$", re.IGNORECASE)


def normalize_image_annotations(
    entries: list[TLine],
    operations: list[DeterministicNormalizationOperation],
    *,
    make_line: LineFactory[TLine],
    make_operation: OperationFactory,
) -> list[TLine]:
    normalized: list[TLine] = []
    index = 0
    while index < len(entries):
        entry = entries[index]
        normalized.append(entry)
        if not IMAGE_RE.match(entry.text):
            index += 1
            continue

        next_index = index + 1
        blanks: list[TLine] = []
        while next_index < len(entries) and not entries[next_index].text.strip():
            blanks.append(entries[next_index])
            next_index += 1
        if next_index < len(entries) and CAPTION_RE.match(entries[next_index].text):
            _record_removed_caption_gaps(blanks, operations, make_operation)
            caption_entry = entries[next_index]
            formatted_caption = format_caption_line(caption_entry.text)
            if formatted_caption != caption_entry.text:
                operations.append(
                    make_operation(
                        "format_figure_caption_blockquote",
                        caption_entry.line_no,
                        caption_entry.text,
                        formatted_caption,
                        "Represent figure/table captions as Markdown blockquotes in refined.md.",
                        len(operations) + 1,
                    )
                )
            normalized.append(make_line(caption_entry.line_no, formatted_caption))
            index = next_index + 1
            continue

        if next_index < len(entries) and CAUTION_RE.match(entries[next_index].text):
            normalized.extend(blanks)
            index += len(blanks) + 1
            continue

        caution_line = ">[!Caution]"
        caution_detail = "> 解析结果没有在图片附近找到可靠图注，需要人工核对原 PDF。"
        operations.append(
            make_operation(
                "mark_image_caption_needs_review",
                entry.line_no,
                entry.text,
                "\n".join([entry.text, caution_line, caution_detail]),
                "Mark images without nearby captions for human review in refined.md.",
                len(operations) + 1,
            )
        )
        normalized.append(make_line(entry.line_no, caution_line))
        normalized.append(make_line(entry.line_no, caution_detail))
        normalized.extend(blanks)
        index += len(blanks) + 1
    return normalized


def format_caption_line(line: str) -> str:
    stripped = line.strip()
    stripped = re.sub(r"^>\s*", "", stripped)
    stripped = re.sub(r"^\*\*图注\*\*[:：]\s*", "", stripped)
    return f"> **图注**：{stripped}"


def _record_removed_caption_gaps(
    blanks: list[TLine],
    operations: list[DeterministicNormalizationOperation],
    make_operation: OperationFactory,
) -> None:
    for blank in blanks:
        operations.append(
            make_operation(
                "remove_image_caption_gap",
                blank.line_no,
                blank.text,
                "",
                "Keep an image and its immediate caption adjacent.",
                len(operations) + 1,
            )
        )


__all__ = ["normalize_image_annotations"]
