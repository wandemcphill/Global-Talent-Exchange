from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AnalyticsEventCreate(BaseModel):
    name: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class AnalyticsEventView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    user_id: str | None
    metadata_json: dict[str, Any]
    created_at: datetime


class AnalyticsSummaryItem(BaseModel):
    name: str
    count: int


class AnalyticsSummaryView(BaseModel):
    since: datetime
    totals: list[AnalyticsSummaryItem]


class AnalyticsFunnelStep(BaseModel):
    name: str
    users: int


class AnalyticsFunnelView(BaseModel):
    since: datetime
    steps: list[AnalyticsFunnelStep]


class PlayerMatchAnalyticsFunnelStep(BaseModel):
    event: str
    count: int


class PlayerMatchScoreMetricView(BaseModel):
    event: str
    average_score: float | None = None


class PlayerMatchDistributionItemView(BaseModel):
    label: str
    count: int


class PlayerMatchWeightItemView(BaseModel):
    factor: str
    weight: float


class PlayerMatchAnalyticsView(BaseModel):
    since: datetime
    funnel: list[PlayerMatchAnalyticsFunnelStep]
    score_effectiveness: list[PlayerMatchScoreMetricView]
    top_positions: list[PlayerMatchDistributionItemView]
    top_countries: list[PlayerMatchDistributionItemView]
    age_buckets: list[PlayerMatchDistributionItemView]
    weights: list[PlayerMatchWeightItemView]


class PlayerMatchWeightRefreshView(BaseModel):
    weights: list[PlayerMatchWeightItemView]


class AnalyticsDeviceFingerprintView(BaseModel):
    fingerprint: str
    source_signals: list[str] = Field(default_factory=list)


class AnalyticsPricePredictionView(BaseModel):
    player_id: str
    current_price: float | None = None
    predicted_price: float | None = None
    predicted_direction: str
    confidence: float
    rationale: list[str] = Field(default_factory=list)


class AnalyticsPricePredictionResponse(BaseModel):
    generated_at: datetime
    items: list[AnalyticsPricePredictionView] = Field(default_factory=list)


class AnalyticsUserSegmentEntryView(BaseModel):
    segment: str
    user_count: int
    share: float


class AnalyticsUserSegmentationView(BaseModel):
    generated_at: datetime
    segments: list[AnalyticsUserSegmentEntryView] = Field(default_factory=list)


class AnalyticsMatchOutcomeView(BaseModel):
    generated_at: datetime
    since: datetime
    matches: int
    avg_total_goals: float
    home_win_rate: float
    away_win_rate: float
    draw_rate: float
    upset_rate: float


class AnalyticsAnomalyBucketView(BaseModel):
    key: str
    count: int


class AnalyticsMatchValidationSignalView(BaseModel):
    code: str
    severity: str
    detail: str


class AnalyticsIntegrityFindingView(BaseModel):
    match_id: str
    anti_cheat_score: int
    tampering_risk: str
    recommended_action: str
    signals: list[AnalyticsMatchValidationSignalView] = Field(default_factory=list)
    validated_at: datetime


class AnalyticsAnomalySummaryView(BaseModel):
    generated_at: datetime
    since: datetime
    critical_count: int
    buckets: list[AnalyticsAnomalyBucketView] = Field(default_factory=list)
    matches_scanned: int = 0
    flagged_matches: int = 0
    top_findings: list[AnalyticsIntegrityFindingView] = Field(default_factory=list)


class AnalyticsAgentLearningView(BaseModel):
    mode: str
    status: str
    since: datetime
    analytics: PlayerMatchAnalyticsView


class ClipLifecycleStageView(BaseModel):
    stage: str
    count: int


class ClipAnalyticsDetailView(BaseModel):
    clip_id: str
    impressions: int
    views: int
    completions: int
    completion_rate: float
    shares: int
    revenue: Decimal
    avg_watch_time_seconds: float
    drop_off_point_seconds: float | None = None
    funnel: list[ClipLifecycleStageView] = Field(default_factory=list)


class ClipDashboardItemView(BaseModel):
    clip_id: str
    title: str | None = None
    views: int
    completion_rate: float
    shares: int
    revenue: Decimal
    score: float


class ClipDropOffItemView(BaseModel):
    clip_id: str
    title: str | None = None
    views: int
    completion_rate: float
    drop_off_point_seconds: float | None = None


class ClipDashboardResponse(BaseModel):
    generated_at: datetime
    items: list[ClipDashboardItemView] = Field(default_factory=list)


class ClipDropOffDashboardResponse(BaseModel):
    generated_at: datetime
    items: list[ClipDropOffItemView] = Field(default_factory=list)
