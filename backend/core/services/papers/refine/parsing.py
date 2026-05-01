from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Literal

from core.services.papers.models import utc_now


PatchOperation = Literal[
    "replace_span",
    "insert_after",
    "delete_span",
    "mark_needs_review",
]


@dataclass(frozen=True, slots=True)
class LineRecord:
    line_no: int
    text: str
    sha256: str


@dataclass(frozen=True, slots=True)
class LineIndex:
    source_path: str
    source_hash: str
    line_count: int
    char_count: int
    generated_at: str
    lines: list[LineRecord]


@dataclass(frozen=True, slots=True)
class RefineIssue:
    issue_id: str
    issue_type: str
    start_line: int
    end_line: int
    severity: str
    confidence: float
    description: str
    suggested_action: str
    needs_pdf_context: bool = False


@dataclass(frozen=True, slots=True)
class RefineDiagnosis:
    source_hash: str
    issues: list[RefineIssue] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class RefinePatch:
    patch_id: str
    issue_id: str
    op: PatchOperation
    start_line: int
    end_line: int
    replacement: str
    confidence: float
    rationale: str = ""


@dataclass(frozen=True, slots=True)
class PatchApplyReport:
    source_hash: str
    output_hash: str
    changed: bool
    applied_patch_ids: list[str]
    rejected_patches: list[dict[str, Any]]
    review_items: list[dict[str, Any]]


@dataclass(frozen=True, slots=True)
class DeterministicNormalizationOperation:
    operation_id: str
    operation_type: str
    line_no: int
    before: str
    after: str
    rationale: str


@dataclass(frozen=True, slots=True)
class DeterministicNormalizationReport:
    source_hash: str
    input_hash: str
    output_hash: str
    changed: bool
    operation_count: int
    operations: list[DeterministicNormalizationOperation]


@dataclass(frozen=True, slots=True)
class RefineVerifyReport:
    source_hash: str
    output_hash: str
    status: Literal["pass", "warning", "fail"]
    checks: list[dict[str, Any]]
    llm_verdict: dict[str, Any]


JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)
HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+\S+")
NUMBERED_HEADING_RE = re.compile(r"^\s*(?:\d+(?:\.\d+)*|[A-H])\s+[A-Z][A-Z0-9 ,:;()/'\-\u2013\u2014]+$")
FLOAT_NUMBER_PATTERN = r"(?:[A-Za-z]\.\d+(?:\.\d+)*|[A-Za-z]?\d+(?:\.\d+)*)"
CAPTION_RE = re.compile(
    rf"^\s*(?:fig(?:ure)?|table)\s*{FLOAT_NUMBER_PATTERN}",
    re.IGNORECASE,
)
IMAGE_RE = re.compile(r"^\s*!\[[^\]]*]\([^)]+\)")
TABLE_RE = re.compile(r"^\s*(?:<table\b|\|.+\|)", re.IGNORECASE)
OCR_SPLIT_RE = re.compile(r"[A-Za-z]-\s+[A-Za-z]|[A-Za-z]-[A-Z]{2,}")

DEFAULT_EVIDENCE_MAX_CHARS = 10_000
EVIDENCE_LINE_MAX_CHARS = 480


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_line_index(markdown_path: Path, markdown_text: str) -> LineIndex:
    lines = markdown_text.splitlines()
    return LineIndex(
        source_path=str(markdown_path),
        source_hash=sha256_text(markdown_text),
        line_count=len(lines),
        char_count=len(markdown_text),
        generated_at=utc_now(),
        lines=[
            LineRecord(
                line_no=index,
                text=line,
                sha256=sha256_text(line),
            )
            for index, line in enumerate(lines, start=1)
        ],
    )


def build_line_numbered_markdown(line_index: LineIndex) -> str:
    return "\n".join(
        f"{record.line_no:05d}: {record.text}" for record in line_index.lines
    )


def build_structural_evidence_markdown(
    line_index: LineIndex,
    *,
    max_chars: int = DEFAULT_EVIDENCE_MAX_CHARS,
    window_radius: int = 1,
) -> str:
    """Build compact, line-addressable evidence for LLM structural diagnosis."""

    full_markdown = build_line_numbered_markdown(line_index)
    if len(full_markdown) <= max_chars:
        return full_markdown

    candidate_lines = _candidate_line_numbers(line_index)
    windows = _merge_line_windows(
        candidate_lines,
        radius=window_radius,
        line_count=line_index.line_count,
    )
    header = "\n".join(
        [
            "# MinerU Structural Evidence",
            f"source_hash: {line_index.source_hash}",
            f"line_count: {line_index.line_count}",
            f"char_count: {line_index.char_count}",
            (
                "Only selected structural windows are shown. Line numbers refer to "
                "the complete source line_index.json."
            ),
            "",
        ]
    )
    blocks = [header]
    current_len = len(header)
    skipped = 0
    for start, end in windows:
        block = _format_window(line_index, start, end)
        if current_len + len(block) > max_chars:
            skipped += 1
            continue
        blocks.append(block)
        current_len += len(block)
    if skipped:
        blocks.append(f"\n[Skipped {skipped} lower-priority evidence windows due to model context budget.]\n")
    return "\n".join(blocks).rstrip()


def _candidate_line_numbers(line_index: LineIndex) -> list[int]:
    candidates: list[int] = []
    for record in line_index.lines:
        text = record.text.strip()
        if record.line_no <= 24:
            candidates.append(record.line_no)
            continue
        if _is_structural_candidate(text):
            candidates.append(record.line_no)
    if line_index.line_count:
        candidates.extend(range(max(1, line_index.line_count - 8), line_index.line_count + 1))
    return sorted(set(candidates))


