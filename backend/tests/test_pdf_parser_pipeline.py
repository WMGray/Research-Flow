from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys

from PIL import Image

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from core.config import get_settings, reset_settings
from core.mineru_config import MinerUConfig
from core.pdf_parser_config import MarkdownRefineConfig, PDFParserConfig
from core.services.papers.parse import PDFParserService
from core.services.papers.parse.postprocess import normalize_heading, process_mineru_markdown_artifacts
from core.services.papers.parse.sections import split_key_sections
from core.services.llm.schemas import LLMMessage, LLMRequest, LLMResponse


class FakeMarkdownRefineLLM:
    def __init__(self, response_content: str) -> None:
        self.response_content = response_content
        self.requests: list[LLMRequest] = []

    async def generate(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        return LLMResponse(
            feature=request.feature or "",
            model_key="fake_markdown_refiner",
            platform="fake",
            provider="fake",
            model="fake-model",
            message=LLMMessage(role="assistant", content=self.response_content),
        )


def test_mineru_settings_support_rflow_env_names(monkeypatch) -> None:
    monkeypatch.setenv("RESEARCH_FLOW_ENV_FILE", "none")
    monkeypatch.setenv("RFLOW_MINERU_BASE_URL", "https://mineru.example.test")
    monkeypatch.setenv("RFLOW_MINERU_API_TOKEN", "test-token")
    monkeypatch.setenv("RFLOW_MINERU_MODEL", "ocr")
    monkeypatch.setenv("RFLOW_MINERU_HTTP_TIMEOUT_SECONDS", "120")
    monkeypatch.setenv("RFLOW_MINERU_POLL_INTERVAL_SECONDS", "2")
    monkeypatch.setenv("RFLOW_MINERU_POLL_TIMEOUT_SECONDS", "60")
    monkeypatch.setenv("RFLOW_PDF_PARSE_MIN_CHARS", "20")

    reset_settings()
    try:
        settings = get_settings()
        assert settings.mineru.base_url == "https://mineru.example.test"
        assert settings.mineru.api_token == "test-token"
        assert settings.mineru.model == "ocr"
        assert settings.mineru.http_timeout_seconds == 120
        assert settings.mineru.poll_interval_seconds == 2
        assert settings.mineru.poll_timeout_seconds == 60
        assert settings.mineru.pdf_parse_min_chars == 20
    finally:
        reset_settings()


def test_pdf_parser_markdown_refine_supports_flat_env_names(monkeypatch) -> None:
    monkeypatch.setenv("RESEARCH_FLOW_ENV_FILE", "none")
    monkeypatch.setenv("PDF_PARSER_MARKDOWN_REFINE_ENABLED", "false")
    monkeypatch.setenv("PDF_PARSER_MARKDOWN_REFINE_FEATURE", "custom_refiner")
    monkeypatch.setenv("PDF_PARSER_MARKDOWN_REFINE_OUTPUT_FILENAME", "custom.md")
    monkeypatch.setenv("PDF_PARSER_MARKDOWN_REFINE_MAX_INPUT_CHARS", "1234")
    monkeypatch.setenv("PDF_PARSER_MARKDOWN_REFINE_FAIL_OPEN", "false")

    reset_settings()
    try:
        config = get_settings().pdf_parser.markdown_refine
        assert config.enabled is False
        assert config.feature == "custom_refiner"
        assert config.output_filename == "custom.md"
        assert config.max_input_chars == 1234
        assert config.fail_open is False
    finally:
        reset_settings()


def test_pdf_parser_reads_existing_mineru_markdown(tmp_path: Path) -> None:
    markdown_path = tmp_path / "full.md"
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    markdown_path.write_text(
        "\n".join(
            [
                "# Abstract",
                "This paper studies robust PDF parsing with enough text for validation.",
                "# Introduction",
                "MinerU returns markdown assets, and the parser normalizes them for later analysis.",
                "# References",
                "[1] Example reference.",
            ]
        ),
        encoding="utf-8",
    )

    parser = PDFParserService(MinerUConfig(pdf_parse_min_chars=20))
    parsed = asyncio.run(parser.parse_existing_markdown(markdown_path, image_dir=image_dir))

    assert parsed.artifact_markdown_path == markdown_path
    assert parsed.artifact_image_dir == image_dir
    assert parsed.artifact_section_dir == markdown_path.parent / "sections"
    assert parsed.char_count >= 20
    assert [section.key for section in parsed.sections] == ["introduction"]
    assert "[Section: Introduction]" in parser.build_llm_context(parsed)


def test_pdf_parser_refines_markdown_before_section_split(tmp_path: Path) -> None:
    markdown_path = tmp_path / "note.md"
    markdown_path.write_text(
        "\n".join(
            [
                "# Demo Paper",
                "",
                "## Raw Intro",
                "Raw intro text from MinerU.",
            ]
        ),
        encoding="utf-8",
    )
    fake_llm = FakeMarkdownRefineLLM(
        "\n".join(
            [
                "```markdown",
                "# Demo Paper",
                "",
                "## 1. Introduction",
                "Refined intro text from the LLM stage.",
                "```",
            ]
        )
    )
    parser_config = PDFParserConfig(
        markdown_refine=MarkdownRefineConfig(
            enabled=True,
            feature="pdf_markdown_refiner",
            prompt="Clean the Markdown before section splitting:\n{{markdown}}",
            output_filename="LLM.refined.md",
        )
    )

    parser = PDFParserService(
        MinerUConfig(pdf_parse_min_chars=20),
        pdf_parser_config=parser_config,
        llm_client=fake_llm,
    )
    parsed = asyncio.run(parser.parse_existing_markdown(markdown_path))

    assert parsed.artifact_markdown_path == tmp_path / "LLM.refined.md"
    assert parsed.sections[0].key == "introduction"
    assert "Refined intro text" in parsed.sections[0].text
    assert fake_llm.requests[0].feature == "pdf_markdown_refiner"
    assert "Raw intro text from MinerU." in fake_llm.requests[0].messages[0].content


def test_process_mineru_markdown_artifacts_merges_extracted_images(tmp_path: Path) -> None:
    raw_markdown_path = tmp_path / "full.md"
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    content_list_path = tmp_path / "content_list_v2.json"
    output_markdown_path = tmp_path / "note.md"
    output_figure_dir = tmp_path / "figures"

    Image.new("RGB", (120, 100), (255, 0, 0)).save(image_dir / "left.jpg")
    Image.new("RGB", (120, 100), (0, 0, 255)).save(image_dir / "right.jpg")

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
    markdown_text = output_markdown_path.read_text(encoding="utf-8")
    assert "images/" not in markdown_text
    assert "![](figures/figure_1.png)" in markdown_text
    assert "> **图注**：legend text Figure 1. Demo figure." in markdown_text
    assert "\nFigure 1. Demo figure." not in markdown_text


def test_postprocess_normalizes_heading_depth() -> None:
    assert normalize_heading("# Demo Paper", is_title=True) == "# Demo Paper"
    assert normalize_heading("# 2 Method", is_title=False) == "## 2 Method"
    assert normalize_heading("# 2.2 Optimization", is_title=False) == "### 2.2 Optimization"
    assert normalize_heading("# 2.2.2 Details", is_title=False) == "#### 2.2.2 Details"


def test_split_key_sections_excludes_references_and_preserves_boundaries(tmp_path: Path) -> None:
    markdown_path = tmp_path / "note.md"
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
    assert [section.key for section in artifacts.sections] == ["introduction", "method", "experiment", "result", "conclusion"]
    assert "References" not in artifacts.full_text
    assert "Main Results" not in (section_dir / "experiment.md").read_text(encoding="utf-8")
    assert "Experiment setup text." in (section_dir / "experiment.md").read_text(encoding="utf-8")
    assert "Result text." in (section_dir / "result.md").read_text(encoding="utf-8")


def test_split_key_sections_supports_implicit_method_section(tmp_path: Path) -> None:
    markdown_path = tmp_path / "note.md"
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
    method_text = (section_dir / "method.md").read_text(encoding="utf-8")
    result_text = (section_dir / "result.md").read_text(encoding="utf-8")

    assert [section.key for section in artifacts.sections] == ["introduction", "method", "experiment", "result", "conclusion"]
    assert "LEARNING TO USE TOOLS WITH VISUAL INSTRUCTION TUNING" in method_text
    assert "Method details." in method_text
    assert "RELATED WORKS" in (section_dir / "introduction.md").read_text(encoding="utf-8")
    assert "COMPARISONS WITH SOTA LMM SYSTEMS" in result_text


def test_split_key_sections_prefers_top_level_method_chapter_over_deeper_model_subsection(tmp_path: Path) -> None:
    markdown_path = tmp_path / "note.md"
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

    split_key_sections(markdown_path, section_dir)
    method_text = (section_dir / "method.md").read_text(encoding="utf-8")

    assert "LEARNING TO USE TOOLS WITH VISUAL INSTRUCTION TUNING" in method_text
    assert "Core design text." in method_text
    assert "Model serving text." in method_text
    assert "RELATED WORKS" not in method_text


if __name__ == "__main__":
    try:
        import pytest
    except ModuleNotFoundError as exc:
        raise SystemExit("pytest is required to run this file directly. Use backend/.venv python or `python -m pytest`.") from exc
    base_temp = BACKEND_ROOT / ".pytest-basetemp" / "test_pdf_parser_pipeline"
    base_temp.mkdir(parents=True, exist_ok=True)
    raise SystemExit(pytest.main([__file__, "-q", "--basetemp", str(base_temp)]))
