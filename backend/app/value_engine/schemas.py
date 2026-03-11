from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.app.ingestion.models import (
    CompetitionContext,
    NormalizedAwardEvent,
    NormalizedMatchEvent,
    NormalizedTransferEvent,
)
from backend.app.value_engine.models import DemandSignal, MarketPulse, PlayerValueInput, ScoutingSignal, TradePrint


class CompetitionContextPayload(BaseModel):
    competition_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    stage: str = Field(min_length=1)
    season: str | None = None
    country: str | None = None

    def to_domain(self) -> CompetitionContext:
        return CompetitionContext(
            competition_id=self.competition_id,
            name=self.name,
            stage=self.stage,
            season=self.season,
            country=self.country,
        )


class MatchEventPayload(BaseModel):
    source: str = Field(min_length=1)
    source_event_id: str = Field(min_length=1)
    match_id: str = Field(min_length=1)
    player_id: str = Field(min_length=1)
    player_name: str = Field(min_length=1)
    team_id: str = Field(min_length=1)
    team_name: str = Field(min_length=1)
    opponent_id: str = Field(min_length=1)
    opponent_name: str = Field(min_length=1)
    competition: CompetitionContextPayload
    occurred_at: datetime
    minutes: int = Field(ge=0)
    rating: float = Field(ge=0)
    goals: int = Field(default=0, ge=0)
    assists: int = Field(default=0, ge=0)
    saves: int = Field(default=0, ge=0)
    clean_sheet: bool = False
    started: bool = False
    won_match: bool = False
    won_final: bool = False
    big_moment: bool = False
    tags: tuple[str, ...] = ()

    def to_domain(self) -> NormalizedMatchEvent:
        return NormalizedMatchEvent(
            source=self.source,
            source_event_id=self.source_event_id,
            match_id=self.match_id,
            player_id=self.player_id,
            player_name=self.player_name,
            team_id=self.team_id,
            team_name=self.team_name,
            opponent_id=self.opponent_id,
            opponent_name=self.opponent_name,
            competition=self.competition.to_domain(),
            occurred_at=self.occurred_at,
            minutes=self.minutes,
            rating=self.rating,
            goals=self.goals,
            assists=self.assists,
            saves=self.saves,
            clean_sheet=self.clean_sheet,
            started=self.started,
            won_match=self.won_match,
            won_final=self.won_final,
            big_moment=self.big_moment,
            tags=self.tags,
        )


class TransferEventPayload(BaseModel):
    source: str = Field(min_length=1)
    source_event_id: str = Field(min_length=1)
    player_id: str = Field(min_length=1)
    player_name: str = Field(min_length=1)
    occurred_at: datetime
    from_club: str = Field(min_length=1)
    to_club: str = Field(min_length=1)
    from_competition: str | None = None
    to_competition: str | None = None
    reported_fee_eur: float | None = Field(default=None, gt=0)
    status: str = "rumour"

    def to_domain(self) -> NormalizedTransferEvent:
        return NormalizedTransferEvent(
            source=self.source,
            source_event_id=self.source_event_id,
            player_id=self.player_id,
            player_name=self.player_name,
            occurred_at=self.occurred_at,
            from_club=self.from_club,
            to_club=self.to_club,
            from_competition=self.from_competition,
            to_competition=self.to_competition,
            reported_fee_eur=self.reported_fee_eur,
            status=self.status,
        )


class AwardEventPayload(BaseModel):
    source: str = Field(min_length=1)
    source_event_id: str = Field(min_length=1)
    player_id: str = Field(min_length=1)
    player_name: str = Field(min_length=1)
    occurred_at: datetime
    award_code: str = Field(min_length=1)
    award_name: str = Field(min_length=1)
    rank: int | None = Field(default=None, ge=1)
    category: str | None = None

    def to_domain(self) -> NormalizedAwardEvent:
        return NormalizedAwardEvent(
            source=self.source,
            source_event_id=self.source_event_id,
            player_id=self.player_id,
            player_name=self.player_name,
            occurred_at=self.occurred_at,
            award_code=self.award_code,
            award_name=self.award_name,
            rank=self.rank,
            category=self.category,
        )


