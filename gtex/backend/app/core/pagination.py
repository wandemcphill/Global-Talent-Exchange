from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Generic, Sequence, TypeVar

from pydantic import BaseModel, Field

DEFAULT_PAGE = 1
DEFAULT_PER_PAGE = 20
MAX_PER_PAGE = 100

ItemT = TypeVar("ItemT")


@dataclass(frozen=True, slots=True)
class PaginationParams:
    page: int
    per_page: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page


class PaginationMeta(BaseModel):
    page: int = Field(ge=1)
    per_page: int = Field(ge=1, le=MAX_PER_PAGE)
    total: int = Field(ge=0)
    total_pages: int = Field(ge=0)
    has_next: bool
    has_previous: bool


class PaginatedItems(BaseModel, Generic[ItemT]):
    items: list[ItemT]
    pagination: PaginationMeta


def resolve_pagination(
    *,
    page: int | None = None,
    per_page: int | None = None,
    limit: int | None = None,
    offset: int | None = None,
    default_per_page: int = DEFAULT_PER_PAGE,
    max_per_page: int = MAX_PER_PAGE,
) -> PaginationParams:
    resolved_default = max(1, min(default_per_page, max_per_page))
    if limit is not None or offset is not None:
        resolved_per_page = _clamp_per_page(limit or resolved_default, max_per_page=max_per_page)
        resolved_offset = max(0, int(offset or 0))
        return PaginationParams(
            page=max(1, (resolved_offset // resolved_per_page) + 1),
            per_page=resolved_per_page,
        )
    return PaginationParams(
        page=max(DEFAULT_PAGE, int(page or DEFAULT_PAGE)),
        per_page=_clamp_per_page(per_page or resolved_default, max_per_page=max_per_page),
    )


def build_pagination_meta(*, params: PaginationParams, total: int) -> PaginationMeta:
    safe_total = max(0, int(total))
    total_pages = ceil(safe_total / params.per_page) if safe_total else 0
    return PaginationMeta(
        page=params.page,
        per_page=params.per_page,
        total=safe_total,
        total_pages=total_pages,
        has_next=params.page < total_pages,
        has_previous=params.page > 1 and total_pages > 0,
    )


def paginate_sequence(
    items: Sequence[ItemT],
    *,
    params: PaginationParams,
) -> tuple[list[ItemT], PaginationMeta]:
    total = len(items)
    page_items = list(items[params.offset : params.offset + params.per_page])
    return page_items, build_pagination_meta(params=params, total=total)


def _clamp_per_page(value: int, *, max_per_page: int) -> int:
    return max(1, min(int(value), max_per_page))


__all__ = [
    "DEFAULT_PAGE",
    "DEFAULT_PER_PAGE",
    "MAX_PER_PAGE",
    "PaginatedItems",
    "PaginationMeta",
    "PaginationParams",
    "build_pagination_meta",
    "paginate_sequence",
    "resolve_pagination",
]
