from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CategoryCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    parent_id: int | None = None
    sort_order: int = 0


class CategoryUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1)
    parent_id: int | None = None
    sort_order: int | None = None

    @model_validator(mode="after")
    def validate_has_update(self) -> "CategoryUpdateRequest":
        if not self.model_dump(exclude_unset=True):
            raise ValueError("At least one field must be provided.")
        return self


class CategoryResponse(BaseModel):
    category_id: int
    name: str
    parent_id: int | None = None
    path: str
    sort_order: int
    paper_count: int = 0


class CategoryTreeResponse(CategoryResponse):
    children: list["CategoryTreeResponse"] = Field(default_factory=list)
