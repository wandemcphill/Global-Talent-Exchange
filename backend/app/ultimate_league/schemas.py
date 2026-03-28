from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import Field, model_validator

from app.common.schemas.base import CommonSchema
from app.models.wallet import LedgerUnit
from app.ultimate_league.league_service import LeagueTier


class UltimateLeagueCompetitorInput(CommonSchema):
    competitor_id: str = Field(min_length=1, max_length=64)
    display_name: str = Field(min_length=1, max_length=80)
    elo_rating: int = Field(ge=0, le=4000)
    user_id: str | None = Field(default=None, min_length=1, max_length=64)
    wins: int = Field(default=0, ge=0)
    draws: int = Field(default=0, ge=0)
    losses: int = Field(default=0, ge=0)
    region: str | None = Field(default=None, min_length=2, max_length=32)
    queue_entered_at: datetime | None = None


class UltimateLeagueCompetitorView(CommonSchema):
    competitor_id: str
    display_name: str
    elo_rating: int
    user_id: str | None = None
    wins: int
    draws: int
    losses: int
    matches_played: int
    league_points: int
    win_rate: float
    tier: LeagueTier
    region: str | None = None
    queue_entered_at: datetime | None = None


class UltimateLeagueTierView(CommonSchema):
    tier: LeagueTier
    label: str
    min_elo: int
    max_elo: int | None = None
    promotion_slots: int
    relegation_slots: int
    default_tournament_size: int
    competitor_count: int = Field(default=0, ge=0)


class UltimateLeagueStandingEntryView(CommonSchema):
    rank: int
    tier: LeagueTier
    zone: str
    competitor: UltimateLeagueCompetitorView
    league_points: int
    matches_played: int
    win_rate: float


class UltimateLeagueStandingsView(CommonSchema):
    tier: LeagueTier
    entries: list[UltimateLeagueStandingEntryView]


class UltimateLeagueMatchmakingRequest(CommonSchema):
    competitor_ids: list[str] = Field(default_factory=list)
    prefer_same_tier: bool = True


class UltimateLeagueMatchProposalView(CommonSchema):
    match_id: str
    home: UltimateLeagueCompetitorView
    away: UltimateLeagueCompetitorView
    rating_gap: int
    search_window_used: int
    same_tier: bool
    same_region: bool


class UltimateLeagueMatchmakingResponse(CommonSchema):
    proposals: list[UltimateLeagueMatchProposalView]
    unmatched: list[UltimateLeagueCompetitorView]


class UltimateLeagueMatchResultRequest(CommonSchema):
    home_competitor_id: str = Field(min_length=1, max_length=64)
    away_competitor_id: str = Field(min_length=1, max_length=64)
    home_score: int = Field(ge=0, le=99)
    away_score: int = Field(ge=0, le=99)
    importance: float = Field(default=1.0, gt=0.0, le=4.0)


class UltimateLeagueRatingUpdateView(CommonSchema):
    home_competitor_id: str
    away_competitor_id: str
    expected_home_score: float
    expected_away_score: float
    actual_home_score: float
    actual_away_score: float
    home_delta: int
    away_delta: int
    home_new_rating: int
    away_new_rating: int
    effective_k_factor: float


class UltimateLeagueMatchResultResponse(CommonSchema):
    home: UltimateLeagueCompetitorView
    away: UltimateLeagueCompetitorView
    rating_update: UltimateLeagueRatingUpdateView


class UltimateLeagueTournamentRequest(CommonSchema):
    tournament_id: str | None = Field(default=None, min_length=3, max_length=64)
    tier: LeagueTier
    starts_at: datetime
    competitor_ids: list[str] = Field(default_factory=list)
    field_size: int | None = Field(default=None, ge=2, le=64)
    round_spacing_minutes: int | None = Field(default=None, ge=15, le=1440)
    match_spacing_minutes: int | None = Field(default=None, ge=5, le=720)
    parallel_matches: int | None = Field(default=None, ge=1, le=16)


class UltimateLeagueTournamentSlotView(CommonSchema):
    competitor_id: str | None = None
    display_name: str | None = None
    seed: int | None = None
    source_match_id: str | None = None
    auto_advanced: bool = False


class UltimateLeagueTournamentMatchView(CommonSchema):
    match_id: str
    round_number: int
    round_name: str
    slot_number: int
    starts_at: datetime
    home: UltimateLeagueTournamentSlotView | None = None
    away: UltimateLeagueTournamentSlotView | None = None
    winner_to_match_id: str | None = None
    bye_match: bool = False


class UltimateLeagueTournamentRoundView(CommonSchema):
    round_number: int
    round_name: str
    matches: list[UltimateLeagueTournamentMatchView]


class UltimateLeagueTournamentView(CommonSchema):
    tournament_id: str
    tier: LeagueTier
    entrants: list[UltimateLeagueCompetitorView]
    recommended_payout_percentages: list[Decimal]
    bracket_size: int
    rounds: list[UltimateLeagueTournamentRoundView]


class UltimateLeaguePayoutPreviewRequest(CommonSchema):
    placements: list[str] = Field(min_length=1)
    gross_pool_gtex: Decimal = Field(gt=Decimal("0"))
    entrant_count: int | None = Field(default=None, ge=2, le=128)
    payout_percentages: list[Decimal] | None = None

    @model_validator(mode="after")
    def validate_percentages(self) -> "UltimateLeaguePayoutPreviewRequest":
        if self.payout_percentages is not None and not self.payout_percentages:
            raise ValueError("payout_percentages cannot be empty when provided.")
        return self


class UltimateLeaguePayoutView(CommonSchema):
    tournament_id: str
    tier: LeagueTier
    placement: int
    competitor_id: str
    display_name: str
    amount: Decimal
    share_percentage: Decimal
    unit: LedgerUnit


class UltimateLeaguePayoutPreviewResponse(CommonSchema):
    tournament_id: str
    payouts: list[UltimateLeaguePayoutView]
    total_gtex: Decimal


__all__ = [
    "UltimateLeagueCompetitorInput",
    "UltimateLeagueCompetitorView",
    "UltimateLeagueMatchmakingRequest",
    "UltimateLeagueMatchmakingResponse",
    "UltimateLeagueMatchProposalView",
    "UltimateLeagueMatchResultRequest",
    "UltimateLeagueMatchResultResponse",
    "UltimateLeaguePayoutPreviewRequest",
    "UltimateLeaguePayoutPreviewResponse",
    "UltimateLeaguePayoutView",
    "UltimateLeagueRatingUpdateView",
    "UltimateLeagueStandingEntryView",
    "UltimateLeagueStandingsView",
    "UltimateLeagueTierView",
    "UltimateLeagueTournamentMatchView",
    "UltimateLeagueTournamentRequest",
    "UltimateLeagueTournamentRoundView",
    "UltimateLeagueTournamentSlotView",
    "UltimateLeagueTournamentView",
]
