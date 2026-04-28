from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
import hashlib
import re

from .image_annotations import normalize_image_annotations
from .parsing import (
    DeterministicNormalizationOperation,
    DeterministicNormalizationReport,
)


HEADING_PREFIX_RE = re.compile(r"^(?P<hashes>#{1,6})\s+(?P<title>.+?)\s*$")
NUMBERED_HEADING_RE = re.compile(
    r"^(?P<number>\d+(?:\.\d+)*)(?:\.)?\s+(?P<title>\S.{0,180})$"
)
LETTER_HEADING_RE = re.compile(
    r"^(?P<number>[A-H])(?:\.)?\s+(?P<title>\S.{0,180})$"
)
APPENDIX_CHILD_HEADING_RE = re.compile(
    r"^(?P<number>[A-H](?:\.\d+)+)(?:\.)?\s+(?P<title>\S.{0,180})$"
)
BULLET_RE = re.compile(r"^(?P<indent>\s*)[\u2022\u25cf\u25aa]\s+")
SENTENCE_END_RE = re.compile(r"[.!?。！？]\s*$")
SPACED_LETTER_RUN_RE = re.compile(r"(?<![A-Za-z])(?:[A-Za-z]\s+){2,}[A-Za-z](?![A-Za-z])")
TERM_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9-]{1,}\b")
EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w.-]+\.\w+\b")
EMAIL_FRAGMENT_RE = re.compile(r"\b(?:[a-z0-9-]+\.)+[a-z]{2,}\b", re.IGNORECASE)
AUTHOR_HEADER_RE = re.compile(r"^\s*Authors?\s*:", re.IGNORECASE)
INSTITUTION_START_RE = re.compile(
    r"\b("
    r"University|Institute|College|School|Department|Laboratory|Lab|"
    r"Corporation|Inc\.?|Ltd\.?|Microsoft|Google|Meta|OpenAI|"
    r"Xiaohongshu|Beihang|Shanghai|Amsterdam|Oxford|Carnegie|CMU"
    r")\b",
    re.IGNORECASE,
)
AUTHOR_TOKEN_RE = re.compile(r"^[A-Z][A-Za-z.'-]*[*†∗]?$")

MAX_HEADING_CHARS = 180
MAX_HEADING_WORDS = 18
METADATA_WINDOW_LINES = 40


@dataclass(frozen=True, slots=True)
class _LineEntry:
    line_no: int
    text: str


def normalize_markdown_structure(
    markdown_text: str,
    *,
    source_hash: str,
    expected_title: str = "",
) -> tuple[str, DeterministicNormalizationReport]:
    """Apply safe, deterministic structure fixes after LLM patches."""

    entries = [
        _LineEntry(line_no=index, text=line)
        for index, line in enumerate(markdown_text.splitlines(), start=1)
    ]
    operations: list[DeterministicNormalizationOperation] = []
    entries = _normalize_front_matter_metadata(entries, operations)
    first_content_line = _first_content_line(entries)
    term_case_map = _build_term_case_map(markdown_text)
    entries = _normalize_lines(
        entries,
        first_content_line,
        expected_title,
        term_case_map,
        operations,
    )
    entries = normalize_image_annotations(
        entries,
        operations,
        make_line=_LineEntry,
        make_operation=_operation_from_args,
    )
    entries = _collapse_blank_runs(entries, operations)

    normalized_text = "\n".join(entry.text for entry in entries).rstrip() + "\n"
    report = DeterministicNormalizationReport(
        source_hash=source_hash,
        input_hash=_sha256_text(markdown_text),
        output_hash=_sha256_text(normalized_text),
        changed=normalized_text != markdown_text.rstrip() + "\n",
        operation_count=len(operations),
        operations=operations,
    )
    return normalized_text, report


