from __future__ import annotations

from argparse import Namespace
from pathlib import Path
from typing import Any

from app.core.config import backend_root, get_settings
from app.schemas.paper_download import PaperDownloadRequest, PaperResolveRequest


STATUS_READY = "ready_download"


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
    def build_gpaper_args(
        request: PaperResolveRequest | PaperDownloadRequest,
    ) -> Namespace:
        # gPaper 原生入口就是 url / doi / name 三选一；这里只补齐运行配置。
        settings = get_settings().paper_download
        request_output_dir = (
            request.output_dir
            if isinstance(request, PaperDownloadRequest) and request.output_dir
            else None
        )
        request_overwrite = (
            request.overwrite
            if isinstance(request, PaperDownloadRequest)
            and request.overwrite is not None
            else settings.overwrite
        )
        return Namespace(
            url=request.url or "",
            doi=request.doi or "",
            name=request.name or "",
            title=request.title or "",
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
            overwrite=request_overwrite,
        )

    @staticmethod
    def load_getpaper_backend() -> tuple[type, type, type, type]:
        # 延迟导入，避免应用启动时因可选依赖缺失而直接崩掉。
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
        # gPaper 内部复用 requests.Session；每次服务调用结束后主动关闭连接。
        session = getattr(downloader, "session", None)
        if session is not None and hasattr(session, "close"):
            session.close()

    @staticmethod
    def build_gpaper_record(record_type: type, args: Namespace) -> Any:
        # raw_input 直接取 url / doi / name，保持与 gPaper CLI 输入语义一致。
        return record_type(
            index=1,
            raw_input=args.url or args.doi or args.name,
            title=args.title or (args.name if args.name else ""),
            year=args.year,
            venue=args.venue,
        )

    def resolve(self, request: PaperResolveRequest | PaperDownloadRequest) -> Any:
        record_type, _, downloader_type, resolver_type = self.load_getpaper_backend()
        args = self.build_gpaper_args(request)
        record = self.build_gpaper_record(record_type, args)
        downloader = downloader_type(args)
        resolver = resolver_type(args, downloader=downloader)
        try:
            return resolver.resolve(record, Path(args.output_dir))
        finally:
            self.close_backend_session(downloader)

    def download(self, request: PaperDownloadRequest) -> tuple[Any, dict[str, Any]]:
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
            # 先 resolve，只有确认可下载时才执行真正的 PDF 下载。
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
