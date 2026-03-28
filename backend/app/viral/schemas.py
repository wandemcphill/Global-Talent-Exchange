from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from app.common.schemas.base import CommonSchema


class ViralScoreBreakdownView(CommonSchema):
    base_event: int = 0
    xg_bonus: int = 0
    late_drama_bonus: int = 0
    comeback_bonus: int = 0
    go_ahead_bonus: int = 0
    equalizer_bonus: int = 0
    rivalry_bonus: int = 0
    upset_bonus: int = 0
    stage_bonus: int = 0
    crowd_bonus: int = 0
    importance_bonus: int = 0
    chaos_bonus: int = 0
    total: int = 0


class ViralCaptionView(CommonSchema):
    hook: str
    caption: str
    cta: str = "Share to WhatsApp"
    hashtags: list[str] = Field(default_factory=list)
    source: str = "template"


class ViralPersonaView(CommonSchema):
    name: str
    tone: str


class ViralCaptionTestView(CommonSchema):
    variant_key: str
    audience: str
    hook: str
    caption: str
    hashtags: list[str] = Field(default_factory=list)
    source: str = "template"
    hypothesis: str | None = None


class ViralDistributionAccountView(CommonSchema):
    handle: str
    niche: str
    target_audience: str
    fit_score: int = Field(default=0, ge=0, le=100)
    persona: ViralPersonaView
    cross_promo_handles: list[str] = Field(default_factory=list)
    caption_tests: list[ViralCaptionTestView] = Field(default_factory=list)


class ViralAccountCatalogItemView(CommonSchema):
    handle: str
    niche: str
    target_audience: str
    focus_event_types: list[str] = Field(default_factory=list)
    persona: ViralPersonaView


class ViralAccountCatalogResponse(CommonSchema):
    accounts: list[ViralAccountCatalogItemView] = Field(default_factory=list)


class ViralEditPlanView(CommonSchema):
    format_key: str = "instant_clip"
    style_preset: str = "instant_clip"
    aspect_ratio: str = "9:16"
    crop_filter: str
    overlay_text: str
    transcode_command: list[str] = Field(default_factory=list)
    overlay_command: list[str] = Field(default_factory=list)
    audio_mix_profile: str = "broadcast_clean"
    loop_window_seconds: int = Field(default=6, ge=1)
    watermark_text: str = "GTEX"
    share_targets: list[str] = Field(default_factory=list)
    narrative_device: str = "raw_moment"
    effect_stack: list[str] = Field(default_factory=list)
    publish_strategy: str = "post_now"
    commentary_prompt: str | None = None


class ViralContentFormatView(CommonSchema):
    format_key: str
    title: str
    description: str
    editor: ViralEditPlanView


class ViralClipAnalyticsView(CommonSchema):
    clip_id: str
    view_count: int = Field(default=0, ge=0)
    completions: int = Field(default=0, ge=0)
    watch_time: float = Field(default=0.0, ge=0.0)
    total_watch_time: float = Field(default=0.0, ge=0.0)
    loops: float = Field(default=0.0, ge=0.0)
    loop_rate: float = Field(default=0.0, ge=0.0)
    shares: int = Field(default=0, ge=0)
    comments: int = Field(default=0, ge=0)
    skips: int = Field(default=0, ge=0)
    completion_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    drop_off_point_seconds: float | None = Field(default=None, ge=0.0)
    share_rate: float = Field(default=0.0, ge=0.0)
    comment_rate: float = Field(default=0.0, ge=0.0)
    views_last_10min: int = Field(default=0, ge=0)
    views_last_60min: int = Field(default=0, ge=0)


class ViralFeedbackLoopView(CommonSchema):
    performance_tier: str
    recommendation: str
    increase_similar_clips: bool = False
    adjust_captions: bool = False
    shorten_clips: bool = False
    actions: list[str] = Field(default_factory=list)
    viral_analysis: str
    analysis_source: str = "heuristic"


class ViralClipDistributionView(CommonSchema):
    impressions_served: int = Field(default=0, ge=0)
    impressions_cap: int = Field(default=100, ge=1)
    expansion_stage: str = "test"
    frozen: bool = False
    eligible: bool = True
    remaining_impressions: int = Field(default=0, ge=0)
    freeze_reason: str | None = None


