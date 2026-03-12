from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import Field

from backend.app.academy.models import AcademySeasonStatus
from backend.app.common.enums.competition_type import CompetitionType
from backend.app.common.enums.fixture_window import FixtureWindow
from backend.app.common.enums.qualification_status import QualificationStatus
from backend.app.common.schemas.base import CommonSchema


class AcademyClubRequestView(CommonSchema):
    club_id: str = Field(min_length=1)
    club_name: str = Field(min_length=1)
    senior_buy_in_tier: int = Field(gt=0)
    carry_over_from_previous_season: bool = False


class AcademyResultRequestView(CommonSchema):
    fixture_id: str = Field(min_length=1)
    home_goals: int = Field(ge=0)
    away_goals: int = Field(ge=0)


class AcademyAwardsLeadersView(CommonSchema):
    top_scorer_club_id: str | None = Field(default=None, min_length=1)
    top_assist_club_id: str | None = Field(default=None, min_length=1)


class AcademySeasonRequestView(CommonSchema):
    season_id: str = Field(min_length=1)
    start_date: date
    clubs: tuple[AcademyClubRequestView, ...]
    results: tuple[AcademyResultRequestView, ...] = ()
    senior_world_super_cup_active: bool = False
    awards_leaders: AcademyAwardsLeadersView | None = None


class AcademyLedgerEventView(CommonSchema):
    event_key: str
    event_type: str
    aggregate_id: str
    payload: dict[str, str | int | bool]


class AcademyRegistrationView(CommonSchema):
    club_id: str
    club_name: str
    senior_buy_in_tier: int
    academy_buy_in: Decimal
    carry_over_from_previous_season: bool


class AcademyFixtureView(CommonSchema):
    fixture_id: str
    season_id: str
    round_number: int
    match_date: date
    window_number: int
    competition_type: CompetitionType
    shared_window: FixtureWindow
    home_club_id: str
    home_club_name: str
    away_club_id: str
    away_club_name: str
    stage_name: str
    is_cup_match: bool
    allow_penalties: bool
    extra_time_allowed: bool
    presentation_min_minutes: int
    presentation_max_minutes: int


class AcademyStandingView(CommonSchema):
    club_id: str
    club_name: str
    senior_buy_in_tier: int
    played: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int
    goal_difference: int
    points: int
    rank: int
    qualification_status: QualificationStatus
    auto_enter_next_season: bool


class AcademyQualificationEntryView(CommonSchema):
    club_id: str
    club_name: str
    league_rank: int
    senior_buy_in_tier: int
    status: QualificationStatus
    next_season_auto_entry: bool


class AcademyQualificationPlanView(CommonSchema):
    entries: tuple[AcademyQualificationEntryView, ...]
    direct_qualifiers: tuple[AcademyQualificationEntryView, ...]
    playoff_qualifiers: tuple[AcademyQualificationEntryView, ...]
    eliminated_clubs: tuple[AcademyQualificationEntryView, ...]


class AcademyLeaguePhaseRowView(CommonSchema):
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


class AcademyKnockoutTieView(CommonSchema):
    tie_id: str
    stage_name: str
    home_club_id: str
    home_club_name: str
    away_club_id: str
    away_club_name: str
    winner_club_id: str
    winner_club_name: str
    is_cup_match: bool
    allow_penalties: bool
    extra_time_allowed: bool
    presentation_min_minutes: int
    presentation_max_minutes: int


class AcademyChampionsLeagueFlowView(CommonSchema):
    qualification: AcademyQualificationPlanView
    playoff_ties: tuple[AcademyKnockoutTieView, ...]
    league_phase_table: tuple[AcademyLeaguePhaseRowView, ...]
    quarterfinals: tuple[AcademyKnockoutTieView, ...]
    semifinals: tuple[AcademyKnockoutTieView, ...]
    final: AcademyKnockoutTieView
    champion_club_id: str
    champion_club_name: str


class AcademyAwardAllocationView(CommonSchema):
    award_code: str
    club_id: str | None
    club_name: str | None
    amount: Decimal


class AcademyAwardsPreviewView(CommonSchema):
    total_pool: Decimal
    league_winner_share: Decimal
    top_scorer_share: Decimal
    top_assist_share: Decimal
    champions_league_fund_share: Decimal
    allocations: tuple[AcademyAwardAllocationView, ...]


class AcademyRegistrationResponseView(CommonSchema):
    season_id: str
    registrations: tuple[AcademyRegistrationView, ...]
    ledger_events: tuple[AcademyLedgerEventView, ...]


class AcademyFixturesResponseView(CommonSchema):
    season_id: str
    fixtures: tuple[AcademyFixtureView, ...]
    ledger_events: tuple[AcademyLedgerEventView, ...]


class AcademyStandingsResponseView(CommonSchema):
    season_id: str
    status: AcademySeasonStatus
    completed_fixture_count: int
    standings: tuple[AcademyStandingView, ...]


class AcademyQualificationResponseView(CommonSchema):
    season_id: str
    status: AcademySeasonStatus
    competition: AcademyChampionsLeagueFlowView


class AcademyAwardsResponseView(CommonSchema):
    season_id: str
    awards: AcademyAwardsPreviewView


class AcademySeasonSummaryView(CommonSchema):
    season_id: str
    status: AcademySeasonStatus
    start_date: date
    end_date: date
    active_during_senior_world_super_cup: bool
    registrations: tuple[AcademyRegistrationView, ...]
    fixtures: tuple[AcademyFixtureView, ...]
    completed_fixture_count: int
    standings: tuple[AcademyStandingView, ...]
    qualification: AcademyQualificationPlanView
    champions_league: AcademyChampionsLeagueFlowView
    awards: AcademyAwardsPreviewView
    rollover_clubs: tuple[AcademyRegistrationView, ...]
    champion_club_id: str
    champion_club_name: str
    ledger_events: tuple[AcademyLedgerEventView, ...]
