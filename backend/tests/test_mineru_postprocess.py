from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from app.services.pdf_parser.postprocess import process_mineru_markdown_artifacts


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
