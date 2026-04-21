from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
NUMBERED_HEADING_RE = re.compile(r"^(?:section\s+)?(?P<num>\d+(?:\.\d+)*)(?:[\.\)]|\s)+(?:\s*)(?P<title>.+)$", re.IGNORECASE)
APPENDIX_HEADING_RE = re.compile(r"^(?:appendix\s+)?(?P<label>[A-Z])(?:[\.\)]|\s+)(?P<title>.+)$")

TARGET_SECTION_ORDER = ["introduction", "method", "experiment", "result", "conclusion"]
STOP_KEYS = {"references", "appendix"}
SECTION_FILE_NAMES = {
    "introduction": "introduction.md",
    "method": "method.md",
    "experiment": "experiment.md",
    "result": "result.md",
    "conclusion": "conclusion.md",
}

SECTION_ALIASES: dict[str, tuple[str, ...]] = {
    "abstract": ("abstract",),
    "introduction": ("introduction", "motivating work", "background", "related work", "related works", "preliminary", "preliminaries", "motivation"),
    "method": ("method", "methods", "methodology", "approach", "approaches", "proposed method", "proposed approach", "framework", "architecture", "model", "models"),
    "experiment": ("experiments", "experiment", "evaluation", "experimental setup", "implementation details", "implementation", "datasets and settings", "dataset", "datasets", "settings"),
    "result": ("results", "main results", "quantitative results", "qualitative analysis", "qualitative results", "visual examples", "comparisons", "comparison", "analysis", "ablation", "ablation study", "discussion", "results and discussion"),
    "conclusion": ("conclusion", "conclusions", "future work", "conclusion and future work"),
    "references": ("references", "bibliography"),
    "appendix": ("appendix", "supplementary material"),
}


@dataclass(frozen=True, slots=True)
class ParsedPaperSection:
    key: str
    title: str
    text: str
    char_count: int


@dataclass(frozen=True, slots=True)
class HeadingEntry:
    line_index: int
    level: int
    raw_title: str
    normalized_title: str
    key: str | None
    structural: bool


@dataclass(frozen=True, slots=True)
class HeadingChunk:
    title: str
    key: str | None
    level: int
    line_index: int
    text: str


@dataclass(frozen=True, slots=True)
class SectionArtifacts:
    section_dir: Path
    sections: list[ParsedPaperSection]
    full_text: str


def normalize_heading_title(title: str) -> str:
    title = title.strip()
    numbered = NUMBERED_HEADING_RE.match(title)
    if numbered is not None:
        title = numbered.group("title")
    appendix = APPENDIX_HEADING_RE.match(title)
    if appendix is not None:
        title = appendix.group("title")
    title = title.strip(" .:-#")
    title = re.sub(r"\s+", " ", title)
    return title.lower()


def classify_heading(title: str) -> str | None:
    lowered = normalize_heading_title(title)
    appendix = APPENDIX_HEADING_RE.match(title.strip())
    if appendix is not None:
        return "appendix"
    for key, aliases in SECTION_ALIASES.items():
        if lowered in aliases:
            return key
    for key, aliases in SECTION_ALIASES.items():
        if any(alias in lowered for alias in aliases):
            return key
    return None


def is_structural_heading(title: str, key: str | None) -> bool:
    if key in {"abstract", "introduction", "method", "experiment", "result", "conclusion", "references", "appendix"}:
        return True
    if NUMBERED_HEADING_RE.match(title):
        return True
    return False


def parse_headings(lines: list[str]) -> list[HeadingEntry]:
    headings: list[HeadingEntry] = []
    for line_index, line in enumerate(lines):
        match = HEADING_RE.match(line)
        if match is None:
            continue
        raw_title = match.group(2).strip()
        key = classify_heading(raw_title)
        headings.append(
            HeadingEntry(
                line_index=line_index,
                level=len(match.group(1)),
                raw_title=raw_title,
                normalized_title=normalize_heading_title(raw_title),
                key=key,
                structural=is_structural_heading(raw_title, key),
            )
        )
    return headings


def next_structural_heading(headings: list[HeadingEntry], current_index: int, default_end: int) -> int:
    for heading in headings:
        if heading.line_index > current_index and heading.structural:
            return heading.line_index
    return default_end


def find_main_body_bounds(headings: list[HeadingEntry], total_lines: int) -> tuple[int, int]:
    abstract_heading = next((heading for heading in headings if heading.key == "abstract"), None)
    if abstract_heading is None:
        start_line = next((heading.line_index for heading in headings if heading.structural), 0)
    else:
        start_line = next_structural_heading(headings, abstract_heading.line_index, total_lines)

    stop_line = total_lines
    for heading in headings:
        if heading.line_index < start_line:
            continue
        if heading.key in STOP_KEYS:
            stop_line = heading.line_index
            break
    return start_line, stop_line