def _normalize_lines(
    entries: list[_LineEntry],
    first_content_line: int | None,
    expected_title: str,
    term_case_map: dict[str, str],
    operations: list[DeterministicNormalizationOperation],
) -> list[_LineEntry]:
    normalized: list[_LineEntry] = []
    for entry in entries:
        after = entry.text.rstrip()
        operation_types: list[str] = []
        rationales: list[str] = []
        if after != entry.text:
            operation_types.append("trim_trailing_whitespace")
            rationales.append("Remove trailing whitespace without changing content.")

        metadata_line = _normalize_metadata_line(after, entry.line_no)
        if metadata_line != after:
            after = metadata_line
            operation_types.append("normalize_metadata_spacing")
            rationales.append("Repair safe spacing artifacts in the title/author metadata window.")

        title_line = _normalize_title_line(
            after,
            entry.line_no,
            first_content_line,
            expected_title,
        )
        if title_line != after:
            after = title_line
            operation_types.append("normalize_title_metadata")
            rationales.append(
                "Use known Paper metadata to repair a high-confidence title OCR artifact."
            )

        heading = _normalize_heading(after, entry.line_no, first_content_line)
        if heading != after:
            after = heading
            operation_types.append("normalize_heading_level")
            rationales.append("Convert a paper section marker to stable Markdown heading syntax.")

        bullet = BULLET_RE.sub(r"\g<indent>- ", after)
        if bullet != after:
            after = bullet
            operation_types.append("normalize_bullet_marker")
            rationales.append("Use a Markdown bullet marker while preserving list text.")

        term_case_line = _restore_known_term_case(after, term_case_map)
        if term_case_line != after:
            after = term_case_line
            operation_types.append("restore_term_case")
            rationales.append(
                "Restore casing for technical terms observed elsewhere in the paper."
            )

        if after != entry.text:
            operations.append(
                _operation(
                    operation_type="+".join(operation_types),
                    line_no=entry.line_no,
                    before=entry.text,
                    after=after,
                    rationale=" ".join(rationales),
                    index=len(operations) + 1,
                )
            )
        normalized.append(_LineEntry(line_no=entry.line_no, text=after))
    return normalized


def _normalize_front_matter_metadata(
    entries: list[_LineEntry],
    operations: list[DeterministicNormalizationOperation],
) -> list[_LineEntry]:
    abstract_index = _find_abstract_index(entries)
    first_content_index = _first_content_index(entries)
    if (
        abstract_index is None
        or first_content_index is None
        or abstract_index > METADATA_WINDOW_LINES
    ):
        return entries

    metadata_start = first_content_index + 1
    while metadata_start < abstract_index:
        text = entries[metadata_start].text.strip()
        if not text or text.startswith("- "):
            metadata_start += 1
            continue
        break
    if metadata_start >= abstract_index:
        return entries

    metadata_entries = entries[metadata_start:abstract_index]
    if any(AUTHOR_HEADER_RE.match(entry.text) for entry in metadata_entries):
        return entries

    authors, institutions, extras = _extract_front_matter(metadata_entries)
    if not authors or (not institutions and not extras):
        return entries

    replacement_lines = [f"Authors: {', '.join(authors)}"]
    if institutions:
        replacement_lines.append(f"Institutions: {', '.join(institutions)}")
    replacement_lines.extend(extras)
    replacement_lines.append("")

    before = "\n".join(entry.text for entry in metadata_entries)
    after = "\n".join(replacement_lines)
    operations.append(
        _operation(
            operation_type="normalize_author_institution_metadata",
            line_no=entries[metadata_start].line_no,
            before=before,
            after=after,
            rationale="Normalize paper front matter to Authors/Institutions and omit email addresses.",
            index=len(operations) + 1,
        )
    )
    replacement_entries = [
        _LineEntry(line_no=entries[metadata_start].line_no, text=line)
        for line in replacement_lines
    ]
    return entries[:metadata_start] + replacement_entries + entries[abstract_index:]


def _find_abstract_index(entries: list[_LineEntry]) -> int | None:
    for index, entry in enumerate(entries[:METADATA_WINDOW_LINES]):
        content = HEADING_PREFIX_RE.sub(r"\g<title>", entry.text.strip()).strip()
        if content.lower() == "abstract":
            return index
    return None


def _first_content_index(entries: list[_LineEntry]) -> int | None:
    for index, entry in enumerate(entries):
        if entry.text.strip():
            return index
    return None


def _extract_front_matter(entries: list[_LineEntry]) -> tuple[list[str], list[str], list[str]]:
    authors: list[str] = []
    institutions: list[str] = []
    extras: list[str] = []
    for entry in entries:
        line = entry.text.strip()
        if not line:
            continue
        if EMAIL_RE.fullmatch(line) or _looks_like_email_fragment(line):
            continue
        line_without_email = EMAIL_RE.sub("", line).strip(" ,;<>")
        if not line_without_email:
            continue
        if line_without_email.startswith("(") and line_without_email.endswith(")"):
            extras.append(line_without_email)
            continue

        author_text, institution_text = _split_author_institution_line(line_without_email)
        if _looks_like_author_text(author_text):
            authors.extend(_split_author_names(author_text))
        elif author_text:
            extras.append(_clean_metadata_value(author_text))
        if institution_text:
            institutions.append(_clean_metadata_value(institution_text))
    return _dedupe(authors), _dedupe(institutions), _dedupe(extras)


def _looks_like_email_fragment(line: str) -> bool:
    stripped = line.strip(" ,;")
    if not stripped:
        return False
    if "{" in stripped or "}" in stripped:
        letters = [char for char in stripped if char.isalpha()]
        return bool(letters) and not any(char.isupper() for char in letters)
    if "@" in stripped:
        remaining = EMAIL_RE.sub("", stripped)
        return not any(char.isupper() for char in remaining if char.isalpha())
    return (
        EMAIL_FRAGMENT_RE.fullmatch(stripped) is not None
        and not any(char.isupper() for char in stripped if char.isalpha())
    )


