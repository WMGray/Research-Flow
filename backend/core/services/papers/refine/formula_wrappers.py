from __future__ import annotations

FORMULA_WRAPPER = "equation_inline"
FORMULA_WRAPPER_END = " text"


def normalize_formula_wrappers(line: str) -> str:
    """Convert MinerU inline formula wrappers to Markdown math."""

    if FORMULA_WRAPPER not in line:
        return line

    parts: list[str] = []
    cursor = 0
    changed = False
    while cursor < len(line):
        wrapper_start = line.find(FORMULA_WRAPPER, cursor)
        if wrapper_start == -1:
            parts.append(line[cursor:])
            break

        payload_start = wrapper_start + len(FORMULA_WRAPPER)
        if payload_start < len(line) and not line[payload_start].isspace():
            parts.append(line[cursor:payload_start])
            cursor = payload_start
            continue

        while payload_start < len(line) and line[payload_start].isspace():
            payload_start += 1

        payload_match = _find_payload(line, payload_start)
        if payload_match is None:
            parts.append(line[cursor:payload_start])
            cursor = payload_start
            continue

        payload, consume_end = payload_match
        if not _looks_like_formula_payload(payload):
            parts.append(line[cursor:payload_start])
            cursor = payload_start
            continue

        parts.append(line[cursor:wrapper_start])
        parts.append(f"${payload}$")
        cursor = consume_end
        changed = True

    return "".join(parts) if changed else line


def _find_payload(line: str, payload_start: int) -> tuple[str, int] | None:
    search_start = payload_start
    while True:
        end_start = line.find(FORMULA_WRAPPER_END, search_start)
        if end_start == -1:
            return None

        consume_end = end_start + len(FORMULA_WRAPPER_END)
        if _is_wrapper_boundary(line, consume_end):
            payload = line[payload_start:end_start].strip()
            payload, consume_end = _consume_balancing_suffix(line, payload, consume_end)
            return payload, consume_end

        search_start = consume_end


def _is_wrapper_boundary(line: str, index: int) -> bool:
    return (
        index >= len(line)
        or line[index].isspace()
        or line[index] in ".,;:)]}"
    )


def _consume_balancing_suffix(line: str, payload: str, consume_end: int) -> tuple[str, int]:
    if not payload:
        return payload, consume_end

    closing = _missing_closing_delimiter(payload)
    if closing is None:
        return payload, consume_end

    suffix_start = consume_end
    while suffix_start < len(line) and line[suffix_start].isspace():
        suffix_start += 1
    if suffix_start >= len(line) or line[suffix_start] != closing:
        return payload, consume_end

    return f"{payload} {closing}", suffix_start + 1


def _missing_closing_delimiter(payload: str) -> str | None:
    pairs = {"(": ")", "[": "]", "{": "}"}
    opening = payload[0]
    closing = pairs.get(opening)
    if closing is None:
        return None
    if payload.count(opening) <= payload.count(closing):
        return None
    return closing


def _looks_like_formula_payload(payload: str) -> bool:
    if not payload:
        return False
    if "$" in payload:
        return False
    return any(
        marker in payload
        for marker in (
            "\\",
            "_",
            "^",
            "{",
            "}",
            "=",
            "%",
            "(",
            ")",
        )
    ) or len(payload.split()) <= 3


__all__ = ["normalize_formula_wrappers"]
