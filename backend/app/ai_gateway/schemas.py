from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AiUsageTotals(BaseModel):
    model_config = ConfigDict(extra="ignore")

    request_count: int = 0
    success_count: int = 0
    error_count: int = 0
    blocked_count: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0


class AiFeatureView(BaseModel):
    model_config = ConfigDict(extra="ignore")

    feature_key: str
    enabled: bool
    audience: str
    complexity: str
    model: str | None = None
    max_requests_per_day: int
    max_output_tokens: int
    cache_ttl_seconds: int


class AiErrorView(BaseModel):
    model_config = ConfigDict(extra="ignore")

    feature: str
    status: str
    error_code: str | None = None
    model: str | None = None
    created_at: str


class AiLimitView(BaseModel):
    model_config = ConfigDict(extra="ignore")

    subject_type: str
    subject_key: str
    max_requests: int
    window_seconds: int


class AiStatusView(BaseModel):
    """Admin status. Credential material is not a field on this model."""

    model_config = ConfigDict(extra="ignore")

    provider: str
    integration_status: str
    environment_enabled: bool
    admin_enabled: bool
    effective_enabled: bool
    api_key_configured: bool
    model: str
    complex_model: str
    max_retries: int
    timeout_ms: int
    daily_budget_usd: float
    monthly_budget_usd: float
    max_input_tokens: int
    max_output_tokens: int
    user_requests_per_minute: int
    global_requests_per_minute: int
    legacy_clients_routed: bool
    config_errors: list[str]
    features: list[AiFeatureView]
    usage: dict[str, Any]
    limits: list[AiLimitView] = Field(default_factory=list)
    authoritative: bool = False


class AiProviderUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool
    model: str | None = Field(default=None, max_length=64)
    daily_budget_usd: float = Field(ge=0, le=10_000)
    monthly_budget_usd: float = Field(ge=0, le=100_000)
    max_input_tokens: int = Field(ge=64, le=8_000)
    max_output_tokens: int = Field(ge=16, le=4_000)
    user_requests_per_minute: int = Field(ge=1, le=1_000)
    global_requests_per_minute: int = Field(ge=1, le=5_000)


class AiFeatureUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool
    model_override: str | None = Field(default=None, max_length=64)
    max_requests_per_day: int = Field(ge=1, le=100_000)
    max_output_tokens: int = Field(ge=16, le=2_000)
    cache_ttl_seconds: int = Field(ge=0, le=86_400)


class AiLimitUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject_type: str = Field(pattern="^(user|feature|global)$")
    subject_key: str = Field(min_length=1, max_length=64)
    max_requests: int = Field(ge=1, le=10_000)
    window_seconds: int = Field(ge=1, le=86_400)


class AiPublicResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    available: bool
    authoritative: bool
    feature: str
    provider: str | None = None
    model: str | None = None
    text: str | None = None
    data: dict[str, Any] | None = None
    error_code: str | None = None
    message: str | None = None
    cache_hit: bool = False
    usage: dict[str, Any] = Field(default_factory=dict)


class MatchReportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    competition_name: str = Field(min_length=1, max_length=80)
    home_club: str = Field(min_length=1, max_length=80)
    away_club: str = Field(min_length=1, max_length=80)
    score: str = Field(min_length=1, max_length=16)
    minute_notes: list[str] = Field(default_factory=list, max_length=8)
    possession_home: int | None = Field(default=None, ge=0, le=100)


class ScoutingBriefRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    player_name: str = Field(min_length=1, max_length=80)
    position: str = Field(min_length=1, max_length=16)
    age: int = Field(ge=14, le=45)
    overall: int = Field(ge=1, le=99)
    potential: int = Field(ge=1, le=99)
    notes: str | None = Field(default=None, max_length=500)


class CompetitionSummaryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    competition_name: str = Field(min_length=1, max_length=80)
    matchday: str = Field(min_length=1, max_length=40)
    table_lines: list[str] = Field(min_length=1, max_length=8)


class YouthDevelopmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    player_name: str = Field(min_length=1, max_length=80)
    age: int = Field(ge=14, le=21)
    position: str = Field(min_length=1, max_length=16)
    overall: int = Field(ge=1, le=99)
    potential: int = Field(ge=1, le=99)
    recent_minutes: int = Field(ge=0, le=5000)


class AnnouncementRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    club_name: str = Field(min_length=1, max_length=80)
    purpose: str = Field(min_length=1, max_length=80)
    facts: str = Field(min_length=1, max_length=800)


class ModerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=2000)


class MetricLine(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1, max_length=80)
    value: str = Field(min_length=1, max_length=80)


class OpsSummaryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metrics: list[MetricLine] = Field(min_length=1, max_length=12)


class MarketInsightRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observations: list[str] = Field(min_length=1, max_length=12)


class FraudSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=64)
    severity: str = Field(pattern="^(low|medium|high)$")
    count: int = Field(ge=0, le=1_000_000)


class FraudReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    signals: list[FraudSignal] = Field(min_length=1, max_length=12)


class MatchReportOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    headline: str = Field(min_length=1, max_length=160)
    summary: str = Field(min_length=1, max_length=1200)
    key_moments: list[str] = Field(max_length=5)
    advisory: str = Field(min_length=1, max_length=400)


class AdvisoryOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1, max_length=1200)
    advisory: str = Field(min_length=1, max_length=400)


class ScoutingToolOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: str = Field(pattern="^(watch|compare|develop|decline)$")
    summary: str = Field(min_length=1, max_length=800)
    reason: str = Field(min_length=1, max_length=800)


class FraudReviewOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1, max_length=800)
    risk_level: str = Field(pattern="^(low|medium|high)$")
    recommended_follow_up: str = Field(min_length=1, max_length=400)


class Classification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1, max_length=40)
    confidence: float = Field(ge=0, le=1)
    rationale: str = Field(min_length=1, max_length=400)
