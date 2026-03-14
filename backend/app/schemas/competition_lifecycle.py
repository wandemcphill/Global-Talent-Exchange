from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import Field

from backend.app.common.enums.fixture_window import FixtureWindow
from backend.app.common.enums.match_status import MatchStatus
from backend.app.common.schemas.base import CommonSchema
from backend.app.common.schemas.competition import CompetitionSchedulePlan


class CompetitionStructureRequest(CommonSchema):
    group_stage_enabled: bool | None = None
    group_count: int | None = Field(default=None, ge=1, le=64)
    group_size: int | None = Field(default=None, ge=2, le=64)
    group_advance_count: int | None = Field(default=None, ge=1, le=32)
    knockout_bracket_size: int | None = Field(default=None, ge=2, le=64)


class CompetitionVisibilityRuleRequest(CommonSchema):
    rule_type: str = Field(min_length=2, max_length=32)
    rule_payload: dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=100, ge=0)
    enabled: bool = True


class CompetitionSeedRequest(CommonSchema):
    seed_method: str | None = Field(default=None, max_length=24)
    manual_seed_order: tuple[str, ...] | None = None


class CompetitionSchedulePreviewRequest(CommonSchema):
    start_date: date | None = None
    requested_dates: tuple[date, ...] | None = None
    priority: int = Field(default=100, ge=0)
    requires_exclusive_windows: bool = False
    alignment_group: str | None = Field(default=None, max_length=64)


class CompetitionSchedulePreviewResponse(CommonSchema):
    competition_id: str
    round_count: int
    match_count: int
    requested_dates: tuple[date, ...]
    assigned_dates: tuple[date, ...]
    schedule_plan: CompetitionSchedulePlan
    warnings: tuple[str, ...] = ()


class CompetitionScheduleJobRequest(CommonSchema):
    start_date: date | None = None
    requested_dates: tuple[date, ...] | None = None
    priority: int = Field(default=100, ge=0)
    requires_exclusive_windows: bool = False
    alignment_group: str | None = Field(default=None, max_length=64)
    preview_only: bool = False
    created_by_user_id: str | None = Field(default=None, max_length=36)


class CompetitionScheduleJobView(CommonSchema):
    id: str
    competition_id: str
    status: str
    requested_dates: tuple[date, ...]
    assigned_dates: tuple[date, ...]
    created_at: datetime
    error_message: str | None = None


class CompetitionRoundView(CommonSchema):
    id: str
    competition_id: str
    round_number: int
    stage: str
    group_key: str | None = None
    name: str | None = None
    status: str
    starts_at: datetime | None = None
    ends_at: datetime | None = None


class CompetitionMatchView(CommonSchema):
    id: str
    competition_id: str
    round_id: str
    round_number: int
    stage: str
    group_key: str | None = None
    home_club_id: str
    away_club_id: str
    scheduled_at: datetime | None = None
    match_date: date | None = None
    window: FixtureWindow | None = None
    slot_sequence: int = Field(default=1, ge=1)
    status: MatchStatus
    home_score: int = Field(default=0, ge=0)
    away_score: int = Field(default=0, ge=0)
    winner_club_id: str | None = None
    decided_by_penalties: bool = False
    requires_winner: bool = False


class CompetitionMatchEventView(CommonSchema):
    id: str
    match_id: str
    event_type: str
    minute: int | None = None
    added_time: int | None = None
    club_id: str | None = None
    player_id: str | None = None
    secondary_player_id: str | None = None
    card_type: str | None = None
    highlight: bool = False
    created_at: datetime
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class CompetitionMatchEventRequest(CommonSchema):
    event_type: str = Field(min_length=2, max_length=32)
    minute: int | None = Field(default=None, ge=0, le=130)
    added_time: int | None = Field(default=None, ge=0, le=20)
    club_id: str | None = Field(default=None, max_length=36)
    player_id: str | None = Field(default=None, max_length=36)
    secondary_player_id: str | None = Field(default=None, max_length=36)
    card_type: str | None = Field(default=None, max_length=16)
    highlight: bool = False
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class CompetitionMatchResultRequest(CommonSchema):
    home_score: int = Field(ge=0)
    away_score: int = Field(ge=0)
    decided_by_penalties: bool = False
    winner_club_id: str | None = Field(default=None, max_length=36)


class CompetitionStandingView(CommonSchema):
    club_id: str
    seed: int | None = None
    group_key: str | None = None
    played: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int
    goal_diff: int
    points: int
    rank: int


class CompetitionAdvanceRequest(CommonSchema):
    force: bool = False


class CompetitionFinalizeRequest(CommonSchema):
    settle: bool = True


class CompetitionInviteAcceptRequest(CommonSchema):
    club_id: str = Field(min_length=1, max_length=36)
    invite_code: str | None = Field(default=None, min_length=4, max_length=32)
    invite_id: str | None = Field(default=None, max_length=36)
    user_id: str | None = Field(default=None, max_length=36)
