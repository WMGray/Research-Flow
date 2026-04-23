from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.paper_download import get_paper_download_service
from app.core.config import reset_settings
from app.main import app
from app.schemas.paper_download import PaperDownloadRequest
from app.services.paper_download.service import PaperDownloadService


@dataclass(frozen=True)
class FakeResolveRow:
    index: int
    raw_input: str
    title: str
    year: str
    venue: str
    doi: str
    resolve_method: str
    source: str
    status: str
    pdf_url: str
    landing_url: str
    final_url: str
    http_status: str
    content_type: str
    detail: str
    error_code: str
    metadata_source: str
    metadata_confidence: str
    suggested_filename: str
    target_path: str
    probe_trace: list[str]


class FakePaperDownloadService:
    def resolve(self, request):
        del request
        return FakeResolveRow(
            index=1,
            raw_input="test",
            title="Test Paper",
            year="2024",
            venue="CVPR",
            doi="10.1234/test",
            resolve_method="direct",
            source="semantic_scholar",
            status="ready_download",
            pdf_url="https://example.com/paper.pdf",
            landing_url="https://example.com/landing",
            final_url="https://example.com/final.pdf",
            http_status="200",
            content_type="application/pdf",
            detail="",
            error_code="",
            metadata_source="semantic_scholar_doi",
            metadata_confidence="high",
            suggested_filename="Test Paper__2024.pdf",
            target_path="C:/tmp/Test Paper__2024.pdf",
            probe_trace=["step-1"],
        )

    def download(self, request):
        del request
        return self.resolve(None), {
            "status": "downloaded",
            "file_path": "C:/tmp/Test Paper__2024.pdf",
            "detail": "",
            "error_code": "",
        }


def test_paper_download_resolve_endpoint() -> None:
    app.dependency_overrides[get_paper_download_service] = lambda: (
        FakePaperDownloadService()
    )
    try:
        with TestClient(app) as client:
            response = client.post(
                "/paper-download/resolve", json={"name": "Test Paper"}
            )
        assert response.status_code == 200
        payload = response.json()
        assert payload["title"] == "Test Paper"
        assert payload["status"] == "ready_download"
        assert payload["probe_trace"] == ["step-1"]
    finally:
        app.dependency_overrides.clear()


def test_paper_download_download_endpoint() -> None:
    app.dependency_overrides[get_paper_download_service] = lambda: (
        FakePaperDownloadService()
    )
    try:
        with TestClient(app) as client:
            response = client.post(
                "/paper-download/download", json={"name": "Test Paper"}
            )
        assert response.status_code == 200
        payload = response.json()
        assert payload["download_status"] == "downloaded"
        assert payload["resolution"]["doi"] == "10.1234/test"
    finally:
        app.dependency_overrides.clear()


def test_paper_download_rejects_unsafe_output_dir() -> None:
    with TestClient(app) as client:
        absolute_response = client.post(
            "/paper-download/download",
            json={"name": "Test Paper", "output_dir": "C:/tmp/papers"},
        )
        traversal_response = client.post(
            "/paper-download/download",
            json={"name": "Test Paper", "output_dir": "../outside"},
        )
        drive_relative_response = client.post(
            "/paper-download/download",
            json={"name": "Test Paper", "output_dir": "C:tmp"},
        )

    assert absolute_response.status_code == 422
    assert traversal_response.status_code == 422
    assert drive_relative_response.status_code == 422


def test_paper_download_scopes_runtime_output_dir(monkeypatch, tmp_path: Path) -> None:
    base_output_dir = tmp_path / "papers"
    monkeypatch.setenv("RESEARCH_FLOW_ENV_FILE", "none")
    monkeypatch.setenv("PAPER_DOWNLOAD_OUTPUT_DIR", str(base_output_dir))
    reset_settings()

    try:
        request = PaperDownloadRequest(name="Test Paper", output_dir="daily")
        args = PaperDownloadService.build_gpaper_args(request)

        assert Path(args.output_dir) == base_output_dir / "daily"
    finally:
        reset_settings()
