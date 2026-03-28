from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, TypeAlias
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


Payload: TypeAlias = dict[str, Any]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class OrchestratorSchema(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        use_enum_values=False,
    )


class BaseCommand(OrchestratorSchema):
    command_id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=_utc_now)


class BaseEvent(OrchestratorSchema):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = Field(default_factory=_utc_now)


class StartMatchCommand(BaseCommand):
    payload: Payload = Field(default_factory=dict)


class CompleteMatchCommand(BaseCommand):
    result: Payload = Field(default_factory=dict)


class CalculateRewardsCommand(BaseCommand):
    result: Payload = Field(default_factory=dict)


class MatchStartedEvent(BaseEvent):
    payload: Payload = Field(default_factory=dict)


class MatchCompletedEvent(BaseEvent):
    result: Payload = Field(default_factory=dict)


class RewardsDistributedEvent(BaseEvent):
    rewards: Payload = Field(default_factory=dict)


class ClipAttentionStateView(OrchestratorSchema):
    clip_id: str
    stage: str = "test"
    allocated_impressions: int = Field(default=0, ge=0)
    consumed_impressions: int = Field(default=0, ge=0)
    remaining_impressions: int = Field(default=0, ge=0)
    velocity_score: float = Field(default=0.0, ge=0.0)
    quality_score: float = Field(default=0.0, ge=0.0, le=1.0)
    trust_score: float = Field(default=0.0, ge=0.0, le=1.0)
    orchestrator_weight: float = Field(default=0.0, ge=0.0)
    is_ad: bool = False
    is_moment: bool = False
    winner_variant_id: str | None = None
    metadata: Payload = Field(default_factory=dict)
    updated_at: datetime = Field(default_factory=_utc_now)


class AttentionOrchestratorConfigView(OrchestratorSchema):
    test_impressions_cap: int = Field(default=1000, ge=1)
    expand_multiplier: float = Field(default=3.0, ge=1.0)
    viral_base_cap: int = Field(default=9000, ge=1)
    viral_velocity_cap_multiplier: float = Field(default=6000.0, ge=0.0)
    new_clip_minimum_impressions: int = Field(default=200, ge=0)
    new_clip_age_hours: float = Field(default=12.0, ge=0.0)
    moment_boost: float = Field(default=1.5, ge=1.0)
    expand_threshold: float = Field(default=0.8, ge=0.0)
    viral_threshold: float = Field(default=1.35, ge=0.0)
    decay_threshold: float = Field(default=0.2, ge=0.0)
    winner_share: float = Field(default=0.70, ge=0.0, le=1.0)
    exploration_share: float = Field(default=0.30, ge=0.0, le=1.0)


class AttentionOrchestratorConfigUpdateRequest(OrchestratorSchema):
    test_impressions_cap: int | None = Field(default=None, ge=1)
    expand_multiplier: float | None = Field(default=None, ge=1.0)
    viral_base_cap: int | None = Field(default=None, ge=1)
    viral_velocity_cap_multiplier: float | None = Field(default=None, ge=0.0)
    new_clip_minimum_impressions: int | None = Field(default=None, ge=0)
    new_clip_age_hours: float | None = Field(default=None, ge=0.0)
    moment_boost: float | None = Field(default=None, ge=1.0)
    expand_threshold: float | None = Field(default=None, ge=0.0)
    viral_threshold: float | None = Field(default=None, ge=0.0)
    decay_threshold: float | None = Field(default=None, ge=0.0)
    winner_share: float | None = Field(default=None, ge=0.0, le=1.0)
    exploration_share: float | None = Field(default=None, ge=0.0, le=1.0)


class AttentionOrchestratorMetricsView(OrchestratorSchema):
    clip_count: int = Field(default=0, ge=0)
    total_allocated_impressions: int = Field(default=0, ge=0)
    total_consumed_impressions: int = Field(default=0, ge=0)
    available_clip_count: int = Field(default=0, ge=0)
    stage_distribution: dict[str, int] = Field(default_factory=dict)
    ad_clip_count: int = Field(default=0, ge=0)
    moment_clip_count: int = Field(default=0, ge=0)
    sample_clips: list[ClipAttentionStateView] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=_utc_now)
