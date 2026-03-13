from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.app.ingestion.models import (
    CompetitionContext,
    NormalizedAwardEvent,
    NormalizedMatchEvent,
    NormalizedTransferEvent,
)
from backend.app.value_engine.models import (
    DemandSignal,
    EGameSignal,
    HistoricalValuePoint,
    MarketPulse,
    PlayerProfileContext,
    PlayerValueInput,
    ReferenceValueContext,
    ScoutingSignal,
    TradePrint,
)


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
        return DemandSignal(**self.model_dump())


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
        return ScoutingSignal(**self.model_dump())


class EGameSignalPayload(BaseModel):
    selection_count: int = Field(default=0, ge=0)
    captain_count: int = Field(default=0, ge=0)
    contest_win_count: int = Field(default=0, ge=0)
    spotlight_count: int = Field(default=0, ge=0)
    featured_performance_count: int = Field(default=0, ge=0)
    suspicious_selection_count: int = Field(default=0, ge=0)
    suspicious_contest_count: int = Field(default=0, ge=0)
    suspicious_spotlight_count: int = Field(default=0, ge=0)

    def to_domain(self) -> EGameSignal:
        return EGameSignal(**self.model_dump())


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


class ReferenceValueContextPayload(BaseModel):
    market_value_eur: float = Field(gt=0)
    source: str = Field(min_length=1)
    confidence_tier: str = Field(min_length=1)
    confidence_score: float = Field(ge=0, le=100)
    staleness_days: int = Field(default=0, ge=0)
    is_stale: bool = False
    blended_with_profile_baseline: bool = False

    def to_domain(self) -> ReferenceValueContext:
        return ReferenceValueContext(**self.model_dump())


class PlayerProfileContextPayload(BaseModel):
    age_years: float | None = Field(default=None, ge=0)
    position_family: str = "midfielder"
    position_subrole: str | None = None
    club_tier: str | None = None
    competition_tier: str | None = None
    competition_strength: float | None = None
    club_prestige: float | None = None
    continental_visibility: float | None = None
    appearances: int = Field(default=0, ge=0)
    starts: int = Field(default=0, ge=0)
    minutes_played: int = Field(default=0, ge=0)
    recent_form_rating: float | None = None
    goals: int = Field(default=0, ge=0)
    assists: int = Field(default=0, ge=0)
    clean_sheets: int = Field(default=0, ge=0)
    saves: int = Field(default=0, ge=0)
    captaincy_flag: bool = False
    leadership_flag: bool = False
    injury_absence_days: int = Field(default=0, ge=0)
    transfer_interest_score: float = Field(default=0.0, ge=0)
    profile_completeness_score: float | None = None
    player_class: str = "established"

    def to_domain(self) -> PlayerProfileContext:
        return PlayerProfileContext(**self.model_dump())


class HistoricalValuePointPayload(BaseModel):
    as_of: datetime
    published_value_credits: float = Field(ge=0)
    football_truth_value_credits: float | None = Field(default=None, ge=0)
    market_signal_value_credits: float | None = Field(default=None, ge=0)
    confidence_score: float | None = Field(default=None, ge=0, le=100)
    snapshot_type: str = "intraday"

    def to_domain(self) -> HistoricalValuePoint:
        return HistoricalValuePoint(**self.model_dump())


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
    egame_signal: EGameSignalPayload | None = None
    market_pulse: MarketPulsePayload = Field(default_factory=MarketPulsePayload)
    profile_context: PlayerProfileContextPayload | None = None
    reference_context: ReferenceValueContextPayload | None = None
    historical_values: tuple[HistoricalValuePointPayload, ...] = ()
    snapshot_type: str = "intraday"
    candidate_reasons: tuple[str, ...] = ()

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
            egame_signal=self.egame_signal.to_domain() if self.egame_signal is not None else EGameSignal(),
            market_pulse=self.market_pulse.to_domain(),
            profile_context=self.profile_context.to_domain() if self.profile_context is not None else PlayerProfileContext(),
            reference_context=self.reference_context.to_domain() if self.reference_context is not None else None,
            historical_values=tuple(item.to_domain() for item in self.historical_values),
            snapshot_type=self.snapshot_type,
            candidate_reasons=self.candidate_reasons,
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
    scouting_signal_value_credits: float | None = None
    egame_signal_value_credits: float | None = None
    reference_market_value_eur: float | None = None
    seeded_reference_market_value_eur: float | None = None
    reference_value_source: str | None = None
    reference_confidence_tier: str | None = None
    reference_confidence_score: float | None = None
    reference_staleness_days: int | None = None
    position_family: str | None = None
    position_subrole: str | None = None
    player_class: str | None = None
    age_curve_multiplier: float | None = None
    competition_quality_multiplier: float | None = None
    club_quality_multiplier: float | None = None
    visibility_multiplier: float | None = None
    injury_adjustment_pct: float | None = None
    scouting_adjustment_pct: float | None = None
    egame_adjustment_pct: float | None = None
    momentum_7d_pct: float | None = None
    momentum_30d_pct: float | None = None
    momentum_adjustment_pct: float | None = None
    trend_confidence: float | None = None
    confidence_score: float | None = None
    market_integrity_score: float | None = None
    signal_trust_score: float | None = None
    participant_diversity_score: float | None = None
    price_discovery_confidence: float | None = None
    low_liquidity_penalty_pct: float | None = None
    suspicious_signal_suppression_multiplier: float | None = None
    weight_profile_code: str | None = None


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
    scouting_signal_value_credits: float | None = None
    egame_signal_value_credits: float | None = None
    previous_global_scouting_index: float
    global_scouting_index: float
    global_scouting_index_movement_pct: float
    published_card_value_credits: float
    confidence_score: float | None = None
    confidence_tier: str | None = None
    liquidity_tier: str | None = None
    market_integrity_score: float | None = None
    signal_trust_score: float | None = None
    trend_7d_pct: float | None = None
    trend_30d_pct: float | None = None
    trend_direction: str | None = None
    trend_confidence: float | None = None
    snapshot_type: str = "intraday"
    config_version: str | None = None
    movement_tags: tuple[str, ...] = ()
    breakdown: ValueBreakdownView
    global_scouting_index_breakdown: ScoutingIndexBreakdownView
    drivers: tuple[str, ...]


