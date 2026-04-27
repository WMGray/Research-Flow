"""Shared paper download service."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path
from typing import Any, Protocol

from core.config import backend_root, get_settings


STATUS_READY = "ready_download"


class PaperResolveInput(Protocol):
    source_url: str | None
    doi: str | None
    title: str | None
    year: str
    venue: str


class PaperDownloadInput(PaperResolveInput, Protocol):
    output_dir: str | None
    overwrite: bool | None


class PaperDownloadService:
    @staticmethod
    def _configured_output_dir() -> Path:
        path = Path(get_settings().paper_download.output_dir).expanduser()
        if not path.is_absolute():
            path = (backend_root() / path).resolve()
        return path.resolve()

    @staticmethod
    def _resolve_output_dir(output_dir: str | None) -> Path:
        base_dir = PaperDownloadService._configured_output_dir()
        if not output_dir:
            return base_dir

        path = (base_dir / output_dir).resolve()
        if not path.is_relative_to(base_dir):
            raise ValueError(
                "paper download output_dir must stay under configured output_dir."
            )
        return path

    @staticmethod
    def build_gpaper_args(request: PaperResolveInput) -> Namespace:
        settings = get_settings().paper_download
        request_output_dir = getattr(request, "output_dir", None)
        request_overwrite = getattr(request, "overwrite", None)
        overwrite = (
            settings.overwrite
            if request_overwrite is None
            else request_overwrite
        )
        paper_title = request.title or ""
        return Namespace(
            url=request.source_url or "",
            doi=request.doi or "",
            name=paper_title,
            title=paper_title,
            year=request.year or "",
            venue=request.venue or "",
            env_file="",
            output_dir=str(
                PaperDownloadService._resolve_output_dir(request_output_dir)
            ),
            email=settings.email or "",
            s2_api_key=settings.s2_api_key or "",
            openalex_api_key=settings.openalex_api_key or "",
            timeout=settings.timeout,
            retries=settings.retries,
            retry_wait=settings.retry_wait,
            rate_limit_wait=settings.rate_limit_wait,
            min_pdf_size=settings.min_pdf_size,
            overwrite=overwrite,
        )

    @staticmethod
    def load_getpaper_backend() -> tuple[type, type, type, type]:
        try:
            from gpaper.common import Record, Resolution
            from gpaper.downloader import Downloader
            from gpaper.resolver import Resolver
        except ImportError as exc:
            raise RuntimeError(
                "gPaper is required for paper_download. Run `uv sync` in backend "
                "after installing the declared getPaper dependency."
            ) from exc
        return Record, Resolution, Downloader, Resolver

    @staticmethod
    def close_backend_session(downloader: Any) -> None:
        session = getattr(downloader, "session", None)
        if session is not None and hasattr(session, "close"):
            session.close()

    @staticmethod
    def build_gpaper_record(record_type: type, args: Namespace) -> Any:
        return record_type(
            index=1,
            raw_input=args.url or args.doi or args.title,
            title=args.title,
            year=args.year,
            venue=args.venue,
        )

    def resolve(self, request: PaperResolveInput) -> Any:
        record_type, _, downloader_type, resolver_type = self.load_getpaper_backend()
        args = self.build_gpaper_args(request)
        record = self.build_gpaper_record(record_type, args)
        downloader = downloader_type(args)
        resolver = resolver_type(args, downloader=downloader)
        try:
            return resolver.resolve(record, Path(args.output_dir))
        finally:
            self.close_backend_session(downloader)

    def download(self, request: PaperDownloadInput) -> tuple[Any, dict[str, Any]]:
        record_type, resolution_type, downloader_type, resolver_type = (
            self.load_getpaper_backend()
        )
        args = self.build_gpaper_args(request)
        record = self.build_gpaper_record(record_type, args)
        downloader = downloader_type(args)
        resolver = resolver_type(args, downloader=downloader)
        output_dir = Path(args.output_dir)
        try:
            row = resolver.resolve(record, output_dir)
            if row.status != STATUS_READY:
                return row, {
                    "status": "not_ready",
                    "detail": row.detail
                    or "paper could not be resolved to a downloadable PDF",
                    "error_code": row.error_code,
                    "file_path": "",
                }
            resolution = resolution_type(
                status="resolved",
                method=row.resolve_method,
                pdf_url=row.pdf_url,
                landing_url=row.landing_url,
                doi=row.doi,
                title=row.title,
                year=row.year,
                venue=row.venue,
                source=row.source,
                detail=row.detail,
                error_code=row.error_code,
                probe_trace=list(row.probe_trace),
            )
            result = downloader.download_pdf(record, resolution, output_dir)
            return row, result
        finally:
            self.close_backend_session(downloader)
