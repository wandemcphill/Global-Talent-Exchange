from __future__ import annotations

from datetime import datetime
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
