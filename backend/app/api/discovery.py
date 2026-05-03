from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.papers import envelope
from app.schemas.discovery import (
    ConferenceCreateRequest,
    ConferenceResponse,
    ConferenceUpdateRequest,
    FeedItemResponse,
    FeedItemUpdateRequest,
    FeedRefreshRequest,
    GraphResponse,
    RecommendationResponse,
)
from app.schemas.papers import APIEnvelope
from core.services.discovery import DiscoveryRepository


router = APIRouter(prefix="/api/v1", tags=["discovery"])


def get_discovery_repository() -> DiscoveryRepository:
    return DiscoveryRepository()


def _today() -> str:
    return datetime.now(UTC).date().isoformat()


def _not_found(exc: KeyError) -> HTTPException:
    return HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": str(exc)})


@router.post(
    "/feed/refresh",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=APIEnvelope,
)
def refresh_feed(
    request: FeedRefreshRequest,
    repository: DiscoveryRepository = Depends(get_discovery_repository),
) -> APIEnvelope:
    feed_date = request.feed_date or _today()
    if request.source == "arxiv":
        try:
            records = repository.refresh_feed_from_arxiv(
                feed_date=feed_date,
                categories=request.categories or None,
                limit=request.limit,
                query=request.query,
            )
        except RuntimeError as exc:
            raise HTTPException(
                status_code=502,
                detail={"code": "ARXIV_FETCH_FAILED", "message": str(exc)},
            ) from exc
    else:
        records = repository.refresh_feed_from_papers(
            feed_date=feed_date,
            topic=request.topic,
            limit=request.limit,
        )
    return envelope(
        [FeedItemResponse.model_validate(asdict(record)) for record in records],
        meta={"feed_date": feed_date, "source": request.source, "total": len(records)},
    )


@router.get("/feed/items", response_model=APIEnvelope)
def list_feed_items(
    feed_date: str = "",
    q: str = "",
    status_filter: str = Query(default="", alias="status"),
    page: int = 1,
    page_size: int = 20,
    repository: DiscoveryRepository = Depends(get_discovery_repository),
) -> APIEnvelope:
    records, total = repository.list_feed_items(
        {
            "feed_date": feed_date,
            "q": q,
            "status": status_filter,
            "page": page,
            "page_size": page_size,
        }
    )
    return envelope(
        [FeedItemResponse.model_validate(asdict(record)) for record in records],
        meta={"page": page, "page_size": page_size, "total": total},
    )


@router.patch("/feed/items/{item_id}", response_model=APIEnvelope)
def update_feed_item(
    item_id: int,
    request: FeedItemUpdateRequest,
    repository: DiscoveryRepository = Depends(get_discovery_repository),
) -> APIEnvelope:
    try:
        record = repository.update_feed_item(item_id, request.model_dump(exclude_unset=True))
        return envelope(FeedItemResponse.model_validate(asdict(record)))
    except KeyError as exc:
        raise _not_found(exc) from exc


@router.post(
    "/conferences",
    status_code=status.HTTP_201_CREATED,
    response_model=APIEnvelope,
)
def create_conference(
    request: ConferenceCreateRequest,
    repository: DiscoveryRepository = Depends(get_discovery_repository),
) -> APIEnvelope:
    record = repository.create_conference(request.model_dump())
    return envelope(ConferenceResponse.model_validate(asdict(record)))


@router.get("/conferences", response_model=APIEnvelope)
def list_conferences(
    q: str = "",
    status_filter: str = Query(default="", alias="status"),
    page: int = 1,
    page_size: int = 20,
    repository: DiscoveryRepository = Depends(get_discovery_repository),
) -> APIEnvelope:
    records, total = repository.list_conferences(
        {"q": q, "status": status_filter, "page": page, "page_size": page_size}
    )
    return envelope(
        [ConferenceResponse.model_validate(asdict(record)) for record in records],
        meta={"page": page, "page_size": page_size, "total": total},
    )


@router.get("/conferences/{conference_id}", response_model=APIEnvelope)
def get_conference(
    conference_id: int,
    repository: DiscoveryRepository = Depends(get_discovery_repository),
) -> APIEnvelope:
    try:
        record = repository.get_conference(conference_id)
        return envelope(ConferenceResponse.model_validate(asdict(record)))
    except KeyError as exc:
        raise _not_found(exc) from exc


@router.patch("/conferences/{conference_id}", response_model=APIEnvelope)
def update_conference(
    conference_id: int,
    request: ConferenceUpdateRequest,
    repository: DiscoveryRepository = Depends(get_discovery_repository),
) -> APIEnvelope:
    try:
        record = repository.update_conference(
            conference_id,
            request.model_dump(exclude_unset=True),
        )
        return envelope(ConferenceResponse.model_validate(asdict(record)))
    except KeyError as exc:
        raise _not_found(exc) from exc


@router.get("/recommendations", response_model=APIEnvelope)
def list_recommendations(
    limit: int = Query(default=10, ge=1, le=100),
    repository: DiscoveryRepository = Depends(get_discovery_repository),
) -> APIEnvelope:
    records = repository.list_recommendations(limit=limit)
    return envelope(
        [RecommendationResponse.model_validate(asdict(record)) for record in records],
        meta={"total": len(records)},
    )


@router.get("/graph", response_model=APIEnvelope)
def get_graph(
    limit: int = Query(default=200, ge=1, le=500),
    repository: DiscoveryRepository = Depends(get_discovery_repository),
) -> APIEnvelope:
    graph = repository.get_graph(limit=limit)
    return envelope(GraphResponse.model_validate(asdict(graph)))
