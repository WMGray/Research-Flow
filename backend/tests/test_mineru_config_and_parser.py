from __future__ import annotations

import asyncio
from pathlib import Path

from app.core.config import get_settings, reset_settings
from app.core.mineru_config import MinerUConfig
from app.services.pdf_parser import PDFParserService


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
