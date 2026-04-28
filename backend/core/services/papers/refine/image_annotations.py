from __future__ import annotations

from collections.abc import Callable, Sequence
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
FLOAT_NUMBER_PATTERN = r"(?:[A-Za-z]\.\d+(?:\.\d+)*|[A-Za-z]?\d+(?:\.\d+)*)"
CAPTION_AT_START_RE = re.compile(
    r"^\s*(?:>\s*)?(?:\*\*)?"
    rf"(?:fig(?:ure)?|table)\s*{FLOAT_NUMBER_PATTERN}"
    r"(?:\*\*)?\s*[:.：]\s*",
    re.IGNORECASE,
)
LOCALIZED_CAPTION_RE = re.compile(
    r"^\s*(?:>\s*)?(?:\*\*)?(?:图注|表注|鍥炬敞|琛ㄦ敞)(?:\*\*)?[:：]\s*",
    re.IGNORECASE,
)
FLOAT_LABEL_RE = re.compile(
    rf"\b(?P<kind>fig(?:ure)?|table)\s*(?P<number>{FLOAT_NUMBER_PATTERN})"
    r"\b(?P<punc>\s*[:.：]?)",
    re.IGNORECASE,
)
CALLOUT_RE = re.compile(r"^\s*>\[!(?:caution|warning)]\s*$", re.IGNORECASE)
CAUTION_RE = re.compile(r"^\s*>\[!caution]\s*$", re.IGNORECASE)
HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+\S")
TABLE_BLOCK_RE = re.compile(r"^\s*(?:<table\b|\|.+\|)", re.IGNORECASE)
SENTENCE_END_RE = re.compile(r"[.!?。！？:：;；)]\s*$")


def normalize_image_annotations(
    entries: list[TLine],
    operations: list[DeterministicNormalizationOperation],
    *,
    make_line: LineFactory[TLine],
    make_operation: OperationFactory,
) -> list[TLine]:
    entries = _normalize_caption_lines(
        entries,
        operations,
        make_line=make_line,
        make_operation=make_operation,
    )
    entries = _normalize_image_blocks(
        entries,
        operations,
        make_line=make_line,
        make_operation=make_operation,
    )
    return _move_interrupted_image_blocks(
        entries,
        operations,
        make_line=make_line,
        make_operation=make_operation,
    )


def _normalize_caption_lines(
    entries: list[TLine],
    operations: list[DeterministicNormalizationOperation],
    *,
    make_line: LineFactory[TLine],
    make_operation: OperationFactory,
) -> list[TLine]:
    normalized: list[TLine] = []
    for entry in entries:
        if _is_caption_line(entry.text):
            formatted_caption = format_caption_line(entry.text)
            if formatted_caption != entry.text:
                operations.append(
                    make_operation(
                        "format_float_caption_blockquote",
                        entry.line_no,
                        entry.text,
                        formatted_caption,
                        (
                            "Represent figure/table captions as Markdown "
                            "blockquotes with Figure/Table labels."
                        ),
                        len(operations) + 1,
                    )
                )
            normalized.append(make_line(entry.line_no, formatted_caption))
            continue

        review_line = _normalize_review_callout_line(entry.text)
        if review_line != entry.text:
            operations.append(
                make_operation(
                    "normalize_caption_review_callout",
                    entry.line_no,
                    entry.text,
                    review_line,
                    "Use warning callouts for unresolved figure/table associations.",
                    len(operations) + 1,
                )
            )
            normalized.append(make_line(entry.line_no, review_line))
            continue

        normalized.append(entry)
    return normalized


