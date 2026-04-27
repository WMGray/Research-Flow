from __future__ import annotations

import re
from typing import Any


CANONICAL_SECTION_ORDER: tuple[tuple[str, str], ...] = (
    ("related_work", "Background and Related Work"),
    ("method", "Method"),
    ("experiment", "Experiment"),
    ("appendix", "Appendix"),
    ("conclusion", "Conclusion"),
)
SECTION_ALIASES: dict[str, tuple[str, ...]] = {
    "related_work": ("introduction", "related work", "related works", "background"),
    "method": ("method", "our method", "methodology", "approach", "framework"),
    "experiment": ("experiment", "experiments", "empirical experiments", "evaluation", "results"),
    "appendix": ("appendix", "supplementary", "additional"),
    "conclusion": ("conclusion", "conclusions", "discussion", "conclusion and future work"),
}
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
SECTION_NUMBER_RE = re.compile(r"^(\d+(?:\.\d+)*)(?:\.)?\s+(.+)$")
APPENDIX_HEADING_RE = re.compile(r"^[a-h](?:\.\d+)*\s+.+$")
EXCLUDED_HEADING_PREFIXES = (
    "references",
    "reference",
    "bibliography",
    "acknowledgment",
    "acknowledgments",
    "acknowledgement",
    "acknowledgements",
)


def split_sections_deterministically(content: str) -> tuple[dict[str, str], dict[str, Any]]:
    section_lines: dict[str, list[str]] = {key: [] for key, _ in CANONICAL_SECTION_ORDER}
    headings: list[dict[str, Any]] = []
    excluded = excluded_line_numbers(content.splitlines())
    current_key: str | None = None

    for line_no, line in enumerate(content.splitlines(), start=1):
        heading = _parse_heading(line, line_no)
        if heading:
            headings.append(heading)
            matched_key = _canonical_key(heading)
            if matched_key:
                current_key = matched_key
            elif _ends_current_section(heading):
                current_key = None
        if current_key is not None and line_no not in excluded:
            section_lines[current_key].append(line)

    blocks = {
        key: "\n".join(lines).strip() + "\n"
        for key, lines in section_lines.items()
        if any(line.strip() for line in lines)
    }
    return blocks, {
        "status": "pass",
        "section_keys": sorted(blocks),
        "heading_count": len(headings),
        "excluded_line_count": len(excluded),
        "headings": headings[:80],
    }


def build_section_outline(content: str, *, max_headings: int = 140) -> str:
    lines = content.splitlines()
    headings = [
        heading
        for index, line in enumerate(lines, start=1)
        if (heading := _parse_heading(line, index))
    ]
    excluded = excluded_line_numbers(lines)
    rendered = [
        "# Section Split Evidence",
        f"line_count: {len(lines)}",
        "Ranges refer to full refined.md line numbers. The backend removes References/Bibliography/Acknowledgments from accepted ranges.",
        "",
        "## Metadata Window",
    ]
    rendered.extend(
        f"{index:05d}: {line[:240]}"
        for index, line in enumerate(lines[:24], start=1)
        if line.strip()
    )
    rendered.extend(["", "## Heading Outline With Local Evidence"])
    for heading in headings[:max_headings]:
        rendered.append(_format_heading(heading))
        rendered.extend(f"  snippet: {snippet}" for snippet in _heading_snippets(lines, heading, excluded))
    if len(headings) > max_headings:
        rendered.append(f"[truncated_headings count={len(headings) - max_headings}]")
    if excluded:
        rendered.extend(["", f"excluded_line_count: {len(excluded)}"])
    return "\n".join(rendered)


def excluded_line_numbers(lines: list[str]) -> set[int]:
    headings = [
        heading
        for index, line in enumerate(lines, start=1)
        if (heading := _parse_heading(line, index))
    ]
    excluded: set[int] = set()
    for index, heading in enumerate(headings):
        if not _is_excluded_heading(heading):
            continue
        start_line = int(heading["line_no"])
        end_line = len(lines)
        for next_heading in headings[index + 1 :]:
            if _is_appendix_heading(next_heading) or int(next_heading["level"]) <= int(heading["level"]):
                end_line = int(next_heading["line_no"]) - 1
                break
        excluded.update(range(start_line, end_line + 1))
    return excluded


def _parse_heading(line: str, line_no: int) -> dict[str, Any] | None:
    match = HEADING_RE.match(line.strip())
    if not match:
        return None
    level = len(match.group(1))
    body = match.group(2).strip()
    number = ""
    label = body
    if number_match := SECTION_NUMBER_RE.match(body.lower()):
        number, label = number_match.group(1), number_match.group(2).strip()
    elif APPENDIX_HEADING_RE.match(body.lower()):
        number, label = body.split(maxsplit=1)
    return {
        "line_no": line_no,
        "level": level,
        "raw": line,
        "label": label.lower(),
        "number": number.lower(),
        "is_major": _is_major_heading(level, number),
    }


def _canonical_key(heading: dict[str, Any]) -> str | None:
    if not heading["is_major"] or _is_excluded_heading(heading):
        return None
    label = str(heading["label"])
    number = str(heading["number"])
    return next(
        (
            key
            for key, aliases in SECTION_ALIASES.items()
            if any(label.startswith(alias) for alias in aliases)
            or (key == "appendix" and bool(number and number[0].isalpha()))
        ),
        None,
    )


def _ends_current_section(heading: dict[str, Any]) -> bool:
    return bool(heading["is_major"]) or _is_excluded_heading(heading)


def _is_major_heading(level: int, number: str) -> bool:
    return "." not in number if number else level <= 2


def _format_heading(heading: dict[str, Any]) -> str:
    excluded = _is_excluded_heading(heading)
    return (
        f"{int(heading['line_no']):05d}: level={heading['level']} "
        f"number={heading['number'] or '-'} major={str(heading['is_major']).lower()} "
        f"excluded={str(excluded).lower()} label={heading['label']} raw={heading['raw']}"
    )


def _is_excluded_heading(heading: dict[str, Any]) -> bool:
    label = str(heading["label"]).lower()
    raw = str(heading["raw"]).lstrip("#").strip().lower()
    return label.startswith(EXCLUDED_HEADING_PREFIXES) or raw.startswith(EXCLUDED_HEADING_PREFIXES)


def _is_appendix_heading(heading: dict[str, Any]) -> bool:
    label = str(heading["label"]).lower()
    number = str(heading["number"]).lower()
    raw = str(heading["raw"]).lstrip("#").strip().lower()
    return label.startswith(("appendix", "supplementary")) or raw.startswith(
        ("appendix", "supplementary")
    ) or bool(number and number[0].isalpha())


def _heading_snippets(
    lines: list[str],
    heading: dict[str, Any],
    excluded: set[int],
    *,
    max_snippets: int = 3,
) -> list[str]:
    snippets: list[str] = []
    start = int(heading["line_no"]) + 1
    for line_no in range(start, min(len(lines), start + 14) + 1):
        if line_no in excluded:
            continue
        line = lines[line_no - 1].strip()
        if not line or HEADING_RE.match(line):
            continue
        snippets.append(f"{line_no:05d}: {line[:220]}")
        if len(snippets) >= max_snippets:
            break
    return snippets


__all__ = [
    "CANONICAL_SECTION_ORDER",
    "build_section_outline",
    "excluded_line_numbers",
    "split_sections_deterministically",
]
