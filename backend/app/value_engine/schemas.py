from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.app.ingestion.models import (
    CompetitionContext,
    NormalizedAwardEvent,
    NormalizedMatchEvent,
    NormalizedTransferEvent,
)
from backend.app.value_engine.models import DemandSignal, PlayerValueInput


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


class PlayerValueInputPayload(BaseModel):
    player_id: str = Field(min_length=1)
    player_name: str = Field(min_length=1)
    reference_market_value_eur: float = Field(gt=0)
    current_credits: float | None = Field(default=None, ge=0)
    match_events: tuple[MatchEventPayload, ...] = ()
    transfer_events: tuple[TransferEventPayload, ...] = ()
    award_events: tuple[AwardEventPayload, ...] = ()
    demand_signal: DemandSignalPayload = Field(default_factory=DemandSignalPayload)

    def to_domain(self, as_of: datetime) -> PlayerValueInput:
        return PlayerValueInput(
            player_id=self.player_id,
            player_name=self.player_name,
            as_of=as_of,
            reference_market_value_eur=self.reference_market_value_eur,
            current_credits=self.current_credits,
            match_events=tuple(event.to_domain() for event in self.match_events),
            transfer_events=tuple(event.to_domain() for event in self.transfer_events),
            award_events=tuple(event.to_domain() for event in self.award_events),
            demand_signal=self.demand_signal.to_domain(),
        )


class ValueSnapshotBatchRequest(BaseModel):
    as_of: datetime
    lookback_days: int = Field(default=7, ge=1)
    inputs: list[PlayerValueInputPayload] = Field(min_length=1)


class ValueBreakdownView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    baseline_credits: float
    anchor_adjustment_pct: float
    performance_adjustment_pct: float
    transfer_adjustment_pct: float
    award_adjustment_pct: float
    demand_adjustment_pct: float
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
    breakdown: ValueBreakdownView
    drivers: tuple[str, ...]


class ValueSnapshotBatchResponse(BaseModel):
    snapshots: list[ValueSnapshotView]
