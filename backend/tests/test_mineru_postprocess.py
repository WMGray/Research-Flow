from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from app.services.pdf_parser.postprocess import normalize_heading, process_mineru_markdown_artifacts
from app.services.pdf_parser.sections import split_key_sections


def test_process_mineru_markdown_artifacts_merges_extracted_images(tmp_path: Path) -> None:
    raw_markdown_path = tmp_path / "full.md"
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    content_list_path = tmp_path / "content_list_v2.json"
    output_markdown_path = tmp_path / "LLM.md"
    output_figure_dir = tmp_path / "figures"

    left_image_path = image_dir / "left.jpg"
    right_image_path = image_dir / "right.jpg"
    Image.new("RGB", (120, 100), (255, 0, 0)).save(left_image_path)
    Image.new("RGB", (120, 100), (0, 0, 255)).save(right_image_path)

    raw_markdown_path.write_text(
        "\n".join(
            [
                "# Demo Paper",
                "",
                "## Abstract",
                "",
                "Demo abstract.",
                "",
                "![](images/left.jpg)",
                "",
                "![](images/right.jpg)",
                "",
                "Figure 1. Demo figure.",
            ]
        ),
        encoding="utf-8",
    )

    content_list = [
        [
            {
                "type": "image",
                "bbox": [10, 20, 70, 70],
                "content": {
                    "image_source": {"path": "images/left.jpg"},
                    "image_caption": [],
                    "image_footnote": [],
                },
            },
            {
                "type": "image",
                "bbox": [80, 20, 140, 70],
                "content": {
                    "image_source": {"path": "images/right.jpg"},
                    "image_caption": [{"type": "text", "content": "legend text Figure 1. Demo figure."}],
                    "image_footnote": [],
                },
            },
        ]
    ]
    content_list_path.write_text(json.dumps(content_list), encoding="utf-8")

    result = process_mineru_markdown_artifacts(
        raw_markdown_path=raw_markdown_path,
        source_image_dir=image_dir,
        content_list_path=content_list_path,
        output_markdown_path=output_markdown_path,
        output_figure_dir=output_figure_dir,
    )

    assert result.figure_count == 1
    assert result.raw_image_ref_count == 2
    assert result.grouped_image_ref_count == 1
    assert output_markdown_path.exists()

    markdown_text = output_markdown_path.read_text(encoding="utf-8")
    assert "images/" not in markdown_text
    assert "![](figures/figure_1.png)" in markdown_text
    assert "- Figure rendering: `MinerU extracted-image montage v2`" in markdown_text

    merged_image_path = output_figure_dir / "figure_1.png"
    assert merged_image_path.exists()

    with Image.open(merged_image_path) as merged_image:
        assert merged_image.width > merged_image.height
        left_pixel = merged_image.getpixel((20, merged_image.height // 2))
        right_pixel = merged_image.getpixel((merged_image.width - 20, merged_image.height // 2))
        assert left_pixel[0] > left_pixel[2]
        assert right_pixel[2] > right_pixel[0]


def test_postprocess_normalizes_heading_depth() -> None:
    assert normalize_heading("# Demo Paper", is_title=True) == "# Demo Paper"
    assert normalize_heading("# 2 Method", is_title=False) == "## 2 Method"
    assert normalize_heading("# 2.2 Optimization", is_title=False) == "### 2.2 Optimization"
    assert normalize_heading("# 2.2.2 Details", is_title=False) == "#### 2.2.2 Details"


def test_split_key_sections_excludes_references_and_preserves_boundaries(tmp_path: Path) -> None:
    markdown_path = tmp_path / "LLM.md"
    section_dir = tmp_path / "sections"
    markdown_path.write_text(
        "\n".join(
            [
                "# Demo Paper",
                "",
                "## Abstract",
                "Abstract text.",
                "",
                "## 1. Introduction",
                "Intro text.",
                "",
                "## 2. Method",
                "Method text.",
                "",
                "## 3. Evaluation",
                "Eval overview.",
                "",
                "### 3.1. Datasets and Settings",
                "Experiment setup text.",
                "",
                "### 3.2. Main Results",
                "Result text.",
                "",
                "## 4. Conclusion",
                "Conclusion text.",
                "",
                "## References",
                "[1] Ref text.",
            ]
        ),
        encoding="utf-8",
    )

    artifacts = split_key_sections(markdown_path, section_dir)
    keys = [section.key for section in artifacts.sections]

    assert keys == ["introduction", "method", "experiment", "result", "conclusion"]
    assert "References" not in artifacts.full_text
    assert "Main Results" not in (section_dir / "experiment.md").read_text(encoding="utf-8")
    assert "Experiment setup text." in (section_dir / "experiment.md").read_text(encoding="utf-8")
    assert "Result text." in (section_dir / "result.md").read_text(encoding="utf-8")


def test_split_key_sections_supports_implicit_method_section(tmp_path: Path) -> None:
    markdown_path = tmp_path / "LLM.md"
    section_dir = tmp_path / "sections"
    markdown_path.write_text(
        "\n".join(
            [
                "# Demo Paper",
                "",
                "## Abstract",
                "Abstract text.",
                "",
                "## 1 INTRODUCTION",
                "Intro text.",
                "",
                "## 2 LEARNING TO USE TOOLS WITH VISUAL INSTRUCTION TUNING",
                "Method overview.",
                "",
                "### 2.1 CORE DESIGN",
                "Method details.",
                "",
                "## 3 RELATED WORKS",
                "Related work text.",
                "",
                "## 4 EXPERIMENTS",
                "Experiment intro.",
                "",
                "### 4.1 THE EFFECTIVENESS OF LEARNING TO USE SKILLS",
                "Experiment setup text.",
                "",
                "### 4.2 COMPARISONS WITH SOTA LMM SYSTEMS",
                "Result text.",
                "",
                "## 5 CONCLUSION",
                "Conclusion text.",
            ]
        ),
        encoding="utf-8",
    )

    artifacts = split_key_sections(markdown_path, section_dir)

    assert [section.key for section in artifacts.sections] == ["introduction", "method", "experiment", "result", "conclusion"]
    method_text = (section_dir / "method.md").read_text(encoding="utf-8")
    assert "LEARNING TO USE TOOLS WITH VISUAL INSTRUCTION TUNING" in method_text
    assert "Method details." in method_text
    assert "RELATED WORKS" not in method_text
    result_text = (section_dir / "result.md").read_text(encoding="utf-8")
    assert "COMPARISONS WITH SOTA LMM SYSTEMS" in result_text


def test_split_key_sections_prefers_top_level_method_chapter_over_deeper_model_subsection(tmp_path: Path) -> None:
    markdown_path = tmp_path / "LLM.md"
    section_dir = tmp_path / "sections"
    markdown_path.write_text(
        "\n".join(
            [
                "# Demo Paper",
                "",
                "## 1 INTRODUCTION",
                "Intro text.",
                "",
                "## 2 LEARNING TO USE TOOLS WITH VISUAL INSTRUCTION TUNING",
                "Method chapter overview.",
                "",
                "### 2.1 CORE DESIGN",
                "Core design text.",
                "",
                "### 2.3 MODEL TRAINING AND SERVING",
                "Model serving text.",
                "",
                "## 3 RELATED WORKS",
                "Related work text.",
                "",
                "## 4 EXPERIMENTS",
                "Experiments text.",
                "",
                "### 4.2 COMPARISONS WITH SOTA LMM SYSTEMS",
                "Result text.",
                "",
                "## 5 CONCLUSION",
                "Conclusion text.",
            ]
        ),
        encoding="utf-8",
    )

    artifacts = split_key_sections(markdown_path, section_dir)
    method_text = (section_dir / "method.md").read_text(encoding="utf-8")

    assert "LEARNING TO USE TOOLS WITH VISUAL INSTRUCTION TUNING" in method_text
    assert "Core design text." in method_text
    assert "Model serving text." in method_text
    assert "RELATED WORKS" not in method_text