class ViralClipView(CommonSchema):
    clip_id: str
    match_id: str
    highlight_id: str
    title: str
    reel_title: str | None = None
    team_name: str | None = None
    player_name: str | None = None
    event_type: str
    minute: int = Field(ge=0)
    scoreline_label: str | None = None
    storage_key: str | None = None
    video_url: str | None = None
    duration_seconds: float | None = Field(default=None, ge=0.0)
    render_status: str = "manifest_ready"
    viral_score: int = Field(default=0, ge=0)
    engagement: float = Field(default=0.0, ge=0.0)
    freshness: float = Field(default=0.0, ge=0.0)
    ranking_score: float = Field(default=0.0, ge=0.0)
    tags: list[str] = Field(default_factory=list)
    share_channel: str = "whatsapp"
    breakdown: ViralScoreBreakdownView
    caption: ViralCaptionView
    distribution_accounts: list[ViralDistributionAccountView] = Field(default_factory=list)
    editor: ViralEditPlanView
    formats: list[ViralContentFormatView] = Field(default_factory=list)
    analytics: ViralClipAnalyticsView
    feedback: ViralFeedbackLoopView
    distribution: ViralClipDistributionView | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ViralClipVariantView(CommonSchema):
    base_clip_id: str
    variant_id: str
    format_type: str
    created_at: datetime
    viral_score: float = Field(default=0.0, ge=0.0)
    distribution_weight: float = Field(default=0.0, ge=0.0)
    promotion_status: str = "exploring"
    promotion_enabled: bool = True
    pushed_to_trending: bool = False
    is_winner: bool = False
    analytics: ViralClipAnalyticsView
    metadata: dict[str, Any] = Field(default_factory=dict)


class ViralSessionAffinityView(CommonSchema):
    content_types: dict[str, float] = Field(default_factory=dict)
    formats: dict[str, float] = Field(default_factory=dict)
    teams: dict[str, float] = Field(default_factory=dict)
    clip_event_types: dict[str, float] = Field(default_factory=dict)
    tags: dict[str, float] = Field(default_factory=dict)
    override_dimensions: list[str] = Field(default_factory=list)


class ViralSessionFeedContextView(CommonSchema):
    session_id: str
    refreshed: bool = False
    refresh_after_clips: int = Field(default=5, ge=1)
    clips_until_refresh: int = Field(default=0, ge=0)
    pending_refresh: bool = False
    override_global_affinity: bool = False
    affinity: ViralSessionAffinityView = Field(default_factory=ViralSessionAffinityView)


class ViralSessionStateView(CommonSchema):
    session_id: str
    clips_seen: int = Field(default=0, ge=0)
    watch_time_ms: int = Field(default=0, ge=0)
    skips: int = Field(default=0, ge=0)
    interactions: int = Field(default=0, ge=0)
    refresh_after_clips: int = Field(default=5, ge=1)
    clips_until_refresh: int = Field(default=0, ge=0)
    pending_refresh: bool = False
    affinity: ViralSessionAffinityView = Field(default_factory=ViralSessionAffinityView)
    last_updated_at: datetime


class TrustFactorView(CommonSchema):
    account_age: float = Field(default=0.0, ge=0.0, le=1.0)
    session_consistency: float = Field(default=0.0, ge=0.0, le=1.0)
    device_fingerprint_stability: float = Field(default=0.0, ge=0.0, le=1.0)
    engagement_authenticity: float = Field(default=0.0, ge=0.0, le=1.0)
    anomaly_detection: float = Field(default=0.0, ge=0.0, le=1.0)


class TrustProfileView(CommonSchema):
    user_id: str
    trust_score: float = Field(default=0.0, ge=0.0, le=1.0)
    shadow_banned: bool = False
    monetization_eligible: bool = True
    ranking_eligible: bool = True
    suspicious_flags: list[str] = Field(default_factory=list)
    suspicious_event_count: int = Field(default=0, ge=0)
    healthy_event_count: int = Field(default=0, ge=0)
    factors: TrustFactorView
    updated_at: datetime


class ViralFeedResponse(CommonSchema):
    clips: list[ViralClipView] = Field(default_factory=list)
    generated_at: datetime
    personalization: dict[str, Any] = Field(default_factory=dict)
    session: ViralSessionFeedContextView | None = None


class PersonalizedFeedAffinityView(CommonSchema):
    view_signal: float = Field(default=0.0, ge=0.0, le=1.0)
    like_signal: float = Field(default=0.0, ge=0.0, le=1.0)
    share_signal: float = Field(default=0.0, ge=0.0, le=1.0)
    format_preference: float = Field(default=0.0, ge=0.0, le=1.0)
    creator_preference: float = Field(default=0.0, ge=0.0, le=1.0)


