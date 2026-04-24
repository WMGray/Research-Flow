"""论文下载共享服务。

该服务封装 gPaper 的解析与下载能力，供 FastAPI app、Celery worker 和脚本共同调用。
"""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path
from typing import Any, Protocol

from core.config import backend_root, get_settings


STATUS_READY = "ready_download"


class PaperResolveInput(Protocol):
    """论文解析所需的最小输入协议，避免 core 依赖 FastAPI schema。"""

    url: str | None
    doi: str | None
    name: str | None
    title: str
    year: str
    venue: str


class PaperDownloadInput(PaperResolveInput, Protocol):
    """论文下载在解析输入之外额外需要的运行时选项。"""

    output_dir: str | None
    overwrite: bool | None


class PaperDownloadService:
    """统一管理论文解析、下载参数构造和 gPaper 后端适配。"""

    @staticmethod
    def _configured_output_dir() -> Path:
        """解析配置中的默认论文下载目录。"""

        path = Path(get_settings().paper_download.output_dir).expanduser()
        if not path.is_absolute():
            path = (backend_root() / path).resolve()
        return path.resolve()

    @staticmethod
    def _resolve_output_dir(output_dir: str | None) -> Path:
        """解析单次请求输出目录，并限制其不能逃逸默认下载目录。"""

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
        request: PaperResolveInput,
    ) -> Namespace:
        """将 API 请求和运行配置合并成 gPaper CLI 风格参数。"""

        # gPaper 原生入口就是 url / doi / name 三选一；这里只补齐运行配置。
        settings = get_settings().paper_download
        request_output_dir = getattr(request, "output_dir", None)
        request_overwrite = getattr(request, "overwrite", None)
        overwrite = settings.overwrite if request_overwrite is None else request_overwrite
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
            overwrite=overwrite,
        )

    @staticmethod
    def load_getpaper_backend() -> tuple[type, type, type, type]:
        """延迟加载 gPaper 依赖，避免应用启动阶段被可选依赖阻塞。"""

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
        """关闭 gPaper downloader 内部复用的 HTTP session。"""

        # gPaper 内部复用 requests.Session；每次服务调用结束后主动关闭连接。
        session = getattr(downloader, "session", None)
        if session is not None and hasattr(session, "close"):
            session.close()

    @staticmethod
    def build_gpaper_record(record_type: type, args: Namespace) -> Any:
        """根据请求参数构造 gPaper Record 对象。"""

        # raw_input 直接取 url / doi / name，保持与 gPaper CLI 输入语义一致。
        return record_type(
            index=1,
            raw_input=args.url or args.doi or args.name,
            title=args.title or (args.name if args.name else ""),
            year=args.year,
            venue=args.venue,
        )

    def resolve(self, request: PaperResolveInput) -> Any:
        """只解析论文来源，不执行 PDF 下载。"""

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
        """解析论文并在状态允许时下载 PDF。"""

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
