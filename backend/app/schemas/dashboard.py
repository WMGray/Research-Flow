from __future__ import annotations

from pydantic import BaseModel

from backend.app.schemas.papers import BatchResponse, CandidateResponse, PaperResponse


class HomeDashboardData(BaseModel):
    totals: dict[str, int]
    status_counts: dict[str, int]
    recent_papers: list[PaperResponse]
    queue_items: list[PaperResponse]
    recent_batches: list[BatchResponse]
    paths: dict[str, str]


class PapersOverviewData(BaseModel):
    papers: list[PaperResponse]
    totals: dict[str, int]


class DiscoverDashboardData(BaseModel):
    summary: dict[str, int]
    batches: list[BatchResponse]
    candidates: list[CandidateResponse]

class PapersDashboardData(BaseModel):
    summary: dict[str, int]
    papers: list[PaperResponse]
    paths: dict[str, str]