class DemandSignalPayload(BaseModel):
    purchases: int = Field(default=0, ge=0)
    sales: int = Field(default=0, ge=0)
    shortlist_adds: int = Field(default=0, ge=0)
    watchlist_adds: int = Field(default=0, ge=0)
    follows: int = Field(default=0, ge=0)
    suspicious_purchases: int = Field(default=0, ge=0)
    suspicious_sales: int = Field(default=0, ge=0)
    suspicious_shortlist_adds: int = Field(default=0, ge=0)
    suspicious_watchlist_adds: int = Field(default=0, ge=0)
    suspicious_follows: int = Field(default=0, ge=0)

    def to_domain(self) -> DemandSignal:
        return DemandSignal(
            purchases=self.purchases,
            sales=self.sales,
            shortlist_adds=self.shortlist_adds,
            watchlist_adds=self.watchlist_adds,
            follows=self.follows,
            suspicious_purchases=self.suspicious_purchases,
            suspicious_sales=self.suspicious_sales,
            suspicious_shortlist_adds=self.suspicious_shortlist_adds,
            suspicious_watchlist_adds=self.suspicious_watchlist_adds,
            suspicious_follows=self.suspicious_follows,
        )


class ScoutingSignalPayload(BaseModel):
    watchlist_adds: int = Field(default=0, ge=0)
    shortlist_adds: int = Field(default=0, ge=0)
    transfer_room_adds: int = Field(default=0, ge=0)
    scouting_activity: int = Field(default=0, ge=0)
    suspicious_watchlist_adds: int = Field(default=0, ge=0)
    suspicious_shortlist_adds: int = Field(default=0, ge=0)
    suspicious_transfer_room_adds: int = Field(default=0, ge=0)
    suspicious_scouting_activity: int = Field(default=0, ge=0)

    def to_domain(self) -> ScoutingSignal:
        return ScoutingSignal(
            watchlist_adds=self.watchlist_adds,
            shortlist_adds=self.shortlist_adds,
            transfer_room_adds=self.transfer_room_adds,
            scouting_activity=self.scouting_activity,
            suspicious_watchlist_adds=self.suspicious_watchlist_adds,
            suspicious_shortlist_adds=self.suspicious_shortlist_adds,
            suspicious_transfer_room_adds=self.suspicious_transfer_room_adds,
            suspicious_scouting_activity=self.suspicious_scouting_activity,
        )


class TradePrintPayload(BaseModel):
    trade_id: str = Field(min_length=1)
    seller_user_id: str = Field(min_length=1)
    buyer_user_id: str = Field(min_length=1)
    price_credits: float = Field(gt=0)
    occurred_at: datetime
    quantity: int = Field(default=1, ge=1)
    shadow_ignored: bool = False

    def to_domain(self) -> TradePrint:
        return TradePrint(
            trade_id=self.trade_id,
            seller_user_id=self.seller_user_id,
            buyer_user_id=self.buyer_user_id,
            price_credits=self.price_credits,
            occurred_at=self.occurred_at,
            quantity=self.quantity,
            shadow_ignored=self.shadow_ignored,
        )


