from __future__ import annotations

from datetime import datetime, date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from backend.app.common.enums.competition_type import CompetitionType
from backend.app.common.enums.fixture_window import FixtureWindow
from backend.app.common.schemas.competition import CompetitionSchedulePlan, CompetitionScheduleRequest


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
