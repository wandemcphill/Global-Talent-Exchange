from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from threading import RLock
from typing import Any, Literal, Protocol

from pydantic import Field, model_validator

from app.common.enums.competition_type import CompetitionType
from app.common.enums.fixture_window import FixtureWindow
from app.common.enums.match_status import MatchStatus
from app.common.enums.replay_visibility import ReplayVisibility
from app.common.schemas.base import CommonSchema
from app.config.competition_constants import (
    FINAL_PRESENTATION_MAX_MINUTES,
    MATCH_PRESENTATION_MAX_MINUTES,
    MATCH_PRESENTATION_MIN_MINUTES,
)
from app.core.events import DomainEvent, EventPublisher, InMemoryEventPublisher, utcnow

SUPPORTED_MATCH_MOMENTS = (
    "goals",
    "assists",
    "missed_chances",
    "yellow_cards",
    "red_cards",
    "substitutions",
    "injuries",
    "penalties",
)
DEFAULT_MATCH_MOMENTS = tuple(
    moment
    for moment in SUPPORTED_MATCH_MOMENTS
    if moment != "penalties"
)


class MatchSimulationJob(CommonSchema):
    queue_name: Literal["match_simulation"] = "match_simulation"
    job_name: Literal["match_simulation"] = "match_simulation"
    fixture_id: str = Field(min_length=1)
    competition_id: str = Field(min_length=1)
    competition_type: CompetitionType
    match_date: date
    window: FixtureWindow
    slot_sequence: int = Field(default=1, ge=1)
    season_id: str | None = None
    competition_name: str | None = None
    stage_name: str | None = None
    round_number: int = Field(default=1, ge=1)
    scheduled_kickoff_at: datetime | None = None
    simulation_seed: int | None = Field(default=None, ge=0)
    home_club_id: str | None = None
    home_club_name: str | None = None
    home_strength_rating: int | None = Field(default=None, ge=1, le=100)
    home_user_id: str | None = None
    away_club_id: str | None = None
    away_club_name: str | None = None
    away_strength_rating: int | None = Field(default=None, ge=1, le=100)
    away_user_id: str | None = None
    replay_visibility: ReplayVisibility = ReplayVisibility.COMPETITION
    match_status: MatchStatus = MatchStatus.QUEUED
    is_cup_match: bool = False
    is_final: bool = False
    allow_penalties: bool = False
    no_extra_time: bool = True
    presentation_min_minutes: int = MATCH_PRESENTATION_MIN_MINUTES
    presentation_max_minutes: int = MATCH_PRESENTATION_MAX_MINUTES
    key_moments: tuple[str, ...] = DEFAULT_MATCH_MOMENTS
    idempotency_key: str | None = None

    @model_validator(mode="after")
    def validate_job(self) -> "MatchSimulationJob":
        if self.allow_penalties and not self.is_cup_match:
            raise ValueError("Penalty shootouts are only valid for cup matches.")
        if not self.no_extra_time:
            raise ValueError("Extra time is not supported in the match presentation flow.")
        if self.presentation_min_minutes < MATCH_PRESENTATION_MIN_MINUTES:
            raise ValueError("Presentation minimum minutes fall below the supported floor.")
        max_allowed = FINAL_PRESENTATION_MAX_MINUTES if self.is_final else MATCH_PRESENTATION_MAX_MINUTES
        if self.presentation_max_minutes > max_allowed:
            raise ValueError("Presentation maximum minutes exceed the allowed cap.")
        if self.presentation_min_minutes > self.presentation_max_minutes:
            raise ValueError("Presentation minimum minutes cannot exceed the maximum.")
        invalid_moments = set(self.key_moments) - set(SUPPORTED_MATCH_MOMENTS)
        if invalid_moments:
            raise ValueError(f"Unsupported match moments requested: {sorted(invalid_moments)}")
        if not self.is_cup_match and "penalties" in self.key_moments:
            raise ValueError("Penalties can only appear in cup match simulations.")
        if self.is_cup_match and self.allow_penalties and "penalties" not in self.key_moments:
            self.key_moments = (*self.key_moments, "penalties")
        if self.stage_name is None:
            self.stage_name = "final" if self.is_final else "regular"
        if self.competition_name is None:
            self.competition_name = self.competition_id
        if self.home_club_name is None and self.home_club_id is not None:
            self.home_club_name = self.home_club_id
        if self.away_club_name is None and self.away_club_id is not None:
            self.away_club_name = self.away_club_id
        if self.idempotency_key is None:
            self.idempotency_key = (
                f"match-simulation:{self.fixture_id}:{self.match_date.isoformat()}:{self.window.value}:{self.slot_sequence}"
            )
        return self


