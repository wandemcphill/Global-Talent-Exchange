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
class ScoutingSignal:
    watchlist_adds: int = 0
    shortlist_adds: int = 0
    transfer_room_adds: int = 0
    scouting_activity: int = 0
    suspicious_watchlist_adds: int = 0
    suspicious_shortlist_adds: int = 0
    suspicious_transfer_room_adds: int = 0
    suspicious_scouting_activity: int = 0

    def eligible_counts(self) -> dict[str, int]:
        return {
            "watchlist_adds": max(self.watchlist_adds - self.suspicious_watchlist_adds, 0),
            "shortlist_adds": max(self.shortlist_adds - self.suspicious_shortlist_adds, 0),
            "transfer_room_adds": max(self.transfer_room_adds - self.suspicious_transfer_room_adds, 0),
            "scouting_activity": max(self.scouting_activity - self.suspicious_scouting_activity, 0),
        }


@dataclass(frozen=True, slots=True)
class MarketPulse:
    midpoint_price_credits: float | None = None
    best_bid_price_credits: float | None = None
    best_ask_price_credits: float | None = None
    last_trade_price_credits: float | None = None
    trade_prints: tuple["TradePrint", ...] = ()
    holder_count: int | None = None
    top_holder_share_pct: float | None = None
    top_3_holder_share_pct: float | None = None

    def snapshot_price_credits(self) -> float | None:
        if self.midpoint_price_credits is not None and self.midpoint_price_credits > 0:
            return round(self.midpoint_price_credits, 2)
        if (
            self.best_bid_price_credits is not None
            and self.best_bid_price_credits > 0
            and self.best_ask_price_credits is not None
            and self.best_ask_price_credits > 0
        ):
            return round((self.best_bid_price_credits + self.best_ask_price_credits) / 2.0, 2)
        if self.best_bid_price_credits is not None and self.best_bid_price_credits > 0:
            return round(self.best_bid_price_credits, 2)
        if self.best_ask_price_credits is not None and self.best_ask_price_credits > 0:
            return round(self.best_ask_price_credits, 2)
        return None


@dataclass(frozen=True, slots=True)
class TradePrint:
    trade_id: str
    seller_user_id: str
    buyer_user_id: str
    price_credits: float
    occurred_at: datetime
    quantity: int = 1
    shadow_ignored: bool = False


@dataclass(frozen=True, slots=True)
class PlayerValueInput:
    player_id: str
    player_name: str
    as_of: datetime
    reference_market_value_eur: float
    current_credits: float | None = None
    previous_ftv_credits: float | None = None
    previous_pcv_credits: float | None = None
    previous_gsi_score: float | None = None
    liquidity_band: str | None = None
    match_events: tuple[NormalizedMatchEvent, ...] = ()
    transfer_events: tuple[NormalizedTransferEvent, ...] = ()
    award_events: tuple[NormalizedAwardEvent, ...] = ()
    demand_signal: DemandSignal = field(default_factory=DemandSignal)
    scouting_signal: ScoutingSignal = field(default_factory=ScoutingSignal)
    market_pulse: MarketPulse = field(default_factory=MarketPulse)


@dataclass(frozen=True, slots=True)
class ValueBreakdown:
    baseline_credits: float
    football_truth_value_credits: float
    market_signal_value_credits: float
    published_card_value_credits: float
    blended_target_credits: float
    band_limited_target_credits: float
    liquidity_weight: float
    snapshot_market_price_credits: float | None
    quoted_market_price_credits: float | None
    trusted_trade_price_credits: float | None
    price_band_floor_credits: float
    price_band_ceiling_credits: float
    anti_manipulation_guard_multiplier: float
    anchor_adjustment_pct: float
    performance_adjustment_pct: float
    transfer_adjustment_pct: float
    award_adjustment_pct: float
    demand_adjustment_pct: float
    market_price_adjustment_pct: float
    market_signal_adjustment_pct: float
    truth_uncapped_adjustment_pct: float
    truth_capped_adjustment_pct: float
    uncapped_adjustment_pct: float
    capped_adjustment_pct: float
    trade_trust_score: float
    trusted_trade_count: int
    suspicious_trade_count: int
    wash_trade_count: int
    circular_trade_count: int
    shadow_ignored_trade_count: int
    unique_trade_participants: int
    holder_count: int | None
    top_holder_share_pct: float | None
    top_3_holder_share_pct: float | None
    holder_concentration_penalty_pct: float
    thin_market: bool


@dataclass(frozen=True, slots=True)
class ScoutingIndexBreakdown:
    neutral_score: float
    previous_score: float
    target_score: float
    weighted_signal_volume: float
    eligible_watchlist_adds: int
    eligible_shortlist_adds: int
    eligible_transfer_room_adds: int
    eligible_scouting_activity: int
    anchor_adjustment_pct: float
    scouting_signal_adjustment_pct: float
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
    football_truth_value_credits: float
    market_signal_value_credits: float
    previous_global_scouting_index: float
    global_scouting_index: float
    global_scouting_index_movement_pct: float
    breakdown: ValueBreakdown
    global_scouting_index_breakdown: ScoutingIndexBreakdown
    drivers: tuple[str, ...]

    @property
    def published_card_value_credits(self) -> float:
        return self.target_credits
