"""论文下载 API 路由。

本文件只负责 HTTP 请求/响应转换，具体解析和下载逻辑委托给 core 服务层。
"""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends

from app.schemas.paper_download import (
    PaperDownloadRequest,
    PaperDownloadResponse,
    PaperResolveRequest,
    PaperResolveResponse,
)
from core.services.paper_download.service import PaperDownloadService


router = APIRouter(prefix="/paper-download", tags=["paper_download"])


def get_paper_download_service() -> PaperDownloadService:
    """创建论文下载服务实例，供 FastAPI 依赖注入使用。"""

    return PaperDownloadService()


@router.post("/resolve", response_model=PaperResolveResponse)
def resolve_paper(
    request: PaperResolveRequest,
    service: PaperDownloadService = Depends(get_paper_download_service),
) -> PaperResolveResponse:
    """根据 URL、DOI 或标题解析论文元数据与可下载 PDF 地址。"""

    # 直接透传到适配层，保持接口薄、业务逻辑集中在 service。
    row = service.resolve(request)
    return PaperResolveResponse.model_validate(asdict(row))


@router.post("/download", response_model=PaperDownloadResponse)
def download_paper(
    request: PaperDownloadRequest,
    service: PaperDownloadService = Depends(get_paper_download_service),
) -> PaperDownloadResponse:
    """解析论文并在可下载时保存 PDF 文件。"""

    # 先 resolve，再在 service 内决定是否继续 download。
    row, result = service.download(request)
    # 目前暂时先返回这些信息
    return PaperDownloadResponse(
        resolution=PaperResolveResponse.model_validate(asdict(row)),
        download_status=result.get("status", ""),
        file_path=result.get("file_path") or None,
        detail=result.get("detail", ""),
        error_code=result.get("error_code", ""),
    )
