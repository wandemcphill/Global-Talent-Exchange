from __future__ import annotations

from datetime import date, datetime

from pydantic import Field, model_validator

from backend.app.common.enums.competition_type import CompetitionType
from backend.app.common.enums.fixture_window import FixtureWindow
from backend.app.common.enums.match_status import MatchStatus
from backend.app.common.enums.replay_visibility import ReplayVisibility

from .base import CommonSchema


class CompetitionReference(CommonSchema):
    competition_id: str = Field(min_length=1)
    competition_type: CompetitionType
    season_id: str | None = None


class FixtureWindowSlot(CommonSchema):
    match_date: date
    window: FixtureWindow
    slot_sequence: int = Field(default=1, ge=1)


class CompetitionWindowAssignment(CommonSchema):
    competition_id: str = Field(min_length=1)
    competition_type: CompetitionType
    match_date: date
    windows: tuple[FixtureWindow, ...]
    slot_sequences: tuple[int, ...] = ()
    exclusive: bool = False
    label: str | None = None

    @model_validator(mode="after")
    def validate_windows(self) -> "CompetitionWindowAssignment":
        if not self.windows:
            raise ValueError("At least one fixture window must be assigned.")
        if len(set(self.windows)) != len(self.windows):
            raise ValueError("Assigned fixture windows must be unique.")
        if self.slot_sequences:
            if any(sequence < 1 for sequence in self.slot_sequences):
                raise ValueError("Assigned slot sequences must be positive integers.")
            if len(set(self.slot_sequences)) != len(self.slot_sequences):
                raise ValueError("Assigned slot sequences must be unique.")
            if len(self.windows) != 1:
                raise ValueError("Slot sequences can only be assigned to a single shared fixture window.")
            if not self.windows[0].supports_slot_sequence:
                raise ValueError("Only open fixture windows support slot sequences.")
        return self


class ExclusiveWindowReservation(CommonSchema):
    reservation_code: str = Field(min_length=1)
    competition_id: str = Field(min_length=1)
    competition_type: CompetitionType
    match_date: date
    windows: tuple[FixtureWindow, ...]
    reason: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_windows(self) -> "ExclusiveWindowReservation":
        if not self.windows:
            raise ValueError("Exclusive reservations require at least one fixture window.")
        if len(set(self.windows)) != len(self.windows):
            raise ValueError("Exclusive reservation windows must be unique.")
        return self


class CalendarConflict(CommonSchema):
    conflict_code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    match_date: date
    window: FixtureWindow
    slot_sequence: int | None = Field(default=None, ge=1)
    competition_id: str | None = None
    conflicting_competition_id: str | None = None
    club_id: str | None = None
    fixture_id: str | None = None
    reservation_code: str | None = None


class LeagueFixtureRequest(CommonSchema):
    fixture_id: str = Field(min_length=1)
    competition_id: str = Field(min_length=1)
    competition_type: CompetitionType = CompetitionType.LEAGUE
    round_number: int = Field(ge=1)
    home_club_id: str = Field(min_length=1)
    away_club_id: str = Field(min_length=1)
    stage_name: str | None = None
    replay_visibility: ReplayVisibility = ReplayVisibility.COMPETITION
    is_cup_match: bool = False

    @model_validator(mode="after")
    def validate_clubs(self) -> "LeagueFixtureRequest":
        if self.home_club_id == self.away_club_id:
            raise ValueError("A fixture cannot schedule the same club against itself.")
        return self


class ScheduledFixture(CommonSchema):
    fixture_id: str = Field(min_length=1)
    competition_id: str = Field(min_length=1)
    competition_type: CompetitionType
    round_number: int = Field(ge=1)
    home_club_id: str = Field(min_length=1)
    away_club_id: str = Field(min_length=1)
    match_date: date
    window: FixtureWindow
    slot_sequence: int = Field(default=1, ge=1)
    stage_name: str | None = None
    replay_visibility: ReplayVisibility = ReplayVisibility.COMPETITION
    status: MatchStatus = MatchStatus.SCHEDULED
    is_cup_match: bool = False
    allow_penalties: bool = False

    @model_validator(mode="after")
    def validate_scheduled_fixture(self) -> "ScheduledFixture":
        if self.home_club_id == self.away_club_id:
            raise ValueError("A scheduled fixture cannot contain the same club twice.")
        if self.allow_penalties and not self.is_cup_match:
            raise ValueError("Penalty shootouts are only allowed in cup matches.")
        return self


class CompetitionScheduleRequest(CommonSchema):
    competition_id: str = Field(min_length=1)
    competition_type: CompetitionType
    requested_dates: tuple[date, ...]
    required_windows: int = Field(default=1, ge=1)
    preferred_windows: tuple[FixtureWindow, ...] = ()
    priority: int = Field(default=100, ge=0)
    requires_exclusive_windows: bool = False

    @model_validator(mode="after")
    def validate_dates(self) -> "CompetitionScheduleRequest":
        if not self.requested_dates:
            raise ValueError("At least one requested date is required.")
        if len(set(self.requested_dates)) != len(self.requested_dates):
            raise ValueError("Requested schedule dates must be unique.")
        return self


class CompetitionPauseEntry(CommonSchema):
    competition_id: str = Field(min_length=1)
    competition_type: CompetitionType
    paused_dates: tuple[date, ...]
    reason: str = Field(min_length=1)


class CompetitionSchedulePlan(CommonSchema):
    assignments: tuple[CompetitionWindowAssignment, ...] = ()
    reservations: tuple[ExclusiveWindowReservation, ...] = ()
    paused_competitions: tuple[CompetitionPauseEntry, ...] = ()


class CompetitionDispatchRequest(CommonSchema):
    fixture: ScheduledFixture
    is_final: bool = False
    season_id: str | None = None
    competition_name: str | None = None
    stage_name: str | None = None
    scheduled_kickoff_at: datetime | None = None
    simulation_seed: int | None = Field(default=None, ge=0)
    home_club_name: str | None = None
    away_club_name: str | None = None
    home_strength_rating: int | None = Field(default=None, ge=1, le=100)
    away_strength_rating: int | None = Field(default=None, ge=1, le=100)
    home_user_id: str | None = None
    away_user_id: str | None = None


class CompetitionEngineBatch(CommonSchema):
    competition_id: str = Field(min_length=1)
    competition_type: CompetitionType
    schedule_plan: CompetitionSchedulePlan
    fixtures: tuple[ScheduledFixture, ...] = ()
    dispatch_requests: tuple[CompetitionDispatchRequest, ...] = ()
