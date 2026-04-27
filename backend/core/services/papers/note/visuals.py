from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
from typing import Any


IMAGE_LINK_RE = re.compile(r"!\[(?P<alt>[^\]]*)]\((?P<target>[^)\s]+)(?:\s+\"[^\"]*\")?\)")
CAPTION_RE = re.compile(
    r"^\s*(?:>\s*)?(?:\*\*图注\*\*[:：]\s*)?"
    r"(?P<label>(?:fig(?:ure)?|table)\s*[A-Za-z]?\d+(?:\.\d+)*)(?:\s*[:.：])?\s*(?P<body>.*)$",
    re.IGNORECASE,
)
MAX_FIGURE_EVIDENCE = 8


@dataclass(frozen=True, slots=True)
class FigureEvidence:
    figure_id: str
    section_key: str
    section_title: str
    image_path: str
    alt_text: str
    caption: str
    line_no: int
    role_hint: str = "support"
    review_notes: tuple[str, ...] = ()


def render_figure_context(figures: list[FigureEvidence]) -> str:
    if not figures:
        return "No usable figure or table image evidence was detected in the parsed paper."
    lines = ["# Figure/Table Evidence"]
    for figure in figures:
        lines.extend(
            [
                f"- id: {figure.figure_id}",
                f"  section: {figure.section_title} ({figure.section_key})",
                f"  role_hint: {figure.role_hint}",
                f"  image_markdown: ![{figure.alt_text}]({figure.image_path})",
                f"  caption: {figure.caption}",
                f"  requires_review: {bool(figure.review_notes)}",
                f"  review_notes: {'; '.join(figure.review_notes) if figure.review_notes else ''}",
                f"  line_no: {figure.line_no}",
            ]
        )
    return "\n".join(lines)


def collect_figure_evidence(
    sections: list[dict[str, Any]],
    *,
    note_path: Path | None = None,
    image_base_dirs: list[Path] | None = None,
    max_figures: int = MAX_FIGURE_EVIDENCE,
) -> list[FigureEvidence]:
    figures: list[FigureEvidence] = []
    seen_paths: set[str] = set()
    base_dirs = image_base_dirs or []
    for section in sections:
        section_key = str(section.get("section_key") or "")
        section_title = str(section.get("title") or section_key or "Section")
        lines = str(section.get("content") or "").splitlines()
        for index, line in enumerate(lines):
            for match in IMAGE_LINK_RE.finditer(line):
                raw_target = match.group("target").strip().strip("<>")
                image_path, image_resolved = _note_image_path(
                    raw_target,
                    note_path=note_path,
                    image_base_dirs=base_dirs,
                )
                if image_path in seen_paths:
                    continue
                seen_paths.add(image_path)
                caption = _nearby_caption(lines, index)
                figure_id = _figure_id(caption, len(figures) + 1)
                alt_text = (match.group("alt").strip() or figure_id).replace("\n", " ")
                figures.append(
                    FigureEvidence(
                        figure_id=figure_id,
                        section_key=section_key,
                        section_title=section_title,
                        image_path=image_path,
                        alt_text=alt_text,
                        caption=caption or "No caption detected in the parsed section.",
                        line_no=index + 1,
                        role_hint=_figure_role_hint(
                            section_key=section_key,
                            section_title=section_title,
                            caption=caption,
                            alt_text=alt_text,
                        ),
                        review_notes=_figure_review_notes(
                            caption=caption,
                            image_resolved=image_resolved,
                            raw_target=raw_target,
                        ),
                    )
                )
    return sorted(figures, key=_figure_sort_key)[:max_figures]


def render_visual_evidence_block(figures: list[FigureEvidence], llm_text: str) -> str:
    cleaned_llm_text = llm_text.strip()
    if not figures:
        return cleaned_llm_text or "Not stated in the parsed paper."

    rendered_figures: list[str] = []
    for figure in figures:
        lines = [
            f"### {figure.figure_id}",
            f"![{figure.alt_text}]({figure.image_path})",
            "",
            f"> **图注**：{figure.caption}",
            f"> **来源章节**：{figure.section_title}",
            f"> **阅读角色**：{_role_label(figure.role_hint)}",
        ]
        if figure.review_notes:
            lines.extend(["", ">[!Caution]"])
            lines.extend(f"> {note}" for note in figure.review_notes)
        rendered_figures.append("\n".join(lines))
    if not cleaned_llm_text or cleaned_llm_text == "Not stated in the parsed paper.":
        return "\n\n".join(rendered_figures)
    return "\n\n".join(rendered_figures) + "\n\n### 图表解读\n" + cleaned_llm_text


def attach_figures_to_note_blocks(
    blocks: dict[str, str],
    figures: list[FigureEvidence],
) -> dict[str, str]:
    """Attach deterministic figure Markdown inside the prompt-defined note sections."""

    if not figures:
        return blocks
    method_figures = _figures_for_method(figures)
    result_figures = [
        figure
        for figure in figures
        if figure.figure_id not in {item.figure_id for item in method_figures}
    ]
    updated = dict(blocks)
    updated["method"] = _append_block_figures(
        updated.get("method", ""),
        method_figures,
        "关键方法图表",
    )
    updated["experimental_results"] = _append_block_figures(
        updated.get("experimental_results", ""),
        result_figures,
        "实验与附录图表证据",
    )
    return updated


