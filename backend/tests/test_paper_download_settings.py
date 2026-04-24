from __future__ import annotations

from core.config import get_settings, reset_settings


def test_paper_download_settings_support_legacy_env_names(monkeypatch) -> None:
    monkeypatch.setenv("RESEARCH_FLOW_ENV_FILE", "none")
    monkeypatch.setenv("EXTRACT_REFS_OUTPUT_DIR", "tmp/papers")
    monkeypatch.setenv("EXTRACT_REFS_TIMEOUT", "45")
    monkeypatch.setenv("EXTRACT_REFS_MIN_PDF_SIZE", "8192")
    reset_settings()

    settings = get_settings()

    assert settings.paper_download.output_dir == "tmp/papers"
    assert settings.paper_download.timeout == 45
    assert settings.paper_download.min_pdf_size == 8192
