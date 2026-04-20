from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends

from app.schemas.paper_download import (
    PaperDownloadRequest,
    PaperDownloadResponse,
    PaperResolveRequest,
    PaperResolveResponse,
)
from app.services.paper_download.service import PaperDownloadService


router = APIRouter(prefix="/paper-download", tags=["paper_download"])


def get_paper_download_service() -> PaperDownloadService:
    return PaperDownloadService()


@router.post("/resolve", response_model=PaperResolveResponse)
def resolve_paper(
    request: PaperResolveRequest,
    service: PaperDownloadService = Depends(get_paper_download_service),
) -> PaperResolveResponse:
    # 直接透传到适配层，保持接口薄、业务逻辑集中在 service。
    row = service.resolve(request)
    return PaperResolveResponse.model_validate(asdict(row))


@router.post("/download", response_model=PaperDownloadResponse)
def download_paper(
    request: PaperDownloadRequest,
    service: PaperDownloadService = Depends(get_paper_download_service),
) -> PaperDownloadResponse:
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