class MarketPulsePayload(BaseModel):
    midpoint_price_credits: float | None = Field(default=None, gt=0)
    best_bid_price_credits: float | None = Field(default=None, gt=0)
    best_ask_price_credits: float | None = Field(default=None, gt=0)
    last_trade_price_credits: float | None = Field(default=None, gt=0)
    trade_prints: tuple[TradePrintPayload, ...] = ()
    holder_count: int | None = Field(default=None, ge=0)
    top_holder_share_pct: float | None = Field(default=None, ge=0)
    top_3_holder_share_pct: float | None = Field(default=None, ge=0)

    def to_domain(self) -> MarketPulse:
        return MarketPulse(
            midpoint_price_credits=self.midpoint_price_credits,
            best_bid_price_credits=self.best_bid_price_credits,
            best_ask_price_credits=self.best_ask_price_credits,
            last_trade_price_credits=self.last_trade_price_credits,
            trade_prints=tuple(trade.to_domain() for trade in self.trade_prints),
            holder_count=self.holder_count,
            top_holder_share_pct=self._normalize_share(self.top_holder_share_pct),
            top_3_holder_share_pct=self._normalize_share(self.top_3_holder_share_pct),
        )

    def _normalize_share(self, value: float | None) -> float | None:
        if value is None:
            return None
        normalized_value = value / 100.0 if value > 1 else value
        return min(max(normalized_value, 0.0), 1.0)


class PlayerValueInputPayload(BaseModel):
    player_id: str = Field(min_length=1)
    player_name: str = Field(min_length=1)
    reference_market_value_eur: float = Field(gt=0)
    current_credits: float | None = Field(default=None, ge=0)
    previous_ftv_credits: float | None = Field(default=None, ge=0)
    previous_pcv_credits: float | None = Field(default=None, ge=0)
    previous_gsi_score: float | None = Field(default=None, ge=0, le=100)
    liquidity_band: str | None = None
    match_events: tuple[MatchEventPayload, ...] = ()
    transfer_events: tuple[TransferEventPayload, ...] = ()
    award_events: tuple[AwardEventPayload, ...] = ()
    demand_signal: DemandSignalPayload = Field(default_factory=DemandSignalPayload)
    scouting_signal: ScoutingSignalPayload | None = None
    market_pulse: MarketPulsePayload = Field(default_factory=MarketPulsePayload)

    def to_domain(self, as_of: datetime) -> PlayerValueInput:
        demand_signal = self.demand_signal.to_domain()
        scouting_signal = (
            self.scouting_signal.to_domain()
            if self.scouting_signal is not None
            else ScoutingSignal(
                watchlist_adds=demand_signal.watchlist_adds,
                shortlist_adds=demand_signal.shortlist_adds,
                suspicious_watchlist_adds=demand_signal.suspicious_watchlist_adds,
                suspicious_shortlist_adds=demand_signal.suspicious_shortlist_adds,
            )
        )
        return PlayerValueInput(
            player_id=self.player_id,
            player_name=self.player_name,
            as_of=as_of,
            reference_market_value_eur=self.reference_market_value_eur,
            current_credits=self.current_credits,
            previous_ftv_credits=self.previous_ftv_credits,
            previous_pcv_credits=self.previous_pcv_credits,
            previous_gsi_score=self.previous_gsi_score,
            liquidity_band=self.liquidity_band,
            match_events=tuple(event.to_domain() for event in self.match_events),
            transfer_events=tuple(event.to_domain() for event in self.transfer_events),
            award_events=tuple(event.to_domain() for event in self.award_events),
            demand_signal=demand_signal,
            scouting_signal=scouting_signal,
            market_pulse=self.market_pulse.to_domain(),
        )


class ValueSnapshotBatchRequest(BaseModel):
    as_of: datetime
    lookback_days: int = Field(default=7, ge=1)
    inputs: list[PlayerValueInputPayload] = Field(min_length=1)


class ValueBreakdownView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class ScoutingIndexBreakdownView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class ValueSnapshotView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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
    published_card_value_credits: float
    breakdown: ValueBreakdownView
    global_scouting_index_breakdown: ScoutingIndexBreakdownView
    drivers: tuple[str, ...]


class ValueSnapshotBatchResponse(BaseModel):
    snapshots: list[ValueSnapshotView]


class ValueSnapshotRebuildRequest(BaseModel):
    as_of: datetime | None = None
    lookback_days: int | None = Field(default=None, ge=1)
    player_ids: list[str] | None = None