def _split_author_institution_line(line: str) -> tuple[str, str]:
    match = INSTITUTION_START_RE.search(line)
    if match is None:
        return line, ""
    if match.start() == 0:
        return "", line
    prefix = line[: match.start()].strip(" ,;")
    if "," not in prefix:
        return "", line
    author_text = prefix
    institution_text = line[match.start() :].strip(" ,;")
    return author_text, institution_text


def _split_author_names(text: str) -> list[str]:
    cleaned = _clean_metadata_value(text)
    if not cleaned:
        return []
    comma_parts = [part.strip() for part in cleaned.split(",") if part.strip()]
    if len(comma_parts) > 1:
        return comma_parts

    tokens = cleaned.split()
    if (
        len(tokens) >= 2
        and len(tokens) % 2 == 0
        and all(AUTHOR_TOKEN_RE.match(token) for token in tokens)
    ):
        return [" ".join(tokens[index : index + 2]) for index in range(0, len(tokens), 2)]
    return [cleaned]


def _looks_like_author_text(text: str) -> bool:
    cleaned = _clean_metadata_value(text)
    if not cleaned:
        return False
    comma_parts = [part.strip() for part in cleaned.split(",") if part.strip()]
    if len(comma_parts) > 1:
        return all(_looks_like_author_name_part(part) for part in comma_parts)
    return _looks_like_author_name_part(cleaned)


def _looks_like_author_name_part(text: str) -> bool:
    cleaned = _clean_metadata_value(text)
    tokens = cleaned.split()
    return (
        len(tokens) >= 2
        and all(AUTHOR_TOKEN_RE.match(token) for token in tokens)
    )


def _clean_metadata_value(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("∗", "*")).strip(" ,;")


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        key = value.lower()
        if not value or key in seen:
            continue
        seen.add(key)
        deduped.append(value)
    return deduped


def _normalize_heading(
    line: str,
    line_no: int,
    first_content_line: int | None,
) -> str:
    stripped = line.strip()
    if not stripped or len(stripped) > MAX_HEADING_CHARS:
        return line

    match = HEADING_PREFIX_RE.match(stripped)
    had_markdown_heading = match is not None
    content = match.group("title").strip() if match else stripped
    if not content:
        return line
    if line_no == first_content_line and not _is_section_heading(content):
        return line

    canonical = _canonical_special_heading(content)
    if canonical is not None and (had_markdown_heading or not SENTENCE_END_RE.search(content)):
        return f"## {canonical}"

    numbered_match = NUMBERED_HEADING_RE.match(content)
    if numbered_match and _looks_like_heading_title(
        numbered_match.group("title"),
        had_markdown_heading=had_markdown_heading,
    ):
        number = numbered_match.group("number")
        level = min(6, number.count(".") + 2)
        return f"{'#' * level} {number} {numbered_match.group('title').strip()}"

    appendix_child_match = APPENDIX_CHILD_HEADING_RE.match(content)
    if appendix_child_match and _looks_like_heading_title(
        appendix_child_match.group("title"),
        had_markdown_heading=had_markdown_heading,
    ):
        number = appendix_child_match.group("number")
        level = min(6, number.count(".") + 2)
        return f"{'#' * level} {number} {appendix_child_match.group('title').strip()}"

    letter_match = LETTER_HEADING_RE.match(content)
    if letter_match and _looks_like_heading_title(
        letter_match.group("title"),
        had_markdown_heading=had_markdown_heading,
    ):
        return f"## {letter_match.group('number')} {letter_match.group('title').strip()}"

    if had_markdown_heading and match is not None:
        return f"{match.group('hashes')} {content}"
    return line


def _normalize_metadata_line(line: str, line_no: int) -> str:
    if line_no > METADATA_WINDOW_LINES or not line.strip() or len(line) > MAX_HEADING_CHARS:
        return line
    normalized = re.sub(r"\b([A-Z])\s+\.\s+", r"\1. ", line)
    normalized = re.sub(r"\s+([,;:])", r"\1", normalized)
    normalized = re.sub(r"([,;:])(?=\S)", r"\1 ", normalized)
    normalized = re.sub(r"\s+-\s+", "-", normalized)
    return SPACED_LETTER_RUN_RE.sub(_join_spaced_letters, normalized)


def _normalize_title_line(
    line: str,
    line_no: int,
    first_content_line: int | None,
    expected_title: str,
) -> str:
    if not expected_title.strip() or line_no != first_content_line:
        return line
    match = HEADING_PREFIX_RE.match(line.strip())
    if match is None:
        return line
    current_title = match.group("title").strip()
    if _title_similarity(current_title, expected_title) < 0.82:
        return line
    return f"# {expected_title.strip()}"


