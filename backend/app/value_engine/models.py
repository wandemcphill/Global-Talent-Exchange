from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from backend.app.ingestion.models import NormalizedAwardEvent, NormalizedMatchEvent, NormalizedTransferEvent


@dataclass(frozen=True, slots=True)
class DemandSignal:
    purchases: int = 0
    sales: int = 0
    shortlist_adds: int = 0
    watchlist_adds: int = 0
    follows: int = 0
    suspicious_purchases: int = 0
    suspicious_sales: int = 0
    suspicious_shortlist_adds: int = 0
    suspicious_watchlist_adds: int = 0
    suspicious_follows: int = 0

    def eligible_counts(self) -> dict[str, int]:
        return {
            "purchases": max(self.purchases - self.suspicious_purchases, 0),
            "sales": max(self.sales - self.suspicious_sales, 0),
            "shortlist_adds": max(self.shortlist_adds - self.suspicious_shortlist_adds, 0),
            "watchlist_adds": max(self.watchlist_adds - self.suspicious_watchlist_adds, 0),
            "follows": max(self.follows - self.suspicious_follows, 0),
        }


@dataclass(frozen=True, slots=True)
class PlayerValueInput:
    player_id: str
    player_name: str
    as_of: datetime
    reference_market_value_eur: float
    current_credits: float | None = None
    match_events: tuple[NormalizedMatchEvent, ...] = ()
    transfer_events: tuple[NormalizedTransferEvent, ...] = ()
    award_events: tuple[NormalizedAwardEvent, ...] = ()
    demand_signal: DemandSignal = field(default_factory=DemandSignal)


@dataclass(frozen=True, slots=True)
class ValueBreakdown:
    baseline_credits: float
    anchor_adjustment_pct: float
    performance_adjustment_pct: float
    transfer_adjustment_pct: float
    award_adjustment_pct: float
    demand_adjustment_pct: float
    uncapped_adjustment_pct: float
    capped_adjustment_pct: float


@dataclass(frozen=True, slots=True)
class ValueSnapshot:
    player_id: str
    player_name: str
    as_of: datetime
    previous_credits: float
    target_credits: float
    movement_pct: float
    breakdown: ValueBreakdown
    drivers: tuple[str, ...]
