from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from backend.app.common.enums.competition_type import CompetitionType
from backend.app.common.enums.replay_visibility import ReplayVisibility
from backend.app.common.schemas.base import CommonSchema
from backend.app.match_engine.schemas import MatchVisualIdentityView
from backend.app.competition_engine.queue_contracts import SUPPORTED_MATCH_MOMENTS
from backend.app.config.competition_constants import (
    FINAL_PRESENTATION_MAX_MINUTES,
    MATCH_PRESENTATION_MAX_MINUTES,
    MATCH_PRESENTATION_MIN_MINUTES,
)


class ReplayClubView(CommonSchema):
    club_id: str = Field(min_length=1)
    club_name: str = Field(min_length=1)


class ReplayScoreline(CommonSchema):
    home_goals: int = Field(ge=0)
    away_goals: int = Field(ge=0)


class ReplayMomentView(CommonSchema):
    event_id: str = Field(min_length=1)
    minute: int = Field(ge=0)
    event_type: str = Field(min_length=1)
    club_id: str | None = None
    club_name: str | None = None
    player_id: str | None = None
    player_name: str | None = None
    secondary_player_id: str | None = None
    secondary_player_name: str | None = None
    description: str | None = None
    home_score: int = Field(ge=0)
    away_score: int = Field(ge=0)
    is_penalty: bool = False

    @model_validator(mode="after")
    def validate_event_type(self) -> "ReplayMomentView":
        if self.event_type not in SUPPORTED_MATCH_MOMENTS:
            raise ValueError(f"Unsupported replay moment type: {self.event_type}")
        return self


class CompetitionContextView(CommonSchema):
    competition_id: str = Field(min_length=1)
    competition_type: CompetitionType
    competition_name: str = Field(min_length=1)
    season_id: str | None = None
    stage_name: str | None = None
    round_number: int | None = Field(default=None, ge=1)
    is_final: bool = False
    is_cup_match: bool = False
    competition_allows_public: bool = False
    allow_early_round_public: bool = False
    presentation_duration_minutes: int | None = None
    replay_visibility: ReplayVisibility = ReplayVisibility.COMPETITION
    resolved_visibility: ReplayVisibility = ReplayVisibility.COMPETITION
    public_metadata_visible: bool = False
    featured_public: bool = False

    @model_validator(mode="after")
    def validate_presentation_window(self) -> "CompetitionContextView":
        max_allowed = FINAL_PRESENTATION_MAX_MINUTES if self.is_final else MATCH_PRESENTATION_MAX_MINUTES
        if self.presentation_duration_minutes is None:
            self.presentation_duration_minutes = max_allowed
        if self.presentation_duration_minutes < MATCH_PRESENTATION_MIN_MINUTES:
            raise ValueError("Replay presentation duration falls below the supported minimum.")
        if self.presentation_duration_minutes > max_allowed:
            raise ValueError("Replay presentation duration exceeds the supported maximum.")
        return self


class ReplayArchiveIngest(CommonSchema):
    replay_id: str | None = None
    fixture_id: str = Field(min_length=1)
    scheduled_start: datetime
    started_at: datetime | None = None
    final_whistle_at: datetime | None = None
    live: bool = False
    home_club: ReplayClubView
    away_club: ReplayClubView
    scoreline: ReplayScoreline
    visual_identity: MatchVisualIdentityView | None = None
    timeline: tuple[ReplayMomentView, ...]
    participant_user_ids: tuple[str, ...] = ()
    competition_context: CompetitionContextView

    @model_validator(mode="after")
    def validate_timeline(self) -> "ReplayArchiveIngest":
        if not self.timeline:
            raise ValueError("Replay archive ingestion requires a timeline.")
        last_minute = -1
        for event in self.timeline:
            if event.minute < last_minute:
                raise ValueError("Replay timeline must be ordered by minute.")
            last_minute = event.minute
        if (
            any(event.event_type == "penalties" or event.is_penalty for event in self.timeline)
            and not self.competition_context.is_cup_match
        ):
            raise ValueError("Penalty replay moments are only valid for cup matches.")
        return self


class ReplayArchiveRecord(CommonSchema):
    replay_id: str = Field(min_length=1)
    version: int = Field(ge=1)
    fixture_id: str = Field(min_length=1)
    created_at: datetime
    updated_at: datetime
    scheduled_start: datetime
    started_at: datetime | None = None
    final_whistle_at: datetime | None = None
    live: bool = False
    home_club: ReplayClubView
    away_club: ReplayClubView
    scoreline: ReplayScoreline
    visual_identity: MatchVisualIdentityView | None = None
    timeline: tuple[ReplayMomentView, ...]
    scorers: tuple[ReplayMomentView, ...] = ()
    assisters: tuple[ReplayMomentView, ...] = ()
    cards: tuple[ReplayMomentView, ...] = ()
    injuries: tuple[ReplayMomentView, ...] = ()
    substitutions: tuple[ReplayMomentView, ...] = ()
    participant_user_ids: tuple[str, ...] = ()
    competition_context: CompetitionContextView


class ReplaySummaryView(CommonSchema):
    replay_id: str = Field(min_length=1)
    fixture_id: str = Field(min_length=1)
    scheduled_start: datetime
    started_at: datetime | None = None
    final_whistle_at: datetime | None = None
    live: bool = False
    home_club: ReplayClubView
    away_club: ReplayClubView
    scoreline: ReplayScoreline
    competition_context: CompetitionContextView


class CountdownUpdatePayload(CommonSchema):
    fixture_id: str = Field(min_length=1)
    replay_id: str | None = None
    scheduled_start: datetime
    home_club: ReplayClubView
    away_club: ReplayClubView
    competition_context: CompetitionContextView
    live: bool = False
    completed: bool = False
    last_notification_key: str | None = None
    notification_sent_at: datetime | None = None


class CountdownView(CommonSchema):
    fixture_id: str = Field(min_length=1)
    replay_id: str | None = None
    scheduled_start: datetime
    state: Literal["scheduled", "live", "complete"]
    seconds_until_start: int
    home_club: ReplayClubView
    away_club: ReplayClubView
    competition_context: CompetitionContextView
    last_notification_key: str | None = None
    next_notification_key: str | None = None
    notification_sent_at: datetime | None = None
