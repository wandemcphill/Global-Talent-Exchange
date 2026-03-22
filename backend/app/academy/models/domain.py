from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import StrEnum

from app.common.enums.competition_type import CompetitionType
from app.common.enums.fixture_window import FixtureWindow
from app.common.enums.qualification_status import QualificationStatus


class AcademyValidationError(ValueError):
    """Raised when an academy competition request violates domain rules."""


class AcademySeasonStatus(StrEnum):
    REGISTRATION_OPEN = "registration_open"
    FIXTURES_PUBLISHED = "fixtures_published"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


@dataclass(slots=True, frozen=True)
class AcademyClubRegistrationRequest:
    club_id: str
    club_name: str
    senior_buy_in_tier: int
    carry_over_from_previous_season: bool = False


@dataclass(slots=True, frozen=True)
class AcademyClubRegistration:
    club_id: str
    club_name: str
    senior_buy_in_tier: int
    academy_buy_in: Decimal
    carry_over_from_previous_season: bool = False


@dataclass(slots=True, frozen=True)
class AcademyMatchResult:
    fixture_id: str
    home_goals: int
    away_goals: int


@dataclass(slots=True, frozen=True)
class AcademyAwardsLeaders:
    top_scorer_club_id: str | None = None
    top_assist_club_id: str | None = None


@dataclass(slots=True, frozen=True)
class AcademySeasonRequest:
    season_id: str
    start_date: date
    clubs: tuple[AcademyClubRegistrationRequest, ...]
    results: tuple[AcademyMatchResult, ...] = ()
    senior_world_super_cup_active: bool = False
    awards_leaders: AcademyAwardsLeaders | None = None


@dataclass(slots=True, frozen=True)
class AcademyLedgerEvent:
    event_key: str
    event_type: str
    aggregate_id: str
    payload: dict[str, str | int | bool]


@dataclass(slots=True, frozen=True)
class AcademyFixture:
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
    is_cup_match: bool = False
    allow_penalties: bool = False
    extra_time_allowed: bool = False
    presentation_min_minutes: int = 0
    presentation_max_minutes: int = 0


@dataclass(slots=True)
class AcademyStandingRow:
    club_id: str
    club_name: str
    senior_buy_in_tier: int
    played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0
    goal_difference: int = 0
    points: int = 0
    rank: int = 0
    qualification_status: QualificationStatus = QualificationStatus.PENDING
    auto_enter_next_season: bool = False


@dataclass(slots=True, frozen=True)
class AcademyQualificationEntry:
    club_id: str
    club_name: str
    league_rank: int
    senior_buy_in_tier: int
    status: QualificationStatus
    next_season_auto_entry: bool = False


@dataclass(slots=True, frozen=True)
class AcademyQualificationPlan:
    entries: tuple[AcademyQualificationEntry, ...]
    direct_qualifiers: tuple[AcademyQualificationEntry, ...]
    playoff_qualifiers: tuple[AcademyQualificationEntry, ...]
    eliminated_clubs: tuple[AcademyQualificationEntry, ...]


@dataclass(slots=True)
class AcademyLeaguePhaseRow:
    club_id: str
    club_name: str
    seed: int
    played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0
    goal_difference: int = 0
    points: int = 0
    rank: int = 0


@dataclass(slots=True, frozen=True)
class AcademyKnockoutTie:
    tie_id: str
    stage_name: str
    home_club_id: str
    home_club_name: str
    away_club_id: str
    away_club_name: str
    winner_club_id: str
    winner_club_name: str
    is_cup_match: bool = True
    allow_penalties: bool = True
    extra_time_allowed: bool = False
    presentation_min_minutes: int = 0
    presentation_max_minutes: int = 0


@dataclass(slots=True, frozen=True)
class AcademyChampionsLeagueFlow:
    qualification: AcademyQualificationPlan
    playoff_ties: tuple[AcademyKnockoutTie, ...]
    league_phase_table: tuple[AcademyLeaguePhaseRow, ...]
    quarterfinals: tuple[AcademyKnockoutTie, ...]
    semifinals: tuple[AcademyKnockoutTie, ...]
    final: AcademyKnockoutTie
    champion_club_id: str
    champion_club_name: str


@dataclass(slots=True, frozen=True)
class AcademyAwardAllocation:
    award_code: str
    club_id: str | None
    club_name: str | None
    amount: Decimal


@dataclass(slots=True, frozen=True)
class AcademyAwardsPreview:
    total_pool: Decimal
    league_winner_share: Decimal
    top_scorer_share: Decimal
    top_assist_share: Decimal
    champions_league_fund_share: Decimal
    allocations: tuple[AcademyAwardAllocation, ...] = field(default_factory=tuple)


@dataclass(slots=True, frozen=True)
class AcademySeasonProjection:
    season_id: str
    status: AcademySeasonStatus
    start_date: date
    end_date: date
    active_during_senior_world_super_cup: bool
    registrations: tuple[AcademyClubRegistration, ...]
    fixtures: tuple[AcademyFixture, ...]
    completed_fixture_count: int
    standings: tuple[AcademyStandingRow, ...]
    qualification: AcademyQualificationPlan
    champions_league: AcademyChampionsLeagueFlow
    awards: AcademyAwardsPreview
    rollover_clubs: tuple[AcademyClubRegistration, ...]
    champion_club_id: str
    champion_club_name: str
    ledger_events: tuple[AcademyLedgerEvent, ...]