def _is_structural_candidate(text: str) -> bool:
    if not text:
        return False
    return any(
        (
            HEADING_RE.match(text),
            NUMBERED_HEADING_RE.match(text),
            CAPTION_RE.match(text),
            IMAGE_RE.match(text),
            TABLE_RE.match(text),
            OCR_SPLIT_RE.search(text),
            len(text) > 1_200,
        )
    )


def _merge_line_windows(
    line_numbers: list[int],
    *,
    radius: int,
    line_count: int,
) -> list[tuple[int, int]]:
    windows: list[tuple[int, int]] = []
    for line_no in line_numbers:
        start = max(1, line_no - radius)
        end = min(line_count, line_no + radius)
        if windows and start <= windows[-1][1] + 1:
            previous_start, previous_end = windows[-1]
            windows[-1] = (previous_start, max(previous_end, end))
        else:
            windows.append((start, end))
    return windows


def _format_window(line_index: LineIndex, start_line: int, end_line: int) -> str:
    records = line_index.lines[start_line - 1 : end_line]
    lines = [f"\n--- lines {start_line}-{end_line} ---"]
    lines.extend(_format_evidence_line(record) for record in records)
    return "\n".join(lines)


def _format_evidence_line(record: LineRecord) -> str:
    text = record.text
    if len(text) > EVIDENCE_LINE_MAX_CHARS:
        text = (
            text[:EVIDENCE_LINE_MAX_CHARS].rstrip()
            + f" ... [truncated chars={len(record.text)} sha256={record.sha256}]"
        )
    return f"{record.line_no:05d}: {text}"


def extract_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    fence_match = JSON_FENCE_RE.match(stripped)
    if fence_match is not None:
        stripped = fence_match.group(1).strip()
    if not stripped.startswith("{"):
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start >= 0 and end > start:
            stripped = stripped[start : end + 1]
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        payload = json.loads(_escape_invalid_json_backslashes(stripped))
    if not isinstance(payload, dict):
        raise ValueError("LLM response must be a JSON object")
    return payload


def _escape_invalid_json_backslashes(text: str) -> str:
    """Escape raw LaTeX/Windows backslashes that LLMs often emit inside JSON strings."""

    valid_simple_escapes = {'"', "\\", "/", "b", "f", "n", "r", "t"}
    repaired: list[str] = []
    index = 0
    while index < len(text):
        char = text[index]
        if char != "\\":
            repaired.append(char)
            index += 1
            continue
        if index + 1 >= len(text):
            repaired.append("\\\\")
            index += 1
            continue
        next_char = text[index + 1]
        if next_char in valid_simple_escapes:
            repaired.append(text[index : index + 2])
            index += 2
            continue
        if (
            next_char == "u"
            and index + 5 < len(text)
            and re.fullmatch(r"u[0-9a-fA-F]{4}", text[index + 1 : index + 6])
        ):
            repaired.append(text[index : index + 6])
            index += 6
            continue
        repaired.append("\\\\")
        index += 1
    return "".join(repaired)


def diagnosis_from_payload(
    payload: dict[str, Any],
    *,
    source_hash: str,
    line_count: int,
) -> RefineDiagnosis:
    raw_issues = payload.get("issues", [])
    if not isinstance(raw_issues, list):
        raw_issues = []
    issues: list[RefineIssue] = []
    for index, item in enumerate(raw_issues, start=1):
        if not isinstance(item, dict):
            continue
        start_line = _bounded_line(item.get("start_line"), 1, line_count)
        end_line = _bounded_line(item.get("end_line"), start_line, line_count)
        if end_line < start_line:
            start_line, end_line = end_line, start_line
        issues.append(
            RefineIssue(
                issue_id=str(item.get("issue_id") or f"issue_{index:03d}"),
                issue_type=str(item.get("type") or item.get("issue_type") or "unknown"),
                start_line=start_line,
                end_line=end_line,
                severity=str(item.get("severity") or "medium"),
                confidence=float(item.get("confidence") or 0.0),
                description=str(item.get("description") or ""),
                suggested_action=str(item.get("suggested_action") or ""),
                needs_pdf_context=bool(item.get("needs_pdf_context", False)),
            )
        )
    return RefineDiagnosis(
        source_hash=str(payload.get("source_hash") or source_hash),
        issues=issues,
    )


def patches_from_payload(
    payload: dict[str, Any],
    *,
    line_count: int,
) -> list[RefinePatch]:
    raw_patches = payload.get("patches", [])
    if not isinstance(raw_patches, list):
        raw_patches = []
    patches: list[RefinePatch] = []
    for index, item in enumerate(raw_patches, start=1):
        if not isinstance(item, dict):
            continue
        start_line = _bounded_line(item.get("start_line"), 1, line_count)
        end_line = _bounded_line(item.get("end_line"), start_line, line_count)
        if end_line < start_line:
            start_line, end_line = end_line, start_line
        patches.append(
            RefinePatch(
                patch_id=str(item.get("patch_id") or f"patch_{index:03d}"),
                issue_id=str(item.get("issue_id") or ""),
                op=str(item.get("op") or "mark_needs_review"),
                start_line=start_line,
                end_line=end_line,
                replacement=str(item.get("replacement") or ""),
                confidence=float(item.get("confidence") or 0.0),
                rationale=str(item.get("rationale") or ""),
            )
        )
    return patches


def _bounded_line(value: object, default: int, line_count: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(1, min(parsed, max(line_count, 1)))
