from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable, Literal

from app.common.enums.competition_format import CompetitionFormat
from app.common.enums.competition_visibility import CompetitionVisibility


@dataclass(slots=True)
class CompetitionDiscoveryFilter:
    public_only: bool = False
    format: CompetitionFormat | None = None
    fee_filter: Literal["free", "paid", None] = None
    sort: Literal["trending", "new", "prize_pool", "fill_rate"] = "trending"
    creator_id: str | None = None
    beginner_friendly: bool | None = None


@dataclass(slots=True)
class CompetitionDiscoveryService:
    def apply_filters(
        self,
        items: Iterable[object],
        *,
        filters: CompetitionDiscoveryFilter,
        prize_pool_lookup,
        fill_rate_lookup,
    ) -> list[object]:
        filtered: list[object] = []
        for item in items:
            visibility = getattr(item, "visibility")
            if filters.public_only and visibility is not CompetitionVisibility.PUBLIC:
                continue
            if filters.format is not None and getattr(item, "format") is not filters.format:
                continue
            if filters.creator_id is not None and getattr(item, "creator_id") != filters.creator_id:
                continue
            if filters.beginner_friendly is not None and getattr(item, "beginner_friendly") != filters.beginner_friendly:
                continue

            entry_fee = getattr(item, "entry_fee")
            if filters.fee_filter == "free" and entry_fee > 0:
                continue
            if filters.fee_filter == "paid" and entry_fee <= 0:
                continue
            filtered.append(item)

        if filters.sort == "new":
            filtered.sort(key=lambda item: getattr(item, "created_at"), reverse=True)
        elif filters.sort == "prize_pool":
            filtered.sort(key=lambda item: prize_pool_lookup(item), reverse=True)
        elif filters.sort == "fill_rate":
            filtered.sort(key=lambda item: fill_rate_lookup(item), reverse=True)
        else:
            filtered.sort(
                key=lambda item: (
                    fill_rate_lookup(item),
                    prize_pool_lookup(item),
                    getattr(item, "updated_at"),
                ),
                reverse=True,
            )

        return filtered