def _title_similarity(current_title: str, expected_title: str) -> float:
    current = _title_key(current_title)
    expected = _title_key(expected_title)
    if not current or not expected:
        return 0.0
    return SequenceMatcher(None, current, expected).ratio()


def _title_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _join_spaced_letters(match: re.Match[str]) -> str:
    return match.group(0).replace(" ", "")


def _build_term_case_map(markdown_text: str) -> dict[str, str]:
    variants: dict[str, dict[str, int]] = {}
    for match in TERM_RE.finditer(markdown_text):
        token = match.group(0)
        if not _has_internal_case(token):
            continue
        key = token.lower()
        variants.setdefault(key, {})
        variants[key][token] = variants[key].get(token, 0) + 1
    return {
        key: sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]
        for key, counts in variants.items()
    }


def _has_internal_case(token: str) -> bool:
    if not any(char.islower() for char in token) or not any(char.isupper() for char in token):
        return False
    segments = [segment for segment in re.split(r"[-_]", token) if segment]
    if not segments:
        return False
    title_case_segments = all(
        len(segment) > 1 and segment[0].isupper() and segment[1:].islower()
        for segment in segments
    )
    return not title_case_segments and any(
        any(char.isupper() for char in segment[1:])
        for segment in segments
    )


def _restore_known_term_case(line: str, term_case_map: dict[str, str]) -> str:
    if not term_case_map:
        return line

    def replace(match: re.Match[str]) -> str:
        token = match.group(0)
        return term_case_map.get(token.lower(), token)

    return TERM_RE.sub(replace, line)


def _canonical_special_heading(content: str) -> str | None:
    cleaned = content.strip().strip(":")
    normalized = re.sub(r"\s+", " ", cleaned).upper()
    if normalized in {"ABSTRACT", "SUMMARY"}:
        return "Abstract"
    if normalized in {"REFERENCES", "REFERENCE"}:
        return "References"
    if normalized in {"ACKNOWLEDGMENTS", "ACKNOWLEDGEMENTS"}:
        return "Acknowledgments"
    if normalized in {"APPENDIX", "APPENDICES"}:
        return "Appendix"
    if normalized.startswith("APPENDIX "):
        return "Appendix " + cleaned[len("APPENDIX ") :].strip()
    return None


def _is_section_heading(content: str) -> bool:
    return (
        _canonical_special_heading(content) is not None
        or NUMBERED_HEADING_RE.match(content) is not None
        or LETTER_HEADING_RE.match(content) is not None
    )


def _looks_like_heading_title(title: str, *, had_markdown_heading: bool) -> bool:
    stripped = title.strip()
    if not stripped or len(stripped.split()) > MAX_HEADING_WORDS:
        return False
    if had_markdown_heading:
        return True
    if SENTENCE_END_RE.search(stripped):
        return False
    letters = [char for char in stripped if char.isalpha()]
    if not letters:
        return False
    uppercase_ratio = sum(char.isupper() for char in letters) / len(letters)
    return uppercase_ratio >= 0.45 or stripped.istitle()


def _collapse_blank_runs(
    entries: list[_LineEntry],
    operations: list[DeterministicNormalizationOperation],
) -> list[_LineEntry]:
    normalized: list[_LineEntry] = []
    blank_count = 0
    for entry in entries:
        if entry.text.strip():
            blank_count = 0
            normalized.append(entry)
            continue
        blank_count += 1
        if blank_count <= 2:
            normalized.append(entry)
            continue
        operations.append(
            _operation(
                operation_type="collapse_excess_blank_line",
                line_no=entry.line_no,
                before=entry.text,
                after="",
                rationale="Collapse blank runs to at most two lines.",
                index=len(operations) + 1,
            )
        )
    return normalized


def _first_content_line(entries: list[_LineEntry]) -> int | None:
    for entry in entries:
        if entry.text.strip():
            return entry.line_no
    return None


def _operation(
    *,
    operation_type: str,
    line_no: int,
    before: str,
    after: str,
    rationale: str,
    index: int,
) -> DeterministicNormalizationOperation:
    return DeterministicNormalizationOperation(
        operation_id=f"det_{index:04d}",
        operation_type=operation_type,
        line_no=line_no,
        before=before,
        after=after,
        rationale=rationale,
    )


def _operation_from_args(
    operation_type: str,
    line_no: int,
    before: str,
    after: str,
    rationale: str,
    index: int,
) -> DeterministicNormalizationOperation:
    return _operation(
        operation_type=operation_type,
        line_no=line_no,
        before=before,
        after=after,
        rationale=rationale,
        index=index,
    )


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


__all__ = ["normalize_markdown_structure"]
