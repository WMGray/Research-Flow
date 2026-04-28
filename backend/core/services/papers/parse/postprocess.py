from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Any

from .sections import APPENDIX_HEADING_RE, classify_heading


CAPTION_RE = re.compile(r"\b(Figure|Fig\.|Table)\s+([A-Za-z0-9_.-]+)", re.IGNORECASE)
IMAGE_LINE_RE = re.compile(r"!\[[^\]]*]\(([^)]+)\)")
CAPTION_LINE_RE = re.compile(
    r"^\s*(?:>\s*)?(?:\*\*图注\*\*[:：]\s*)?"
    r"(?P<label>(?:fig(?:ure)?|table)\s+[A-Za-z]?\d+(?:\.\d+)*)"
    r"(?P<body>\s*[:.：]?.*)$",
    re.IGNORECASE,
)
NUMBERED_HEADING_RE = re.compile(r"^(?P<num>\d+(?:\.\d+)*)(?:[\.\)]|\s)+(?:\s*)(?P<title>.+)$")
MARKDOWN_IMAGE_DIR = "images"


def load_pillow_image() -> Any:
    try:
        from PIL import Image
    except ModuleNotFoundError as exc:
        raise RuntimeError("Pillow is required for MinerU figure postprocessing.") from exc
    return Image


@dataclass(frozen=True, slots=True)
class BBox:
    x0: float
    y0: float
    x1: float
    y1: float

    @classmethod
    def from_list(cls, values: list[float] | tuple[float, float, float, float]) -> "BBox":
        return cls(float(values[0]), float(values[1]), float(values[2]), float(values[3]))

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        return self.y1 - self.y0

    def union(self, other: "BBox") -> "BBox":
        return BBox(
            x0=min(self.x0, other.x0),
            y0=min(self.y0, other.y0),
            x1=max(self.x1, other.x1),
            y1=max(self.y1, other.y1),
        )


@dataclass(frozen=True, slots=True)
class PageItem:
    page_index: int
    raw_index: int
    item_type: str
    bbox: BBox
    text: str
    image_name: str | None
    caption: str


@dataclass(frozen=True, slots=True)
class FigureGroup:
    page_index: int
    label: str
    caption: str
    output_name: str
    crop_bbox: BBox
    image_names: tuple[str, ...]
    image_items: tuple[PageItem, ...]


@dataclass(frozen=True, slots=True)
class ProcessedMarkdownArtifacts:
    markdown_path: Path
    figure_dir: Path
    figure_count: int
    raw_image_ref_count: int
    grouped_image_ref_count: int


def collect_text(node: object) -> list[str]:
    if isinstance(node, str):
        return [node]
    if isinstance(node, list):
        fragments: list[str] = []
        for item in node:
            fragments.extend(collect_text(item))
        return fragments
    if isinstance(node, dict):
        fragments: list[str] = []
        for key, value in node.items():
            if key in {"bbox", "path", "level"}:
                continue
            fragments.extend(collect_text(value))
        return fragments
    return []


