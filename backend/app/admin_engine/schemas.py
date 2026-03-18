from __future__ import annotations

from datetime import datetime, date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from backend.app.common.enums.competition_type import CompetitionType
from backend.app.common.enums.fixture_window import FixtureWindow
from backend.app.common.schemas.competition import CompetitionSchedulePlan, CompetitionScheduleRequest


class AdminGiftStabilityControlConfig(BaseModel):
    max_amount: Decimal = Field(default=Decimal("250.0000"), gt=0)
    daily_sender_limit: Decimal = Field(default=Decimal("1000.0000"), gt=0)
    daily_recipient_limit: Decimal = Field(default=Decimal("2500.0000"), gt=0)
    daily_pair_limit: Decimal = Field(default=Decimal("500.0000"), gt=0)
    cooldown_seconds: int = Field(default=0, ge=0, le=86_400)
    burst_window_seconds: int = Field(default=120, ge=10, le=86_400)
    burst_max_count: int = Field(default=6, ge=1, le=1_000)
    review_threshold_bps: int = Field(default=8500, ge=1000, le=10_000)


class AdminRewardLoopControlConfig(BaseModel):
    max_amount: Decimal = Field(default=Decimal("5000.0000"), gt=0)
    daily_user_limit: Decimal = Field(default=Decimal("10000.0000"), gt=0)
    daily_user_count_limit: int = Field(default=10, ge=1, le=1_000)
    burst_window_seconds: int = Field(default=3600, ge=60, le=86_400)
    burst_max_count: int = Field(default=5, ge=1, le=1_000)
    duplicate_window_seconds: int = Field(default=900, ge=60, le=86_400)
    review_threshold_bps: int = Field(default=8500, ge=1000, le=10_000)


class AdminFanPredictionFairnessConfig(BaseModel):
    min_distinct_participants_for_fancoin: int = Field(default=2, ge=1, le=1_000)
    max_fixture_promo_pool_fancoin: Decimal = Field(default=Decimal("250.0000"), ge=0)
    max_fancoin_pool_per_participant: Decimal = Field(default=Decimal("100.0000"), ge=0)
    max_reward_winners: int = Field(default=5, ge=1, le=100)


def _default_gtex_competition_gift_controls() -> AdminGiftStabilityControlConfig:
    return AdminGiftStabilityControlConfig(
        max_amount=Decimal("500.0000"),
        daily_sender_limit=Decimal("2500.0000"),
        daily_recipient_limit=Decimal("5000.0000"),
        daily_pair_limit=Decimal("1000.0000"),
        cooldown_seconds=0,
        burst_window_seconds=180,
        burst_max_count=8,
    )


def _default_creator_match_gift_controls() -> AdminGiftStabilityControlConfig:
    return AdminGiftStabilityControlConfig(
        max_amount=Decimal("150.0000"),
        daily_sender_limit=Decimal("600.0000"),
        daily_recipient_limit=Decimal("1800.0000"),
        daily_pair_limit=Decimal("300.0000"),
        cooldown_seconds=0,
        burst_window_seconds=120,
        burst_max_count=5,
    )


def _default_creator_viewer_purchase_controls() -> AdminRewardLoopControlConfig:
    return AdminRewardLoopControlConfig(
        max_amount=Decimal("150.0000"),
        daily_user_limit=Decimal("240.0000"),
        daily_user_count_limit=6,
        burst_window_seconds=900,
        burst_max_count=3,
        duplicate_window_seconds=900,
    )


class AdminRewardRuleStabilityControls(BaseModel):
    user_hosted_gift: AdminGiftStabilityControlConfig = Field(default_factory=AdminGiftStabilityControlConfig)
    gtex_competition_gift: AdminGiftStabilityControlConfig = Field(default_factory=_default_gtex_competition_gift_controls)
    creator_match_gift: AdminGiftStabilityControlConfig = Field(default_factory=_default_creator_match_gift_controls)
    creator_viewer_purchase: AdminRewardLoopControlConfig = Field(default_factory=_default_creator_viewer_purchase_controls)
    reward: AdminRewardLoopControlConfig = Field(default_factory=AdminRewardLoopControlConfig)
    fan_prediction: AdminFanPredictionFairnessConfig = Field(default_factory=AdminFanPredictionFairnessConfig)


class AdminFeatureFlagView(BaseModel):
    id: str
    feature_key: str
    title: str
    description: str | None = None
    enabled: bool
    audience: str
    updated_at: datetime


class AdminFeatureFlagUpsertRequest(BaseModel):
    feature_key: str = Field(min_length=2, max_length=64)
    title: str = Field(min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    enabled: bool = False
    audience: str = Field(default="global", min_length=1, max_length=32)


class AdminCalendarRuleView(BaseModel):
    id: str
    rule_key: str
    title: str
    description: str | None = None
    world_cup_exclusive: bool
    active: bool
    priority: int
    config_json: dict[str, Any]
    updated_at: datetime


class AdminCalendarRuleUpsertRequest(BaseModel):
    rule_key: str = Field(min_length=2, max_length=64)
    title: str = Field(min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    world_cup_exclusive: bool = False
    active: bool = True
    priority: int = Field(default=100, ge=0, le=10_000)
    config_json: dict[str, Any] = Field(default_factory=dict)


class AdminRewardRuleView(BaseModel):
    id: str
    rule_key: str
    title: str
    description: str | None = None
    trading_fee_bps: int
    gift_platform_rake_bps: int
    withdrawal_fee_bps: int
    minimum_withdrawal_fee_credits: Decimal
    competition_platform_fee_bps: int
    stability_controls: AdminRewardRuleStabilityControls = Field(default_factory=AdminRewardRuleStabilityControls)
    active: bool
    updated_at: datetime


class AdminRewardRuleUpsertRequest(BaseModel):
    rule_key: str = Field(min_length=2, max_length=64)
    title: str = Field(min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    trading_fee_bps: int = Field(default=2000, ge=0, le=5000)
    gift_platform_rake_bps: int = Field(default=3000, ge=0, le=5000)
    withdrawal_fee_bps: int = Field(default=1000, ge=0, le=5000)
    minimum_withdrawal_fee_credits: Decimal = Field(default=Decimal("5.0000"), ge=0)
    competition_platform_fee_bps: int = Field(default=1000, ge=0, le=5000)
    stability_controls: AdminRewardRuleStabilityControls = Field(default_factory=AdminRewardRuleStabilityControls)
    active: bool = True


class CompetitionSchedulePreviewRequest(BaseModel):
    requests: list[CompetitionScheduleRequest]


class CompetitionSchedulePreviewResponse(BaseModel):
    applied_rule_keys: list[str]
    world_cup_exclusive_rule_active: bool
    plan: CompetitionSchedulePlan


class CompetitionScheduleBootstrapView(BaseModel):
    active_feature_flags: list[AdminFeatureFlagView]
    active_calendar_rules: list[AdminCalendarRuleView]
    active_reward_rules: list[AdminRewardRuleView]


class QuickCompetitionScheduleRequest(BaseModel):
    competition_id: str = Field(min_length=1)
    competition_type: CompetitionType
    requested_dates: list[date]
    preferred_windows: list[FixtureWindow] = Field(default_factory=list)
    required_windows: int = Field(default=1, ge=1, le=8)
    priority: int = Field(default=100, ge=0, le=10_000)
    requires_exclusive_windows: bool = False
