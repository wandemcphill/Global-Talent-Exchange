from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import Field

from app.common.schemas.base import CommonSchema


class ReferralRiskFlagView(CommonSchema):
    flag_id: str
    flag_type: str
    severity: str
    subject_kind: str
    subject_id: str
    status: str
    reason_codes: tuple[str, ...] = ()
    payload_json: dict[str, str] = Field(default_factory=dict)
    detected_at: datetime


class ReferralAnalyticsDailyView(CommonSchema):
    analytics_date: date | None = None
    metric_date: date | None = None
    scope: str | None = None
    scope_id: str | None = None
    creator_profile_id: str | None = None
    share_code_id: str | None = None
    codes_created: int = 0
    codes_redeemed: int = 0
    attributed_signups: int = 0
    qualified_referrals: int = 0
    creator_competition_joins: int = 0
    retained_users: int = 0
    approved_rewards: int = 0
    blocked_rewards: int = 0
    reward_cost: Decimal = Decimal("0")
    signups_count: int = 0
    qualified_users_count: int = 0
    retained_day_7_count: int = 0
    retained_day_30_count: int = 0
    reward_count: int = 0
    blocked_reward_count: int = 0
    approved_reward_amount: Decimal = Decimal("0.0000")


class CreatorLeaderboardEntryView(CommonSchema):
    creator_id: str
    handle: str | None = None
    creator_handle: str | None = None
    display_name: str | None = None
    creator_display_name: str | None = None
    tier: str
    rank: int
    score: Decimal = Decimal("0")
    fraud_adjusted_score: Decimal = Decimal("0")
    risk_penalty: Decimal = Decimal("0")
    headline: str = ""
    attributed_signups: int = 0
    qualified_participants: int = 0
    creator_competition_joins: int = 0
    net_revenue_contribution: Decimal = Decimal("0")
    total_signups: int = 0
    qualified_joins: int = 0
    active_participants: int = 0
    retained_users: int = 0
    approved_reward_amount: Decimal = Decimal("0.0000")


class ReferralSourceRetentionView(CommonSchema):
    source_channel: str
    signups: int = 0
    retained_day_7: int = 0
    retained_day_30: int = 0
    retention_rate_day_7: Decimal = Decimal("0")
    retention_rate_day_30: Decimal = Decimal("0")


class CreatorCampaignPerformanceView(CommonSchema):
    creator_id: str | None = None
    creator_handle: str | None = None
    share_code_id: str | None = None
    share_code: str | None = None
    campaign_name: str | None = None
    linked_competition_id: str | None = None
    attributed_signups: int = 0
    qualified_participants: int = 0
    creator_competition_joins: int = 0
    retained_users: int = 0
    pending_rewards: int = 0
    approved_rewards: int = 0
    blocked_rewards: int = 0
    reward_cost: Decimal = Decimal("0")
    participation_quality_rate: Decimal = Decimal("0")
    retention_rate: Decimal = Decimal("0")


class CommunityGrowthEfficiencyView(CommonSchema):
    reward_cost: Decimal = Decimal("0")
    qualified_referrals: int = 0
    retained_users: int = 0
    blocked_rewards: int = 0
    cost_per_qualified_referral: Decimal = Decimal("0")
    retained_users_per_100_credits: Decimal = Decimal("0")
    net_community_growth_efficiency: Decimal = Decimal("0")


class ReferralAnalyticsSummaryView(CommonSchema):
    generated_at: datetime
    codes_created: int = 0
    codes_redeemed: int = 0
    attributed_signups: int = 0
    qualified_referrals: int = 0
    creator_competition_joins: int = 0
    retained_users: int = 0
    reward_cost: Decimal = Decimal("0")
    approved_rewards: int = 0
    blocked_rewards: int = 0
    pending_rewards: int = 0
    retention_by_source: list[ReferralSourceRetentionView] = Field(default_factory=list)
    top_campaigns: list[CreatorCampaignPerformanceView] = Field(default_factory=list)
    daily: list["ReferralAnalyticsDailyView"] = Field(default_factory=list)
    efficiency: CommunityGrowthEfficiencyView = Field(default_factory=CommunityGrowthEfficiencyView)


class CreatorLeaderboardResponse(CommonSchema):
    generated_at: datetime
    metric: str = "fraud_adjusted_score"
    items: list["CreatorLeaderboardEntryView"] = Field(default_factory=list)
