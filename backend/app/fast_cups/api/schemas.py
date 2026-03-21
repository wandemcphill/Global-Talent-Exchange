from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.common.enums.competition_type import CompetitionType
from app.common.enums.fixture_window import FixtureWindow
from app.fast_cups.models.domain import FastCupDivision, FastCupStage, FastCupStatus


class ClubCompetitionWindowRequest(BaseModel):
    club_id: str
    competition_id: str
    competition_type: CompetitionType
    starts_at: datetime
    ends_at: datetime
    window: FixtureWindow | None = None


class JoinFastCupRequest(BaseModel):
    club_id: str
    club_name: str
    division: FastCupDivision
    rating: int = Field(ge=0)
    registered_at: datetime | None = None
    existing_windows: list[ClubCompetitionWindowRequest] = Field(default_factory=list)


class FastCupEntrantView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    club_id: str
    club_name: str
    division: FastCupDivision
    rating: int
    registered_at: datetime


class FastCupSlotView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    registration_opens_at: datetime
    registration_closes_at: datetime
    kickoff_at: datetime
    expected_completion_at: datetime
    window: FixtureWindow


class FastCupPreviewView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    cup_id: str
    title: str
    division: FastCupDivision
    size: int
    buy_in: Decimal
    currency: str
    status: FastCupStatus
    slot: FastCupSlotView
    entrants: list[FastCupEntrantView]


class UpcomingFastCupsView(BaseModel):
    cups: list[FastCupPreviewView]


class JoinFastCupResponse(BaseModel):
    cup: FastCupPreviewView
    entrants_registered: int
    slots_remaining: int


class FastCupMatchView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tie_id: str
    stage: FastCupStage
    round_number: int
    slot_number: int
    scheduled_at: datetime
    presentation_min_minutes: int
    presentation_max_minutes: int
    home: FastCupEntrantView | None = None
    away: FastCupEntrantView | None = None
    winner: FastCupEntrantView | None = None
    home_goals: int | None = None
    away_goals: int | None = None
    home_penalties: int | None = None
    away_penalties: int | None = None
    decided_by_penalties: bool
    penalties_if_tied: bool
    extra_time_allowed: bool
    key_moments: tuple[str, ...]
    home_source_tie_id: str | None = None
    away_source_tie_id: str | None = None


class FastCupRoundView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    stage: FastCupStage
    round_number: int
    scheduled_at: datetime
    presentation_max_minutes: int
    matches: list[FastCupMatchView]


class FastCupBracketView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rounds: list[FastCupRoundView]
    total_rounds: int
    total_matches: int
    expected_duration_minutes: int
    simulated: bool
    champion: FastCupEntrantView | None = None
    runner_up: FastCupEntrantView | None = None
    semifinalists: list[FastCupEntrantView] = Field(default_factory=list)


class RegistrationCountdownView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    cup_id: str
    status: FastCupStatus
    seconds_until_registration_close: int
    seconds_until_kickoff: int
    seconds_until_completion: int
    entrants_registered: int
    slots_remaining: int


class CupRewardView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    club_id: str
    club_name: str
    finish: str
    amount: Decimal
    currency: str


class PayoutLedgerEventView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_key: str
    event_type: str
    aggregate_id: str
    amount: Decimal
    currency: str
    payload: dict[str, str]


class FastCupResultSummaryView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    cup_id: str
    division: FastCupDivision
    size: int
    champion: FastCupEntrantView
    runner_up: FastCupEntrantView
    semifinalists: list[FastCupEntrantView]
    total_rounds: int
    total_matches: int
    expected_duration_minutes: int
    concluded_at: datetime
    prize_pool: Decimal
    reward_pool: Decimal
    platform_fee: Decimal
    currency: str
    penalty_shootouts: int
    rewards: list[CupRewardView]
    events: list[PayoutLedgerEventView]
