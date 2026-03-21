from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.ingestion.models import NormalizedAwardEvent, NormalizedMatchEvent, NormalizedTransferEvent


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

    def eligible_volume(self) -> int:
        return sum(self.eligible_counts().values())


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

    def eligible_volume(self) -> int:
        return sum(self.eligible_counts().values())


@dataclass(frozen=True, slots=True)
class EGameSignal:
    selection_count: int = 0
    captain_count: int = 0
    contest_win_count: int = 0
    spotlight_count: int = 0
    featured_performance_count: int = 0
    suspicious_selection_count: int = 0
    suspicious_contest_count: int = 0
    suspicious_spotlight_count: int = 0

    def eligible_counts(self) -> dict[str, int]:
        return {
            "selection_count": max(self.selection_count - self.suspicious_selection_count, 0),
            "captain_count": max(self.captain_count - self.suspicious_selection_count, 0),
            "contest_win_count": max(self.contest_win_count - self.suspicious_contest_count, 0),
            "spotlight_count": max(self.spotlight_count - self.suspicious_spotlight_count, 0),
            "featured_performance_count": max(self.featured_performance_count - self.suspicious_contest_count, 0),
        }

    def sample_size(self) -> int:
        return sum(self.eligible_counts().values())


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
class HistoricalValuePoint:
    as_of: datetime
    published_value_credits: float
    football_truth_value_credits: float | None = None
    market_signal_value_credits: float | None = None
    confidence_score: float | None = None
    snapshot_type: str = "intraday"


@dataclass(frozen=True, slots=True)
class ReferenceValueContext:
    market_value_eur: float
    source: str
    confidence_tier: str
    confidence_score: float
    staleness_days: int = 0
    is_stale: bool = False
    blended_with_profile_baseline: bool = False


@dataclass(frozen=True, slots=True)
class PlayerProfileContext:
    age_years: float | None = None
    position_family: str = "midfielder"
    position_subrole: str | None = None
    club_tier: str | None = None
    competition_tier: str | None = None
    competition_strength: float | None = None
    club_prestige: float | None = None
    continental_visibility: float | None = None
    appearances: int = 0
    starts: int = 0
    minutes_played: int = 0
    recent_form_rating: float | None = None
    goals: int = 0
    assists: int = 0
    clean_sheets: int = 0
    saves: int = 0
    captaincy_flag: bool = False
    leadership_flag: bool = False
    injury_absence_days: int = 0
    transfer_interest_score: float = 0.0
    profile_completeness_score: float | None = None
    player_class: str = "established"


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
    egame_signal: EGameSignal = field(default_factory=EGameSignal)
    market_pulse: MarketPulse = field(default_factory=MarketPulse)
    profile_context: PlayerProfileContext = field(default_factory=PlayerProfileContext)
    reference_context: ReferenceValueContext | None = None
    historical_values: tuple[HistoricalValuePoint, ...] = ()
    snapshot_type: str = "intraday"
    candidate_reasons: tuple[str, ...] = ()


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
    scouting_signal_value_credits: float = 0.0
    egame_signal_value_credits: float = 0.0
    reference_market_value_eur: float = 0.0
    seeded_reference_market_value_eur: float = 0.0
    reference_value_source: str = "heuristic"
    reference_confidence_tier: str = "heuristic_only"
    reference_confidence_score: float = 0.0
    reference_staleness_days: int = 0
    position_family: str = "midfielder"
    position_subrole: str | None = None
    player_class: str = "established"
    age_curve_multiplier: float = 1.0
    competition_quality_multiplier: float = 1.0
    club_quality_multiplier: float = 1.0
    visibility_multiplier: float = 1.0
    injury_adjustment_pct: float = 0.0
    scouting_adjustment_pct: float = 0.0
    egame_adjustment_pct: float = 0.0
    momentum_7d_pct: float = 0.0
    momentum_30d_pct: float = 0.0
    momentum_adjustment_pct: float = 0.0
    trend_confidence: float = 0.0
    confidence_score: float = 0.0
    market_integrity_score: float = 0.0
    signal_trust_score: float = 0.0
    participant_diversity_score: float = 0.0
    price_discovery_confidence: float = 0.0
    low_liquidity_penalty_pct: float = 0.0
    suspicious_signal_suppression_multiplier: float = 1.0
    weight_profile_code: str = "default"
    reason_codes: tuple[str, ...] = ()
    integrity_flags: tuple[str, ...] = ()


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
    scouting_signal_value_credits: float
    egame_signal_value_credits: float
    previous_global_scouting_index: float
    global_scouting_index: float
    global_scouting_index_movement_pct: float
    confidence_score: float
    confidence_tier: str
    liquidity_tier: str
    market_integrity_score: float
    signal_trust_score: float
    trend_7d_pct: float
    trend_30d_pct: float
    trend_direction: str
    trend_confidence: float
    snapshot_type: str
    config_version: str
    breakdown: ValueBreakdown
    global_scouting_index_breakdown: ScoutingIndexBreakdown
    drivers: tuple[str, ...]
    reason_codes: tuple[str, ...]

    @property
    def published_card_value_credits(self) -> float:
        return self.target_credits
