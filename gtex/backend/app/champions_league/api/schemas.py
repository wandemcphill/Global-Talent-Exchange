from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.champions_league.models.domain import (
    AdvancementStatus,
    MatchStage,
    QualificationStatus,
)


class ClubCandidateRequest(BaseModel):
    club_id: str
    club_name: str
    region: str
    tier: str
    ranking_points: int = Field(ge=0)
    domestic_rank: int = Field(ge=1)


class ClubSeedRequest(BaseModel):
    club_id: str
    club_name: str
    seed: int = Field(ge=1)
    region: str | None = None
    tier: str | None = None


class LeagueMatchResultRequest(BaseModel):
    match_id: str
    home_club_id: str
    away_club_id: str
    home_goals: int = Field(ge=0)
    away_goals: int = Field(ge=0)


class LeagueStandingRowRequest(BaseModel):
    club_id: str
    club_name: str
    seed: int = Field(ge=1)
    played: int = Field(ge=0)
    wins: int = Field(ge=0)
    draws: int = Field(ge=0)
    losses: int = Field(ge=0)
    goals_for: int = Field(ge=0)
    goals_against: int = Field(ge=0)
    goal_difference: int
    points: int = Field(ge=0)
    rank: int = Field(ge=1)
    advancement_status: AdvancementStatus = AdvancementStatus.ELIMINATED


class QualificationMapRequest(BaseModel):
    clubs: list[ClubCandidateRequest]


class PlayoffBracketRequest(BaseModel):
    clubs: list[ClubCandidateRequest]
    winner_overrides: dict[str, str] = Field(default_factory=dict)


class LeaguePhaseTableRequest(BaseModel):
    clubs: list[ClubSeedRequest]
    matches: list[LeagueMatchResultRequest] = Field(default_factory=list)


class KnockoutBracketRequest(BaseModel):
    standings: list[LeagueStandingRowRequest]
    knockout_playoff_winners: dict[str, str] = Field(default_factory=dict)
    round_of_16_winners: dict[str, str] = Field(default_factory=dict)
    quarterfinal_winners: dict[str, str] = Field(default_factory=dict)
    semifinal_winners: dict[str, str] = Field(default_factory=dict)
    final_winner: dict[str, str] = Field(default_factory=dict)


class PrizePoolPreviewRequest(BaseModel):
    season_id: str
    league_leftover_allocation: Decimal = Field(ge=Decimal("0"))
    champion_club_id: str | None = None
    champion_club_name: str | None = None
    currency: str = "credit"


class ClubSeedView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    club_id: str
    club_name: str
    seed: int
    region: str | None = None
    tier: str | None = None


class QualifiedClubView(ClubSeedView):
    status: QualificationStatus
    display_color: str


class TierAllocationView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    stage: str
    tier: str
    slot_count: int


class QualificationRegionSummaryView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    region: str
    direct_count: int
    playoff_count: int
    eliminated_count: int


class QualificationMapView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    entries: list[QualifiedClubView]
    direct_qualifiers: list[QualifiedClubView]
    playoff_qualifiers: list[QualifiedClubView]
    tier_allocations: list[TierAllocationView]
    region_summaries: list[QualificationRegionSummaryView]


class KnockoutTieView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tie_id: str
    stage: MatchStage
    home_club: ClubSeedView
    away_club: ClubSeedView
    winner: ClubSeedView
    penalties_if_tied: bool
    extra_time_allowed: bool
    presentation_max_minutes: int


class PlayoffBracketView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    qualification: QualificationMapView
    ties: list[KnockoutTieView]
    advancing_clubs: list[ClubSeedView]


class LeagueStandingRowView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    club_id: str
    club_name: str
    seed: int
    played: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int
    goal_difference: int
    points: int
    rank: int
    advancement_status: AdvancementStatus


class LeaguePhaseTableView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rows: list[LeagueStandingRowView]
    is_complete: bool


class KnockoutBracketView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    knockout_playoff: list[KnockoutTieView]
    round_of_16: list[KnockoutTieView]
    quarterfinals: list[KnockoutTieView]
    semifinals: list[KnockoutTieView]
    final: KnockoutTieView
    champion: ClubSeedView


class SettlementEventPlanView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_key: str
    event_type: str
    aggregate_id: str
    amount: Decimal
    currency: str
    payload: dict[str, str]


class PrizeSettlementPreviewView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    season_id: str
    champion_club_id: str | None
    champion_club_name: str | None
    league_leftover_allocation: Decimal
    funded_pool: Decimal
    champion_share: Decimal
    platform_share: Decimal
    currency: str
    events: list[SettlementEventPlanView]