def section_text_from_lines(lines: list[str], start: int, end: int) -> str:
    return "\n".join(lines[start:end]).strip()


def build_main_body_chunks(markdown_text: str) -> list[HeadingChunk]:
    lines = markdown_text.splitlines()
    headings = parse_headings(lines)
    start_line, stop_line = find_main_body_bounds(headings, len(lines))
    body_headings = [
        heading
        for heading in headings
        if heading.structural and start_line <= heading.line_index < stop_line and heading.key not in STOP_KEYS
    ]

    chunks: list[HeadingChunk] = []
    for index, heading in enumerate(body_headings):
        end_line = body_headings[index + 1].line_index if index + 1 < len(body_headings) else stop_line
        chunk_text = section_text_from_lines(lines, heading.line_index, end_line)
        chunks.append(
            HeadingChunk(
                title=heading.raw_title,
                key=heading.key,
                level=heading.level,
                line_index=heading.line_index,
                text=chunk_text,
            )
        )
    return chunks


def explicit_bucket(chunk: HeadingChunk) -> str | None:
    if chunk.key in TARGET_SECTION_ORDER:
        return chunk.key
    if chunk.key == "introduction":
        return "introduction"
    return None


def first_index(chunks: list[HeadingChunk], bucket: str) -> int | None:
    for index, chunk in enumerate(chunks):
        if explicit_bucket(chunk) == bucket:
            return index
    return None


def infer_bucket(
    chunk: HeadingChunk,
    *,
    chunk_index: int,
    chunks: list[HeadingChunk],
    current_bucket: str,
    first_experiment_index: int | None,
    first_result_index: int | None,
    first_conclusion_index: int | None,
) -> str:
    bucket = explicit_bucket(chunk)
    if bucket is not None:
        return bucket

    if first_conclusion_index is not None and chunk_index >= first_conclusion_index:
        return "conclusion"
    if first_result_index is not None and chunk_index >= first_result_index:
        return "result"
    if first_experiment_index is not None and chunk_index >= first_experiment_index:
        return "experiment"

    if current_bucket == "introduction":
        return "method" if chunk_index > 0 else "introduction"
    if current_bucket in {"method", "experiment", "result"}:
        return current_bucket
    return "method"


def classify_chunks(chunks: list[HeadingChunk]) -> list[tuple[str, HeadingChunk]]:
    first_experiment_index = first_index(chunks, "experiment")
    first_result_index = first_index(chunks, "result")
    first_conclusion_index = first_index(chunks, "conclusion")

    classified: list[tuple[str, HeadingChunk]] = []
    current_bucket = "introduction"
    for chunk_index, chunk in enumerate(chunks):
        bucket = infer_bucket(
            chunk,
            chunk_index=chunk_index,
            chunks=chunks,
            current_bucket=current_bucket,
            first_experiment_index=first_experiment_index,
            first_result_index=first_result_index,
            first_conclusion_index=first_conclusion_index,
        )
        classified.append((bucket, chunk))
        current_bucket = bucket
    return classified


def merge_classified_chunks(classified_chunks: list[tuple[str, HeadingChunk]]) -> list[ParsedPaperSection]:
    merged: list[ParsedPaperSection] = []
    for key in TARGET_SECTION_ORDER:
        bucket_chunks = [chunk for bucket, chunk in classified_chunks if bucket == key]
        if not bucket_chunks:
            continue
        text = "\n\n".join(chunk.text for chunk in bucket_chunks).strip()
        if len(text) < 20:
            continue
        merged.append(
            ParsedPaperSection(
                key=key,
                title=bucket_chunks[0].title,
                text=text,
                char_count=len(text),
            )
        )
    return merged


def extract_key_sections(markdown_text: str) -> list[ParsedPaperSection]:
    chunks = build_main_body_chunks(markdown_text)
    classified_chunks = classify_chunks(chunks)
    return merge_classified_chunks(classified_chunks)


def write_key_sections(section_dir: Path, sections: list[ParsedPaperSection]) -> None:
    section_dir.mkdir(parents=True, exist_ok=True)
    keep_names = set()
    for section in sections:
        file_name = SECTION_FILE_NAMES[section.key]
        keep_names.add(file_name)
        (section_dir / file_name).write_text(section.text.rstrip() + "\n", encoding="utf-8")
    for child in section_dir.iterdir():
        if child.is_file() and child.name not in keep_names:
            child.unlink()


def split_key_sections(markdown_path: Path, section_dir: Path) -> SectionArtifacts:
    markdown_text = markdown_path.read_text(encoding="utf-8")
    sections = extract_key_sections(markdown_text)
    write_key_sections(section_dir, sections)
    full_text = "\n\n".join(section.text for section in sections).strip()
    return SectionArtifacts(
        section_dir=section_dir,
        sections=sections,
        full_text=full_text,
    )
