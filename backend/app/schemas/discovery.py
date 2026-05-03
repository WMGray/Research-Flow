from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


FeedStatus = Literal["candidate", "saved", "dismissed"]
ConferenceStatus = Literal["tracking", "submitted", "accepted", "rejected", "archived"]


class FeedItemResponse(BaseModel):
    item_id: int
    paper_id: int
    title: str
    abstract: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    venue: str = ""
    source_url: str = ""
    pdf_url: str = ""
    score: int
    reason: str
    topic: str
    status: FeedStatus
    source: str
    feed_date: str
    created_at: str
    updated_at: str


class FeedRefreshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feed_date: str = ""
    topic: str = ""
    source: Literal["paper_library", "arxiv"] = "arxiv"
    categories: list[str] = Field(default_factory=list)
    query: str = ""
    limit: int = Field(default=20, ge=1, le=100)


class FeedItemUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: FeedStatus | None = None
    topic: str | None = None
    reason: str | None = None
    score: int | None = Field(default=None, ge=0, le=100)

    @model_validator(mode="after")
    def validate_has_update(self) -> "FeedItemUpdateRequest":
        if not self.model_dump(exclude_unset=True):
            raise ValueError("At least one field must be provided.")
        return self


class ConferenceCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    acronym: str = Field(min_length=1)
    year: int
    rank: str = ""
    field: str = ""
    abstract_deadline: str = ""
    paper_deadline: str = ""
    notification_date: str = ""
    status: ConferenceStatus = "tracking"
    url: str = ""
    notes: str = ""


class ConferenceUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1)
    acronym: str | None = Field(default=None, min_length=1)
    year: int | None = None
    rank: str | None = None
    field: str | None = None
    abstract_deadline: str | None = None
    paper_deadline: str | None = None
    notification_date: str | None = None
    status: ConferenceStatus | None = None
    url: str | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def validate_has_update(self) -> "ConferenceUpdateRequest":
        if not self.model_dump(exclude_unset=True):
            raise ValueError("At least one field must be provided.")
        return self


class ConferenceResponse(ConferenceCreateRequest):
    conference_id: int
    created_at: str
    updated_at: str


class RecommendationResponse(BaseModel):
    recommendation_id: str
    target_type: str
    target_id: int
    title: str
    reason: str
    score: int
    action: str
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class GraphNodeResponse(BaseModel):
    id: str
    label: str
    type: str
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class GraphEdgeResponse(BaseModel):
    id: str
    source: str
    target: str
    relation: str
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class GraphResponse(BaseModel):
    nodes: list[GraphNodeResponse]
    edges: list[GraphEdgeResponse]