class PersonalizedFeedScoreBreakdownView(CommonSchema):
    viral_score: float = Field(default=0.0, ge=0.0, le=1.0)
    user_affinity: float = Field(default=0.0, ge=0.0, le=1.0)
    recency_score: float = Field(default=0.0, ge=0.0, le=1.0)
    repetition_penalty: float = Field(default=0.0, ge=0.0, le=1.0)
    diversity_penalty: float = Field(default=0.0, ge=0.0, le=1.0)
    social_boost: float = Field(default=0.0, ge=0.0)
    creator_boost: float = Field(default=0.0, ge=0.0)
    following_boost: float = Field(default=0.0, ge=0.0, le=1.0)
    cold_start_exploration: bool = False
    affinity: PersonalizedFeedAffinityView


class PersonalizedFeedClipView(ViralClipView):
    rank: int = Field(default=1, ge=1)
    score: float = Field(default=0.0, ge=0.0)
    feed_source: str = "for_you"
    score_breakdown: PersonalizedFeedScoreBreakdownView


class PersonalizedFeedResponse(CommonSchema):
    user_id: str
    clips: list[PersonalizedFeedClipView] = Field(default_factory=list)
    generated_at: datetime
    feed_key: str
    feed_type: str = "for_you"
    mix: dict[str, float] = Field(default_factory=dict)
    cache_hit: bool = False


class ViralTrendingMetricsView(CommonSchema):
    completion_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    avg_watch_time: float = Field(default=0.0, ge=0.0)
    avg_watch_time_normalized: float = Field(default=0.0, ge=0.0, le=1.0)
    loop_rate: float = Field(default=0.0, ge=0.0)
    share_rate: float = Field(default=0.0, ge=0.0)
    comment_rate: float = Field(default=0.0, ge=0.0)
    skip_rate: float = Field(default=0.0, ge=0.0)
    velocity: float = Field(default=0.0, ge=0.0)
    views_last_10min: int = Field(default=0, ge=0)
    views_last_60min: int = Field(default=0, ge=0)
    velocity_boost_applied: bool = False
    decay_multiplier: float = Field(default=1.0, ge=0.0)


class ViralTrendingClipView(ViralClipView):
    rank: int = Field(default=1, ge=1)
    trending_score: float = Field(default=0.0, ge=0.0)
    age_hours: float = Field(default=0.0, ge=0.0)
    recompute_bucket: str = "hot"
    last_ranked_at: datetime
    trending_metrics: ViralTrendingMetricsView


class ViralTrendingResponse(CommonSchema):
    clips: list[ViralTrendingClipView] = Field(default_factory=list)
    generated_at: datetime
    refreshed: bool = False
    leaderboard_key: str = "leaderboard:clips"


class ViralCascadeMetricsView(CommonSchema):
    velocity: float = Field(default=0.0, ge=0.0)
    completion_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    share_rate: float = Field(default=0.0, ge=0.0)
    views_last_10min: int = Field(default=0, ge=0)
    views_last_60min: int = Field(default=0, ge=0)
    view_count: int = Field(default=0, ge=0)
    source: str = "clip_analytics"


class ViralCascadeActionView(CommonSchema):
    distribution_cap_multiplier: int = Field(default=1, ge=1)
    feed_injection_targets: list[str] = Field(default_factory=list)
    pinned_in_trending: bool = False


class ViralCascadeView(CommonSchema):
    clip_id: str
    match_id: str | None = None
    highlight_id: str | None = None
    title: str | None = None
    cascade: bool = False
    status: str = "inactive"
    triggered_at: datetime
    active_until: datetime
    cooldown_until: datetime
    trigger_count: int = Field(default=1, ge=1)
    actions: ViralCascadeActionView
    metrics: ViralCascadeMetricsView
    metadata: dict[str, Any] = Field(default_factory=dict)


class ViralCascadesResponse(CommonSchema):
    cascades: list[ViralCascadeView] = Field(default_factory=list)
    generated_at: datetime


class ViralClipVariantsResponse(CommonSchema):
    clip_id: str
    variants: list[ViralClipVariantView] = Field(default_factory=list)
    resolved: bool = False
    leading_variant_id: str | None = None
    generated_at: datetime


class ViralClipWinnerResponse(CommonSchema):
    clip_id: str
    resolved: bool = False
    decision_reason: str | None = None
    winner: ViralClipVariantView | None = None
    leading_variant: ViralClipVariantView | None = None
    generated_at: datetime