class ValueHistoryResponse(BaseModel):
    snapshots: list[ValueSnapshotView]


class ValueSnapshotBatchResponse(BaseModel):
    snapshots: list[ValueSnapshotView]


class ValueSnapshotRebuildRequest(BaseModel):
    as_of: datetime | None = None
    lookback_days: int | None = Field(default=None, ge=1)
    player_ids: list[str] | None = None
    snapshot_type: str = "intraday"


class ValueDailyCloseView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    player_id: str
    player_name: str
    close_date: date
    close_credits: float
    football_truth_value_credits: float
    market_signal_value_credits: float
    scouting_signal_value_credits: float | None = None
    egame_signal_value_credits: float | None = None
    confidence_score: float | None = None
    confidence_tier: str | None = None
    liquidity_tier: str | None = None
    trend_7d_pct: float | None = None
    trend_30d_pct: float | None = None
    trend_direction: str | None = None
    trend_confidence: float | None = None
    movement_tags: tuple[str, ...] = ()


class ValueDailyCloseResponse(BaseModel):
    closes: list[ValueDailyCloseView]


class ValueTrendSummaryView(BaseModel):
    player_id: str
    current_value_credits: float
    trend_7d_pct: float
    trend_30d_pct: float
    trend_direction: str
    trend_confidence: float
    confidence_tier: str
    movement_tags: tuple[str, ...]


class ValueRecomputeRequest(BaseModel):
    as_of: datetime | None = None
    lookback_days: int | None = Field(default=None, ge=1)
    player_ids: list[str] | None = None
    tempo: str = Field(default="hourly", pattern="^(fast|hourly|daily|manual)$")
    limit: int | None = Field(default=None, ge=1)
    snapshot_type: str = "intraday"


class ValueRunRecordView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_type: str
    status: str
    as_of: datetime
    config_version: str
    triggered_by: str
    actor_user_id: str | None
    candidate_count: int
    processed_count: int
    snapshot_count: int
    started_at: datetime | None
    completed_at: datetime | None
    notes_json: dict
    error_message: str | None


class ValueRunHistoryResponse(BaseModel):
    runs: list[ValueRunRecordView]


class ValueRecomputeCandidateView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    player_id: str
    player_name: str | None
    status: str
    requested_tempo: str
    priority: int
    trigger_count: int
    signal_delta_score: float
    last_event_at: datetime | None
    last_requested_at: datetime | None
    claimed_at: datetime | None
    processed_at: datetime | None
    next_eligible_at: datetime | None
    last_error: str | None
    reason_codes: tuple[str, ...]
    metadata: dict


class ValueCandidateResponse(BaseModel):
    candidates: list[ValueRecomputeCandidateView]


class ValueAdminAuditView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    action_type: str
    actor_user_id: str | None
    actor_role: str | None
    config_version: str | None
    target_player_id: str | None
    payload_json: dict
    is_override: bool


class ValueAdminAuditResponse(BaseModel):
    audits: list[ValueAdminAuditView]


class AdminValueInspectionView(BaseModel):
    latest_snapshot: ValueSnapshotView | None
    candidate: ValueRecomputeCandidateView | None
    history: list[ValueSnapshotView]
    daily_closes: list[ValueDailyCloseView]

