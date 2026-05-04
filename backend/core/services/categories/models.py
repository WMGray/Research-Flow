from __future__ import annotations

from dataclasses import dataclass


class CategoryRepositoryError(RuntimeError):
    code = "CATEGORY_REPOSITORY_ERROR"


class CategoryNotFoundError(CategoryRepositoryError):
    code = "CATEGORY_NOT_FOUND"


class CategoryConflictError(CategoryRepositoryError):
    code = "CATEGORY_CONFLICT"


class CategoryInUseError(CategoryRepositoryError):
    code = "CATEGORY_IN_USE"


class CategoryInvalidParentError(CategoryRepositoryError):
    code = "CATEGORY_INVALID_PARENT"


@dataclass(frozen=True, slots=True)
class CategoryRecord:
    category_id: int
    name: str
    parent_id: int | None
    path: str
    sort_order: int
    paper_count: int = 0


@dataclass(frozen=True, slots=True)
class CategoryCreateInput:
    name: str
    parent_id: int | None = None
    sort_order: int = 0


@dataclass(frozen=True, slots=True)
class CategoryUpdateInput:
    name: str | None = None
    parent_id: int | None = None
    sort_order: int | None = None
