from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import Field, model_validator

from app.common.schemas.base import CommonSchema
from app.match_engine.schemas import MatchReplayPayloadView, MatchTeamInput
from app.models.competitive_integrity import (
    CompetitiveMatchCompetitionType,
    CompetitiveMatchStatus,
    CompetitiveNotificationChannel,
    CompetitiveNotificationStatus,
    ManagerType,
    MatchControllerType,
)


class ManagerRuleInput(CommonSchema):
    minute: int = Field(ge=0, le=120)
    condition: str | None = Field(default=None, min_length=2, max_length=64)
    action: str | dict[str, Any]


class ManagerInstructionPayload(CommonSchema):
    formation: str | None = Field(default=None, min_length=5, max_length=15)
    style: str | None = Field(default=None, min_length=3, max_length=32)
    pressing: str | int | None = None
    tempo: str | int | None = None
    rules: list[ManagerRuleInput] = Field(default_factory=list)


class TacticalProfilePayload(CommonSchema):
    style: str | None = Field(default=None, min_length=3, max_length=32)
    pressing: str | int | None = None
    tempo: str | int | None = None
    mentality: str | None = Field(default=None, min_length=3, max_length=32)
    notes: str | None = Field(default=None, max_length=255)


class ManagerCreateRequest(CommonSchema):
    type: ManagerType
    appointed_user_id: str | None = Field(default=None, min_length=1)
    instructions: ManagerInstructionPayload = Field(default_factory=ManagerInstructionPayload)
    tactical_profile: TacticalProfilePayload = Field(default_factory=TacticalProfilePayload)

    @model_validator(mode="after")
    def validate_manager(self) -> "ManagerCreateRequest":
        if self.type is ManagerType.USER:
            self.appointed_user_id = None
        elif not self.appointed_user_id:
            raise ValueError("appointed_user_id is required for a real manager.")
        return self


class ManagerUpdateInstructionsRequest(CommonSchema):
    instructions: ManagerInstructionPayload
    tactical_profile: TacticalProfilePayload | None = None


class ManagerView(CommonSchema):
    id: str
    user_id: str
    type: ManagerType
    appointed_user_id: str | None = None
    instructions: dict[str, Any]
    tactical_profile: dict[str, Any]
    reputation_score: float
    created_at: datetime


class ManagerCandidateView(CommonSchema):
    user_id: str
    username: str
    display_name: str
    average_reputation: float
    prior_appointments: int


class CompetitiveMatchCreateRequest(CommonSchema):
    competition_type: CompetitiveMatchCompetitionType
    home_user_id: str = Field(min_length=1)
    away_user_id: str = Field(min_length=1)
    home_manager_id: str | None = None
    away_manager_id: str | None = None
    is_user_online_home: bool = False
    is_user_online_away: bool = False
    locked_lineup_home: MatchTeamInput
    locked_lineup_away: MatchTeamInput
    kickoff_at: datetime | None = None
    ai_detected: bool = False
    automation_detected: bool = False

    @model_validator(mode="after")
    def validate_users(self) -> "CompetitiveMatchCreateRequest":
        if self.home_user_id == self.away_user_id:
            raise ValueError("home_user_id and away_user_id must differ.")
        return self


class CompetitiveMatchExecuteRequest(CommonSchema):
    is_user_online_home: bool | None = None
    is_user_online_away: bool | None = None
    simulation_seed: int | None = Field(default=None, ge=0)
    ai_detected: bool = False
    automation_detected: bool = False


class ControllerSummaryView(CommonSchema):
    home: MatchControllerType
    away: MatchControllerType


class MatchControlLogView(CommonSchema):
    side: str
    controller_type: MatchControllerType
    timestamp: datetime


class CompetitiveMatchView(CommonSchema):
    id: str
    competition_type: CompetitiveMatchCompetitionType
    home_user_id: str
    away_user_id: str
    home_manager_id: str | None = None
    away_manager_id: str | None = None
    fast_game_run_id: str | None = None
    is_user_online_home: bool
    is_user_online_away: bool
    kickoff_at: datetime | None = None
    status: CompetitiveMatchStatus
    result_payload: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class CompetitiveMatchExecutionView(CommonSchema):
    match: CompetitiveMatchView
    controllers: ControllerSummaryView
    control_logs: list[MatchControlLogView]
    replay: MatchReplayPayloadView | None = None


class FastGameRunStartRequest(CommonSchema):
    manager_id: str | None = None
    entry_fee_amount: Decimal = Field(default=Decimal("10.0000"), ge=Decimal("0.0000"))
    base_reward_amount: Decimal = Field(default=Decimal("25.0000"), ge=Decimal("0.0000"))
    base_rating: int = Field(default=1200, ge=0, le=5000)
    scaling_factor: int = Field(default=25, ge=1, le=500)
    ai_detected: bool = False
    automation_detected: bool = False


class FastGameRunView(CommonSchema):
    id: str
    user_id: str
    wins: int
    losses: int
    is_active: bool
    manager_locked_id: str | None = None
    entry_fee_amount: Decimal
    base_reward_amount: Decimal
    base_rating: int
    scaling_factor: int
    reward_amount_paid: Decimal
    started_at: datetime
    ended_at: datetime | None = None


class FastGamePlayRequest(CommonSchema):
    home_manager_id: str | None = None
    away_user_id: str = Field(min_length=1)
    away_manager_id: str | None = None
    is_user_online_home: bool = True
    is_user_online_away: bool = True
    locked_lineup_home: MatchTeamInput
    locked_lineup_away: MatchTeamInput
    kickoff_at: datetime | None = None
    simulation_seed: int | None = Field(default=None, ge=0)
    ai_detected: bool = False
    automation_detected: bool = False


class FastGameResultView(CommonSchema):
    run: FastGameRunView
    match: CompetitiveMatchExecutionView
    result: str
    reward_amount: Decimal
    max_reward_triggered: bool = False
    matchmaking_rating: int


class NotificationEventRequest(CommonSchema):
    user_id: str = Field(min_length=1)
    type: str = Field(min_length=3, max_length=64)
    payload: dict[str, Any] = Field(default_factory=dict)


class CompetitiveNotificationView(CommonSchema):
    id: str
    user_id: str
    type: str
    payload: dict[str, Any]
    status: CompetitiveNotificationStatus
    channel: CompetitiveNotificationChannel
    scheduled_for: datetime
    provider_message_id: str | None = None
    failure_reason: str | None = None
    sent_at: datetime | None = None
    created_at: datetime


class WorkerRunResultView(CommonSchema):
    executed_matches: int
    delivered_notifications: int
