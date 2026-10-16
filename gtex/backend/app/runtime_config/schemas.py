from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from app.common.schemas.base import CommonSchema


class ViralWeightsConfig(CommonSchema):
    completion_rate: float = Field(default=0.35, ge=0.0, le=2.0)
    loop_rate: float = Field(default=0.20, ge=0.0, le=2.0)
    share_rate: float = Field(default=0.20, ge=0.0, le=2.0)
    comment_rate: float = Field(default=0.10, ge=0.0, le=2.0)
    avg_watch_time: float = Field(default=0.10, ge=0.0, le=2.0)
    skip_penalty: float = Field(default=0.15, ge=0.0, le=2.0)
    velocity_multiplier: float = Field(default=1.20, ge=1.0, le=3.0)
    sponsored_boost: float = Field(default=0.10, ge=0.0, le=1.0)


class ViralWeightsUpdate(CommonSchema):
    completion_rate: float | None = Field(default=None, ge=0.0, le=2.0)
    loop_rate: float | None = Field(default=None, ge=0.0, le=2.0)
    share_rate: float | None = Field(default=None, ge=0.0, le=2.0)
    comment_rate: float | None = Field(default=None, ge=0.0, le=2.0)
    avg_watch_time: float | None = Field(default=None, ge=0.0, le=2.0)
    skip_penalty: float | None = Field(default=None, ge=0.0, le=2.0)
    velocity_multiplier: float | None = Field(default=None, ge=1.0, le=3.0)
    sponsored_boost: float | None = Field(default=None, ge=0.0, le=1.0)


class FeedWeightsConfig(CommonSchema):
    viral_score: float = Field(default=0.40, ge=0.0, le=2.0)
    user_affinity: float = Field(default=0.30, ge=0.0, le=2.0)
    recency: float = Field(default=0.20, ge=0.0, le=2.0)
    repetition_penalty: float = Field(default=0.10, ge=0.0, le=2.0)
    social_boost: float = Field(default=0.06, ge=0.0, le=2.0)
    following_boost: float = Field(default=0.12, ge=0.0, le=2.0)
    following_feed_boost: float = Field(default=0.95, ge=0.0, le=2.0)
    hybrid_for_you_share: float = Field(default=0.60, ge=0.0, le=1.0)
    hybrid_following_share: float = Field(default=0.40, ge=0.0, le=1.0)
    exploration_rate: float = Field(default=0.50, ge=0.0, le=1.0)
    new_creator_boost: float = Field(default=0.12, ge=0.0, le=1.0)
    creator_feedback_boost: float = Field(default=0.08, ge=0.0, le=1.0)


class FeedWeightsUpdate(CommonSchema):
    viral_score: float | None = Field(default=None, ge=0.0, le=2.0)
    user_affinity: float | None = Field(default=None, ge=0.0, le=2.0)
    recency: float | None = Field(default=None, ge=0.0, le=2.0)
    repetition_penalty: float | None = Field(default=None, ge=0.0, le=2.0)
    social_boost: float | None = Field(default=None, ge=0.0, le=2.0)
    following_boost: float | None = Field(default=None, ge=0.0, le=2.0)
    following_feed_boost: float | None = Field(default=None, ge=0.0, le=2.0)
    hybrid_for_you_share: float | None = Field(default=None, ge=0.0, le=1.0)
    hybrid_following_share: float | None = Field(default=None, ge=0.0, le=1.0)
    exploration_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    new_creator_boost: float | None = Field(default=None, ge=0.0, le=1.0)
    creator_feedback_boost: float | None = Field(default=None, ge=0.0, le=1.0)


class TrustThresholdsConfig(CommonSchema):
    velocity_threshold: float = Field(default=0.30, ge=0.0, le=1.0)
    freeze_completion_floor: float = Field(default=0.42, ge=0.0, le=1.0)
    freeze_share_floor: float = Field(default=0.01, ge=0.0, le=1.0)
    freeze_skip_ceiling: float = Field(default=0.55, ge=0.0, le=1.0)


class TrustThresholdsUpdate(CommonSchema):
    velocity_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    freeze_completion_floor: float | None = Field(default=None, ge=0.0, le=1.0)
    freeze_share_floor: float | None = Field(default=None, ge=0.0, le=1.0)
    freeze_skip_ceiling: float | None = Field(default=None, ge=0.0, le=1.0)


class AdFrequencyConfig(CommonSchema):
    min_interval: int = Field(default=5, ge=1, le=20)
    max_interval: int = Field(default=8, ge=1, le=20)


class AdFrequencyUpdate(CommonSchema):
    min_interval: int | None = Field(default=None, ge=1, le=20)
    max_interval: int | None = Field(default=None, ge=1, le=20)


class RuntimeConfigSnapshot(CommonSchema):
    version: int = Field(default=1, ge=1)
    viral_weights: ViralWeightsConfig = Field(default_factory=ViralWeightsConfig)
    feed_weights: FeedWeightsConfig = Field(default_factory=FeedWeightsConfig)
    trust_thresholds: TrustThresholdsConfig = Field(default_factory=TrustThresholdsConfig)
    ad_frequency: AdFrequencyConfig = Field(default_factory=AdFrequencyConfig)
    ab_flags: dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime | None = None
    source: str = "defaults"


class RuntimeConfigUpdateRequest(CommonSchema):
    viral_weights: ViralWeightsUpdate | None = None
    feed_weights: FeedWeightsUpdate | None = None
    trust_thresholds: TrustThresholdsUpdate | None = None
    ad_frequency: AdFrequencyUpdate | None = None
    ab_flags: dict[str, Any] | None = None
