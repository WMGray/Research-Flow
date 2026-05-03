from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FeedItemRecord:
    item_id: int
    paper_id: int
    title: str
    abstract: str
    authors: list[str]
    year: int | None
    venue: str
    source_url: str
    pdf_url: str
    score: int
    reason: str
    topic: str
    status: str
    source: str
    feed_date: str
    created_at: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class ConferenceRecord:
    conference_id: int
    name: str
    acronym: str
    year: int
    rank: str
    field: str
    abstract_deadline: str
    paper_deadline: str
    notification_date: str
    status: str
    url: str
    notes: str
    created_at: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class RecommendationRecord:
    recommendation_id: str
    target_type: str
    target_id: int
    title: str
    reason: str
    score: int
    action: str
    metadata: dict[str, str | int | float | bool | None]


@dataclass(frozen=True, slots=True)
class GraphNodeRecord:
    id: str
    label: str
    type: str
    metadata: dict[str, str | int | float | bool | None]


@dataclass(frozen=True, slots=True)
class GraphEdgeRecord:
    id: str
    source: str
    target: str
    relation: str
    metadata: dict[str, str | int | float | bool | None]


@dataclass(frozen=True, slots=True)
class GraphRecord:
    nodes: list[GraphNodeRecord]
    edges: list[GraphEdgeRecord]
