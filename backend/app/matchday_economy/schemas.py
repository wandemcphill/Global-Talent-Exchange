from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class MatchdayEconomyMetricView(BaseModel):
    key: str
    label: str
    value: float
    display_value: str
    unit: str | None = None
    status: str = "ok"
    route: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MatchdayEconomySectionView(BaseModel):
    key: str
    title: str
    description: str
    feature_key: str
    route: str
    launch_state: str = "not_configured"
    enabled: bool = False
    health_status: str = "not_configured"
    metrics: list[MatchdayEconomyMetricView] = Field(default_factory=list)
    alerts: list[str] = Field(default_factory=list)


class MatchdayEconomyOverviewView(BaseModel):
    generated_at: datetime
    audience: str
    sections: list[MatchdayEconomySectionView]
    totals: dict[str, float] = Field(default_factory=dict)


class FederationSanctionResolutionRequest(BaseModel):
    note: str | None = Field(default=None, max_length=500)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class PredictionRewardSettlementRequest(BaseModel):
    fancoin_amount: Decimal = Field(default=Decimal("25.0000"), ge=0)
    max_winners: int = Field(default=3, ge=1, le=100)
    note: str | None = Field(default=None, max_length=500)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class TicketCheckInRequest(BaseModel):
    loyalty_points: int = Field(default=25, ge=0, le=10000)
    xp_awarded: int = Field(default=10, ge=0, le=10000)
    reaction_type: str | None = Field(default=None, min_length=2, max_length=32)
    crowd_delta: Decimal = Field(default=Decimal("1.0000"))
    influence_multiplier: Decimal = Field(default=Decimal("1.0000"))
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class CardListingSettlementRequest(BaseModel):
    buyer_user_id: str = Field(min_length=1, max_length=36)
    quantity: int = Field(default=1, ge=1, le=10000)
    fee_bps: int = Field(default=400, ge=0, le=10000)
    settlement_reference: str | None = Field(default=None, min_length=4, max_length=128)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class MatchdayEconomyActionView(BaseModel):
    action: str
    status: str
    resource_id: str
    message: str
    metrics: dict[str, float] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
