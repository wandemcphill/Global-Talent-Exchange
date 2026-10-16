from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import ConfigDict, Field

from app.common.schemas.base import CommonSchema
from app.schemas.creator_requests import CreatorCopilotDraftRequest


class CreatorProfileView(CommonSchema):
    model_config = ConfigDict(from_attributes=True)

    creator_id: str
    user_id: str
    handle: str
    display_name: str
    tier: str
    status: str
    default_share_code: str | None = None
    default_competition_id: str | None = None
    revenue_share_percent: Decimal | None = None
    created_at: datetime
    updated_at: datetime


class CreatorCompetitionView(CommonSchema):
    model_config = ConfigDict(from_attributes=True)

    competition_id: str
    title: str
    linked_share_code: str | None = None
    active_participants: int = 0
    attributed_signups: int = 0
    qualified_joins: int = 0


class CreatorSummaryView(CommonSchema):
    model_config = ConfigDict(from_attributes=True)

    profile: CreatorProfileView
    total_signups: int = 0
    qualified_joins: int = 0
    active_participants: int = 0
    pending_rewards: int = 0
    approved_rewards: int = 0
    featured_competitions: list[CreatorCompetitionView] = Field(default_factory=list)


class CreatorFinanceSummaryView(CommonSchema):
    currency: str = "credits"
    total_gift_income: Decimal = Decimal("0.0000")
    total_reward_income: Decimal = Decimal("0.0000")
    total_clip_income: Decimal = Decimal("0.0000")
    total_clip_views: int = 0
    monetized_clips: int = 0
    viral_clip_count: int = 0
    total_viral_bonus: Decimal = Decimal("0.0000")
    total_referral_bonus: Decimal = Decimal("0.0000")
    total_weekly_top_creator_bonus: Decimal = Decimal("0.0000")
    total_withdrawn_gross: Decimal = Decimal("0.0000")
    total_withdrawal_fees: Decimal = Decimal("0.0000")
    total_withdrawn_net: Decimal = Decimal("0.0000")
    pending_withdrawals: Decimal = Decimal("0.0000")
    wallet_balance: Decimal = Decimal("0.0000")
    wallet_available_balance: Decimal = Decimal("0.0000")
    wallet_currency: str = "credits"
    active_competitions: int = 0
    attributed_signups: int = 0
    qualified_joins: int = 0
    insights: list[str] = Field(default_factory=list)


class CreatorMetricProfileView(CommonSchema):
    avg_completion_rate: float = 0.0
    avg_share_rate: float = 0.0
    avg_loop_rate: float = 0.0
    viral_hit_rate: float = 0.0
    best_format: str | None = None
    worst_format: str | None = None
    optimal_duration: str | None = None
    audience_cluster: str | None = None


class CreatorInsightAnalyzerView(CommonSchema):
    strongest_format: str | None = None
    patterns: list[str] = Field(default_factory=list)
    clips_analyzed: int = 0


class CreatorInsightRecommendationView(CommonSchema):
    best_format: str | None = None
    optimal_length: str | None = None
    hook_style: str | None = None
    posting_strategy: str | None = None


class CreatorViralFeedbackLoopView(CommonSchema):
    clips_analyzed: int = 0
    high_retention_clips: int = 0
    shorten_clip_signals: int = 0
    caption_adjustment_signals: int = 0
    increase_similar_signals: int = 0
    recommended_actions: list[str] = Field(default_factory=list)


class CreatorInsightsView(CommonSchema):
    creator_id: str
    profile_key: str
    creator_metrics: CreatorMetricProfileView
    analyzer: CreatorInsightAnalyzerView
    recommendations: CreatorInsightRecommendationView
    viral_feedback_loop: CreatorViralFeedbackLoopView


class CreatorCopilotPredictionView(CommonSchema):
    viral_probability: float = Field(default=0.0, ge=0.0, le=1.0)
    expected_views: int = Field(default=0, ge=0)
    best_format: str
    risk_flags: list[str] = Field(default_factory=list)


class CreatorCopilotVariantRecommendationView(CommonSchema):
    type: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reason: str
    exploratory: bool = False


class CreatorCopilotVariantStrategyView(CommonSchema):
    recommended_variants: list[CreatorCopilotVariantRecommendationView] = Field(default_factory=list)
    exploration_factor: float = Field(default=0.2, ge=0.0, le=1.0)
    rationale: list[str] = Field(default_factory=list)


class CreatorCopilotTimingView(CommonSchema):
    post_now: bool = False
    best_time_in_minutes: int = Field(default=0, ge=0)
    reason: str
    competition_density: float = Field(default=0.0, ge=0.0, le=1.0)
    audience_activity: float = Field(default=0.0, ge=0.0, le=1.0)


class CreatorCopilotHookAnalysisView(CommonSchema):
    hook_score: float = Field(default=0.0, ge=0.0, le=1.0)
    suggestion: str
    intro_strength: str
    event_density: float = Field(default=0.0, ge=0.0, le=1.0)
    visual_intensity: float = Field(default=0.0, ge=0.0, le=1.0)


class CreatorCopilotStrategyProfileView(CommonSchema):
    profile_key: str
    archetype: str
    summary: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    winning_formats: list[str] = Field(default_factory=list)
    winning_duration: str | None = None
    audience_cluster: str | None = None


class CreatorCopilotLiveCoachingView(CommonSchema):
    event_name: str = "copilot.alert.triggered"
    headline: str
    message: str
    recommended_action: str


class CreatorCopilotAnalysisView(CommonSchema):
    creator_id: str
    draft: CreatorCopilotDraftRequest
    prediction: CreatorCopilotPredictionView
    variant_strategy: CreatorCopilotVariantStrategyView
    timing: CreatorCopilotTimingView
    hook_analysis: CreatorCopilotHookAnalysisView
    strategy_profile: CreatorCopilotStrategyProfileView
    live_coaching: CreatorCopilotLiveCoachingView
    action_plan: list[str] = Field(default_factory=list)