def normalize_text(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = re.sub(r"^(text|equation_inline)\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_page_items(content_list_path: Path) -> list[list[PageItem]]:
    raw_pages = json.loads(content_list_path.read_text(encoding="utf-8"))
    pages: list[list[PageItem]] = []
    for page_index, page_items in enumerate(raw_pages):
        parsed_items: list[PageItem] = []
        for raw_index, item in enumerate(page_items):
            item_type = str(item.get("type") or "")
            bbox = BBox.from_list(item.get("bbox") or [0, 0, 0, 0])
            item_content = item.get("content") or {}
            text = normalize_text(" ".join(collect_text(item_content)))
            image_name: str | None = None
            caption = ""
            if item_type == "image":
                image_source = item_content.get("image_source") or {}
                image_path = image_source.get("path") or ""
                image_name = Path(str(image_path)).name if image_path else None
                caption = normalize_text(" ".join(collect_text(item_content.get("image_caption") or [])))
            parsed_items.append(
                PageItem(
                    page_index=page_index,
                    raw_index=raw_index,
                    item_type=item_type,
                    bbox=bbox,
                    text=text,
                    image_name=image_name,
                    caption=caption,
                )
            )
        pages.append(parsed_items)
    return pages


def is_captioned_figure(caption: str) -> bool:
    return bool(CAPTION_RE.search(caption))


def parse_label(caption: str, page_index: int, seen_labels: dict[str, int]) -> str:
    match = CAPTION_RE.search(caption)
    if match is None:
        base_label = f"page_{page_index + 1:02d}"
    else:
        kind = match.group(1).lower().replace(".", "")
        number = re.sub(r"[^A-Za-z0-9_-]+", "_", match.group(2).strip(" ._-")).strip("_")
        base_label = f"{kind}_{number}"
    suffix_index = seen_labels.get(base_label, 0)
    seen_labels[base_label] = suffix_index + 1
    return base_label if suffix_index == 0 else f"{base_label}_{suffix_index + 1}"


def should_include_aux_item(candidate: PageItem, base_bbox: BBox) -> bool:
    if candidate.item_type not in {"paragraph", "page_footnote"}:
        return False
    if not candidate.text:
        return False
    if candidate.bbox.y0 < base_bbox.y0 - 20:
        return False
    if candidate.bbox.y0 - base_bbox.y1 > 140:
        return False
    text_length = len(candidate.text)
    if text_length <= 120:
        return True
    return candidate.bbox.height <= 30 and text_length <= 220


def build_groups(pages: list[list[PageItem]]) -> list[FigureGroup]:
    groups: list[FigureGroup] = []
    seen_labels: dict[str, int] = {}
    for page_index, items in enumerate(pages):
        cursor = 0
        while cursor < len(items):
            if items[cursor].item_type != "image":
                cursor += 1
                continue

            image_run: list[PageItem] = []
            while cursor < len(items) and items[cursor].item_type == "image":
                image_run.append(items[cursor])
                cursor += 1

            captioned_item = next((item for item in image_run if is_captioned_figure(item.caption)), None)
            if captioned_item is None:
                continue

            crop_bbox = image_run[0].bbox
            for image_item in image_run[1:]:
                crop_bbox = crop_bbox.union(image_item.bbox)

            aux_cursor = cursor
            while aux_cursor < len(items) and should_include_aux_item(items[aux_cursor], crop_bbox):
                crop_bbox = crop_bbox.union(items[aux_cursor].bbox)
                aux_cursor += 1

            label = parse_label(captioned_item.caption, page_index, seen_labels)
            groups.append(
                FigureGroup(
                    page_index=page_index,
                    label=label,
                    caption=captioned_item.caption,
                    output_name=f"{label}.png",
                    crop_bbox=crop_bbox,
                    image_names=tuple(item.image_name for item in image_run if item.image_name),
                    image_items=tuple(item for item in image_run if item.image_name),
                )
            )
    return groups


def open_source_images(source_image_dir: Path, group: FigureGroup) -> list[tuple[PageItem, Any]]:
    image_module = load_pillow_image()
    opened_images: list[tuple[PageItem, Any]] = []
    for item in group.image_items:
        if item.image_name is None:
            continue
        source_path = source_image_dir / item.image_name
        if not source_path.exists():
            continue
        image = image_module.open(source_path).convert("RGB")
        opened_images.append((item, image))
    return opened_images


def image_scale_factors(image: Any, bbox: BBox) -> tuple[float, float]:
    if bbox.width <= 0 or bbox.height <= 0:
        return 1.0, 1.0
    return image.width / bbox.width, image.height / bbox.height


def render_single_image(image: Any, output_path: Path) -> None:
    image.save(output_path)


def render_image_montage(
    opened_images: list[tuple[PageItem, Any]],
    output_path: Path,
    padding: int,
) -> None:
    image_module = load_pillow_image()
    scales: list[float] = []
    for item, image in opened_images:
        scale_x, scale_y = image_scale_factors(image, item.bbox)
        scales.extend([scale_x, scale_y])
    scale = median(scales) if scales else 1.0
    min_x = min(item.bbox.x0 for item, _ in opened_images)
    min_y = min(item.bbox.y0 for item, _ in opened_images)
    max_x = max(item.bbox.x1 for item, _ in opened_images)
    max_y = max(item.bbox.y1 for item, _ in opened_images)
    canvas_width = max(1, round((max_x - min_x) * scale) + padding * 2)
    canvas_height = max(1, round((max_y - min_y) * scale) + padding * 2)
    canvas = image_module.new("RGB", (canvas_width, canvas_height), "white")
    for item, image in opened_images:
        left = padding + round((item.bbox.x0 - min_x) * scale)
        top = padding + round((item.bbox.y0 - min_y) * scale)
        width = max(1, round(item.bbox.width * scale))
        height = max(1, round(item.bbox.height * scale))
        resized = image.resize((width, height), image_module.Resampling.LANCZOS)
        canvas.paste(resized, (left, top))
    canvas.save(output_path)


def normalize_heading(line: str, *, is_title: bool) -> str:
    heading_text = line.lstrip("#").strip()
    if is_title:
        return f"# {heading_text}"

    match = NUMBERED_HEADING_RE.match(heading_text)
    if match is not None:
        numbered_depth = match.group("num").count(".") + 1
        markdown_level = min(numbered_depth + 1, 6)
        return f"{'#' * markdown_level} {heading_text}"

    key = classify_heading(heading_text)
    lowered = heading_text.lower()
    if lowered == "abstract" or key == "abstract":
        return "## Abstract"
    if lowered == "references" or key == "references":
        return "## References"
    if key == "appendix" or APPENDIX_HEADING_RE.match(heading_text):
        return f"## {heading_text}"
    if lowered.startswith("algorithm "):
        return "#### " + heading_text
    if key is not None:
        return "## " + heading_text
    return heading_text


def rewrite_markdown(
    raw_markdown_path: Path,
    output_markdown_path: Path,
    figure_dir: Path,
    source_image_dir: Path,
    groups: list[FigureGroup],
) -> tuple[int, int, set[str]]:
    raw_lines = raw_markdown_path.read_text(encoding="utf-8").splitlines()
    image_to_group = {
        image_name: group for group in groups for image_name in group.image_names
    }
    raw_image_ref_count = 0
    grouped_image_ref_count = 0
    referenced_figure_names: set[str] = set()
    rewritten: list[str] = []
    active_group: str | None = None
    first_heading_seen = False
    skip_caption_labels: set[str] = set()

    for line in raw_lines:
        if line.startswith("#"):
            rewritten.append(normalize_heading(line, is_title=not first_heading_seen))
            first_heading_seen = True
            active_group = None
            continue

        match = IMAGE_LINE_RE.fullmatch(line.strip())
        if match is None:
            caption_label = caption_label_key(line)
            if caption_label and caption_label in skip_caption_labels:
                skip_caption_labels.remove(caption_label)
                if line.strip():
                    active_group = None
                continue
            rewritten.append(line)
            if line.strip():
                active_group = None
            continue

        raw_image_ref_count += 1
        image_name = Path(match.group(1)).name
        group = image_to_group.get(image_name)
        if group is not None:
            if active_group == group.output_name:
                continue
            rewritten.append(f"![]({MARKDOWN_IMAGE_DIR}/{group.output_name})")
            if group.caption:
                rewritten.append(f"> **图注**：{group.caption}")
                skip_caption_labels.add(group.label)
            else:
                rewritten.extend(missing_caption_caution_lines())
            active_group = group.output_name
            grouped_image_ref_count += 1
            referenced_figure_names.add(group.output_name)
            continue

        target_name = image_name
        source_path = source_image_dir / image_name
        target_path = figure_dir / target_name
        if source_path.exists() and not target_path.exists():
            shutil.copy2(source_path, target_path)
        rewritten.append(f"![]({MARKDOWN_IMAGE_DIR}/{target_name})")
        active_group = target_name
        referenced_figure_names.add(target_name)

    rewritten = normalize_figure_annotations(rewritten)
    metadata_lines = [
        "- Parser: `MinerU`",
        "- Figure rendering: `MinerU extracted-image montage v2`",
        "- Organization: chapter-based Markdown, not page-based",
        f"- Embedded figure references: {grouped_image_ref_count}",
    ]
    updated: list[str] = []
    inserted = False
    for line in rewritten:
        if line.startswith("- "):
            continue
        updated.append(line)
        if line.startswith("# ") and not inserted:
            updated.append("")
            updated.extend(metadata_lines)
            inserted = True

    output_markdown_path.write_text("\n".join(updated).rstrip() + "\n", encoding="utf-8")
    return raw_image_ref_count, grouped_image_ref_count, referenced_figure_names


def normalize_figure_annotations(lines: list[str]) -> list[str]:
    normalized: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        normalized.append(line)
        if IMAGE_LINE_RE.fullmatch(line.strip()) is None:
            index += 1
            continue

        next_index = index + 1
        blanks: list[str] = []
        while next_index < len(lines) and not lines[next_index].strip():
            blanks.append(lines[next_index])
            next_index += 1
        if next_index < len(lines) and is_caption_line(lines[next_index]):
            normalized.append(format_caption_line(lines[next_index]))
            index = next_index + 1
            continue
        if next_index < len(lines) and is_caution_line(lines[next_index]):
            normalized.extend(blanks)
            index += len(blanks) + 1
            continue
        normalized.extend(missing_caption_caution_lines())
        normalized.extend(blanks)
        index += len(blanks) + 1
    return normalized


def is_caption_line(line: str) -> bool:
    return CAPTION_LINE_RE.match(line.strip()) is not None


def is_caution_line(line: str) -> bool:
    return line.strip().lower() == ">[!caution]"


def caption_label_key(line: str) -> str | None:
    match = CAPTION_LINE_RE.match(line.strip())
    if match is None:
        return None
    return re.sub(r"[^a-z0-9]+", "_", match.group("label").lower()).strip("_")


def format_caption_line(line: str) -> str:
    stripped = line.strip()
    stripped = re.sub(r"^>\s*", "", stripped)
    stripped = re.sub(r"^\*\*图注\*\*[:：]\s*", "", stripped)
    return f"> **图注**：{stripped}"


def missing_caption_caution_lines() -> list[str]:
    return [
        ">[!Caution]",
        "> 解析结果没有在图片附近找到可靠图注，需要人工核对原 PDF。",
    ]


def cleanup_stale_figures(figure_dir: Path, keep_names: set[str]) -> None:
    if not figure_dir.exists():
        return
    for image_path in figure_dir.iterdir():
        if image_path.is_file() and image_path.name not in keep_names:
            image_path.unlink()


def process_mineru_markdown_artifacts(
    *,
    raw_markdown_path: Path,
    source_image_dir: Path,
    content_list_path: Path | None,
    output_markdown_path: Path,
    output_figure_dir: Path,
    padding: int = 12,
) -> ProcessedMarkdownArtifacts:
    output_figure_dir.mkdir(parents=True, exist_ok=True)
    groups = build_groups(parse_page_items(content_list_path)) if content_list_path and content_list_path.exists() else []

    keep_names: set[str] = set()
    for group in groups:
        opened_images = open_source_images(source_image_dir, group)
        if not opened_images:
            continue
        output_path = output_figure_dir / group.output_name
        if len(opened_images) == 1:
            render_single_image(opened_images[0][1], output_path)
        else:
            render_image_montage(opened_images, output_path, padding=padding)
        keep_names.add(group.output_name)

    raw_image_ref_count, grouped_image_ref_count, referenced_figure_names = rewrite_markdown(
        raw_markdown_path=raw_markdown_path,
        output_markdown_path=output_markdown_path,
        figure_dir=output_figure_dir,
        source_image_dir=source_image_dir,
        groups=groups,
    )
    keep_names.update(referenced_figure_names)
    cleanup_stale_figures(output_figure_dir, keep_names)

    return ProcessedMarkdownArtifacts(
        markdown_path=output_markdown_path,
        figure_dir=output_figure_dir,
        figure_count=len(list(output_figure_dir.iterdir())),
        raw_image_ref_count=raw_image_ref_count,
        grouped_image_ref_count=grouped_image_ref_count,
    )


__all__ = ["ProcessedMarkdownArtifacts", "process_mineru_markdown_artifacts"]