def _normalize_image_blocks(
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

        callout_entries: list[TLine] = []
        if next_index < len(entries) and CALLOUT_RE.match(entries[next_index].text):
            callout_entries.append(entries[next_index])
            next_index += 1
            while next_index < len(entries) and _is_review_detail_line(entries[next_index].text):
                callout_entries.append(entries[next_index])
                next_index += 1
            while next_index < len(entries) and not entries[next_index].text.strip():
                blanks.append(entries[next_index])
                next_index += 1

        if next_index < len(entries) and _is_caption_line(entries[next_index].text):
            _record_removed_caption_gaps(blanks, operations, make_operation)
            _record_removed_callout(callout_entries, operations, make_operation)
            normalized.append(entries[next_index])
            index = next_index + 1
            continue

        if callout_entries:
            _record_removed_caption_gaps(blanks, operations, make_operation)
            warning_lines = _missing_caption_warning_lines()
            before = "\n".join(callout.text for callout in callout_entries)
            after = "\n".join(warning_lines)
            if before != after:
                operations.append(
                    make_operation(
                        "normalize_missing_caption_warning",
                        entry.line_no,
                        before,
                        after,
                        "Normalize unresolved image caption review to a warning callout.",
                        len(operations) + 1,
                    )
                )
            normalized.extend(make_line(entry.line_no, line) for line in warning_lines)
            index = next_index
            continue

        warning_lines = _missing_caption_warning_lines()
        operations.append(
            make_operation(
                "mark_image_caption_needs_review",
                entry.line_no,
                entry.text,
                "\n".join([entry.text, *warning_lines]),
                "Mark images without nearby captions for review in refined.md.",
                len(operations) + 1,
            )
        )
        normalized.extend(make_line(entry.line_no, line) for line in warning_lines)
        normalized.extend(blanks)
        index += len(blanks) + 1
    return normalized


def format_caption_line(line: str) -> str:
    stripped = line.strip()
    stripped = re.sub(r"^>\s*", "", stripped)
    stripped = LOCALIZED_CAPTION_RE.sub("", stripped)
    stripped = re.sub(
        rf"^\*\*((?:fig(?:ure)?|table)\s*{FLOAT_NUMBER_PATTERN})\*\*\s*[:.：]\s*",
        r"\1: ",
        stripped,
        flags=re.IGNORECASE,
    ).strip()

    match = FLOAT_LABEL_RE.search(stripped)
    if match is None:
        return f"> {stripped}"

    label = _canonical_float_label(match)
    punctuation = ":" if ":" in match.group("punc") else "."
    before = stripped[: match.start()].strip(" .:：;-")
    after = stripped[match.end() :].strip()
    caption_text = " ".join(part for part in [before, after] if part)
    if not caption_text:
        return f"> {label}{punctuation}"
    return f"> {label}{punctuation} {caption_text}"


def _move_interrupted_image_blocks(
    entries: list[TLine],
    operations: list[DeterministicNormalizationOperation],
    *,
    make_line: LineFactory[TLine],
    make_operation: OperationFactory,
) -> list[TLine]:
    result = list(entries)
    index = 0
    while index < len(result):
        if not IMAGE_RE.match(result[index].text):
            index += 1
            continue

        block_start = index
        block_end = _image_block_end(result, block_start)
        prev_index = _previous_content_index(result, block_start)
        next_index = _next_content_index(result, block_end + 1)
        if (
            prev_index is None
            or next_index is None
            or not _is_interrupted_sentence_pair(result[prev_index].text, result[next_index].text)
        ):
            index = block_end + 1
            continue

        paragraph_end = _paragraph_end(result, next_index)
        block_entries = result[block_start : block_end + 1]
        before = "\n".join(entry.text for entry in result[prev_index : paragraph_end + 1])
        joined_line = f"{result[prev_index].text.rstrip()} {result[next_index].text.lstrip()}"
        rebuilt = result[:block_start]
        while rebuilt and not rebuilt[-1].text.strip():
            rebuilt.pop()
        rebuilt[-1] = make_line(result[prev_index].line_no, joined_line)
        rebuilt.extend(result[next_index + 1 : paragraph_end + 1])
        rebuilt.append(make_line(result[prev_index].line_no, ""))
        rebuilt.extend(block_entries)
        rebuilt.append(make_line(result[prev_index].line_no, ""))
        rebuilt.extend(result[paragraph_end + 1 :])
        preview_end = prev_index + len(block_entries) + 3
        after = "\n".join(entry.text for entry in rebuilt[prev_index:preview_end])
        operations.append(
            make_operation(
                "move_interrupted_image_block",
                result[block_start].line_no,
                before,
                after,
                (
                    "Move a figure block out of a running sentence and join "
                    "the interrupted paragraph."
                ),
                len(operations) + 1,
            )
        )
        result = rebuilt
        index = prev_index + len(block_entries) + 3
    return result


def _is_caption_line(line: str) -> bool:
    return bool(CAPTION_AT_START_RE.match(line) or LOCALIZED_CAPTION_RE.match(line))


def _normalize_review_callout_line(line: str) -> str:
    if CAUTION_RE.match(line):
        return ">[!warning]"
    return line


def _is_review_detail_line(line: str) -> bool:
    return bool(
        line.strip().startswith(">")
        and not CALLOUT_RE.match(line)
        and not _is_caption_line(line)
    )


def _missing_caption_warning_lines() -> list[str]:
    return [
        ">[!warning]",
        "> No reliable caption was matched near this image; verify against the source PDF.",
    ]


def _canonical_float_label(match: re.Match[str]) -> str:
    kind = "Table" if match.group("kind").lower().startswith("table") else "Figure"
    return f"{kind} {match.group('number').strip()}"


def _image_block_end(entries: Sequence[TLine], start: int) -> int:
    end = start
    index = start + 1
    while index < len(entries):
        text = entries[index].text
        if not text.strip() or CALLOUT_RE.match(text) or _is_caption_line(text):
            end = index
            index += 1
            continue
        break
    while end > start and not entries[end].text.strip():
        end -= 1
    return end


def _previous_content_index(entries: Sequence[TLine], before_index: int) -> int | None:
    index = before_index - 1
    while index >= 0:
        if entries[index].text.strip():
            return index
        index -= 1
    return None


def _next_content_index(entries: Sequence[TLine], start_index: int) -> int | None:
    index = start_index
    while index < len(entries):
        if entries[index].text.strip():
            return index
        index += 1
    return None


def _paragraph_end(entries: Sequence[TLine], start_index: int) -> int:
    index = start_index
    while index + 1 < len(entries):
        next_text = entries[index + 1].text
        if not next_text.strip() or _is_structural_line(next_text):
            break
        index += 1
    return index


def _is_interrupted_sentence_pair(before: str, after: str) -> bool:
    before_text = before.strip()
    after_text = after.strip()
    return (
        bool(before_text)
        and bool(after_text)
        and not SENTENCE_END_RE.search(before_text)
        and _is_running_text(before_text)
        and _looks_like_sentence_continuation(after_text)
    )


def _is_running_text(line: str) -> bool:
    return not _is_structural_line(line) and not IMAGE_RE.match(line)


def _is_structural_line(line: str) -> bool:
    return bool(
        HEADING_RE.match(line)
        or TABLE_BLOCK_RE.match(line)
        or CALLOUT_RE.match(line)
        or _is_caption_line(line)
        or line.strip().startswith(">")
    )


def _looks_like_sentence_continuation(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if stripped[0].islower():
        return True
    return stripped.startswith(
        ("to ", "and ", "or ", "but ", "while ", "often ", "which ", "that ")
    )


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


def _record_removed_callout(
    callout_entries: list[TLine],
    operations: list[DeterministicNormalizationOperation],
    make_operation: OperationFactory,
) -> None:
    if not callout_entries:
        return
    before = "\n".join(entry.text for entry in callout_entries)
    operations.append(
        make_operation(
            "remove_redundant_caption_review_callout",
            callout_entries[0].line_no,
            before,
            "",
            "Remove stale missing-caption review callout when a usable caption is present.",
            len(operations) + 1,
        )
    )


__all__ = ["normalize_image_annotations"]