class BracketAdvancementJob(CommonSchema):
    queue_name: Literal["bracket_advancement"] = "bracket_advancement"
    job_name: Literal["bracket_advancement"] = "bracket_advancement"
    competition_id: str = Field(min_length=1)
    competition_type: CompetitionType
    source_fixture_id: str = Field(min_length=1)
    stage_code: str = Field(min_length=1)
    match_date: date
    winner_club_id: str | None = None
    home_goals: int | None = Field(default=None, ge=0)
    away_goals: int | None = Field(default=None, ge=0)
    decided_by_penalties: bool = False
    idempotency_key: str | None = None

    @model_validator(mode="after")
    def populate_idempotency_key(self) -> "BracketAdvancementJob":
        if (self.home_goals is None) != (self.away_goals is None):
            raise ValueError("Bracket advancement scores require both home and away goals.")
        if self.idempotency_key is None:
            self.idempotency_key = (
                f"bracket-advancement:{self.competition_id}:{self.stage_code}:{self.source_fixture_id}"
            )
        return self


class PayoutSettlementJob(CommonSchema):
    queue_name: Literal["payout_settlement"] = "payout_settlement"
    job_name: Literal["payout_settlement"] = "payout_settlement"
    competition_id: str = Field(min_length=1)
    competition_type: CompetitionType
    settlement_scope: str = Field(min_length=1)
    settlement_date: date
    source_fixture_id: str | None = None
    idempotency_key: str | None = None

    @model_validator(mode="after")
    def populate_idempotency_key(self) -> "PayoutSettlementJob":
        if self.idempotency_key is None:
            source_scope = self.source_fixture_id or self.settlement_scope
            self.idempotency_key = (
                f"payout-settlement:{self.competition_id}:{self.settlement_date.isoformat()}:{source_scope}"
            )
        return self


class NotificationJob(CommonSchema):
    queue_name: Literal["notification"] = "notification"
    job_name: Literal["notification"] = "notification"
    competition_id: str = Field(min_length=1)
    competition_type: CompetitionType
    template_key: str = Field(min_length=1)
    audience_key: str = Field(min_length=1)
    resource_id: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = None

    @model_validator(mode="after")
    def populate_idempotency_key(self) -> "NotificationJob":
        if self.idempotency_key is None:
            self.idempotency_key = (
                f"notification:{self.competition_id}:{self.template_key}:{self.resource_id}:{self.audience_key}"
            )
        return self


CompetitionQueueJob = (
    MatchSimulationJob
    | BracketAdvancementJob
    | PayoutSettlementJob
    | NotificationJob
)


class QueuedJobRecord(CommonSchema):
    queue_name: str = Field(min_length=1)
    job_name: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1)
    payload: dict[str, Any]
    published_at: datetime = Field(default_factory=utcnow)


class QueuePublisher(Protocol):
    def publish(self, job: CompetitionQueueJob) -> QueuedJobRecord:
        ...

    def list_published(self, queue_name: str | None = None) -> tuple[QueuedJobRecord, ...]:
        ...


@dataclass(slots=True)
class InMemoryQueuePublisher:
    event_publisher: EventPublisher = field(default_factory=InMemoryEventPublisher)
    _records: list[QueuedJobRecord] = field(default_factory=list)
    _idempotency_index: dict[str, QueuedJobRecord] = field(default_factory=dict)
    _lock: RLock = field(default_factory=RLock)

    def publish(self, job: CompetitionQueueJob) -> QueuedJobRecord:
        dedupe_key = f"{job.queue_name}:{job.idempotency_key}"
        with self._lock:
            existing = self._idempotency_index.get(dedupe_key)
            if existing is not None:
                return existing

            record = QueuedJobRecord(
                queue_name=job.queue_name,
                job_name=job.job_name,
                idempotency_key=job.idempotency_key or dedupe_key,
                payload=job.model_dump(mode="json"),
            )
            self._records.append(record)
            self._idempotency_index[dedupe_key] = record

        self.event_publisher.publish(
            DomainEvent(
                name=f"competition_engine.queue.{record.queue_name}.queued",
                payload={
                    "job_name": record.job_name,
                    "queue_name": record.queue_name,
                    "idempotency_key": record.idempotency_key,
                    "job_payload": record.payload,
                },
            )
        )
        return record

    def list_published(self, queue_name: str | None = None) -> tuple[QueuedJobRecord, ...]:
        with self._lock:
            records = tuple(self._records)
        if queue_name is None:
            return records
        return tuple(record for record in records if record.queue_name == queue_name)