def _nearby_caption(lines: list[str], image_index: int) -> str:
    for offset in (1, 2, -1, -2, 3, -3):
        candidate_index = image_index + offset
        if candidate_index < 0 or candidate_index >= len(lines):
            continue
        candidate = lines[candidate_index].strip()
        if candidate and CAPTION_RE.match(candidate):
            return _clean_caption_line(candidate)
    return ""


def _figures_for_method(figures: list[FigureEvidence]) -> list[FigureEvidence]:
    method_figures = [
        figure
        for figure in figures
        if figure.role_hint in {"method", "problem"} or figure.section_key == "method"
    ]
    if method_figures:
        return method_figures
    return figures[:1]


def _append_block_figures(
    block_text: str,
    figures: list[FigureEvidence],
    heading: str,
) -> str:
    cleaned = block_text.strip()
    if not figures:
        return cleaned
    rendered = _render_figures(figures, heading)
    return f"{cleaned}\n\n{rendered}".strip() if cleaned else rendered


def _render_figures(figures: list[FigureEvidence], heading: str) -> str:
    rendered_figures: list[str] = [f"### {heading}"]
    for figure in figures:
        rendered_figures.extend(
            [
                "",
                f"#### {figure.figure_id}",
                f"![{figure.alt_text}]({figure.image_path})",
                "",
                f"> **图注**：{figure.caption}",
                f"> **来源章节**：{figure.section_title}",
                f"> **阅读角色**：{_role_label(figure.role_hint)}",
            ]
        )
        if figure.review_notes:
            rendered_figures.extend(["", ">[!Caution]"])
            rendered_figures.extend(f"> {note}" for note in figure.review_notes)
    return "\n".join(rendered_figures)


def _clean_caption_line(line: str) -> str:
    stripped = line.strip()
    stripped = re.sub(r"^>\s*", "", stripped)
    return re.sub(r"^\*\*图注\*\*[:：]\s*", "", stripped)


def _figure_id(caption: str, fallback_index: int) -> str:
    if caption and (match := CAPTION_RE.match(caption)):
        return re.sub(r"\s+", " ", match.group("label").strip()).title()
    return f"Figure Evidence {fallback_index}"


def _note_image_path(
    raw_target: str,
    *,
    note_path: Path | None,
    image_base_dirs: list[Path],
) -> tuple[str, bool]:
    if re.match(r"^[a-z][a-z0-9+.-]*://", raw_target, re.IGNORECASE):
        return raw_target, True
    resolved = _resolve_image_target(raw_target, image_base_dirs)
    if resolved is None or note_path is None:
        return raw_target.replace("\\", "/"), resolved is not None
    try:
        return Path(os.path.relpath(resolved, start=note_path.parent)).as_posix(), True
    except ValueError:
        return str(resolved).replace("\\", "/"), True


def _figure_role_hint(
    *,
    section_key: str,
    section_title: str,
    caption: str,
    alt_text: str,
) -> str:
    text = f"{section_key} {section_title} {caption} {alt_text}".lower()
    if section_key == "experiment" or any(
        token in text
        for token in (
            "accuracy",
            "result",
            "experiment",
            "evaluation",
            "benchmark",
            "ablation",
            "performance",
            "comparison",
            "validation",
        )
    ):
        return "result"
    if section_key == "method" or any(
        token in text
        for token in (
            "overview",
            "pipeline",
            "framework",
            "architecture",
            "approach",
            "model",
            "module",
            "workflow",
        )
    ):
        return "method"
    if any(token in text for token in ("problem", "task", "motivation", "setting")):
        return "problem"
    return "support"


def _figure_review_notes(
    *,
    caption: str,
    image_resolved: bool,
    raw_target: str,
) -> tuple[str, ...]:
    notes: list[str] = []
    if not caption.strip():
        notes.append("解析结果没有在图片附近找到可靠图注，需要人工核对原 PDF。")
    if not image_resolved:
        notes.append(f"图片路径 `{raw_target}` 未能解析到本地文件，需要检查解析产物。")
    return tuple(notes)


def _figure_sort_key(figure: FigureEvidence) -> tuple[int, str, int]:
    role_priority = {"method": 0, "problem": 1, "result": 2, "support": 3}
    return (
        role_priority.get(figure.role_hint, 9),
        figure.section_key,
        figure.line_no,
    )


def _role_label(role_hint: str) -> str:
    return {
        "method": "方法主线/架构图，优先用于理解本文方法",
        "problem": "问题设定/动机图，用于理解任务背景",
        "result": "实验结果/对比图，用于支撑结果分析",
        "support": "补充证据图，用于辅助理解论文内容",
    }.get(role_hint, "补充证据图，用于辅助理解论文内容")


def _resolve_image_target(raw_target: str, image_base_dirs: list[Path]) -> Path | None:
    raw_path = Path(raw_target)
    if raw_path.is_absolute() and raw_path.exists():
        return raw_path
    for base_dir in image_base_dirs:
        candidate = (base_dir / raw_target).resolve()
        if candidate.exists():
            return candidate
    target_name = raw_path.name
    if not target_name:
        return None
    for base_dir in image_base_dirs:
        if not base_dir.exists():
            continue
        direct = base_dir / target_name
        if direct.exists():
            return direct.resolve()
        for child in base_dir.glob(f"**/{target_name}"):
            if child.exists():
                return child.resolve()
    return None


__all__ = [
    "FigureEvidence",
    "attach_figures_to_note_blocks",
    "collect_figure_evidence",
    "render_figure_context",
    "render_visual_evidence_block",
]
