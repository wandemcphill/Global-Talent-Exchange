from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class IntegrityScoreResponse(BaseModel):
    id: str
    user_id: str
    score: Decimal
    risk_level: str
    incident_count: int
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class IntegrityIncidentResponse(BaseModel):
    id: str
    user_id: str
    incident_type: str
    severity: str
    title: str
    description: str
    score_delta: Decimal
    detected_by: str
    status: str
    metadata_json: dict[str, Any]
    resolution_note: str | None
    created_at: datetime
    updated_at: datetime


class IntegrityScanRequest(BaseModel):
    repeated_gift_threshold: int = Field(default=3, ge=2, le=20)
    reward_cluster_threshold: int = Field(default=3, ge=2, le=20)
    lookback_limit: int = Field(default=200, ge=20, le=1000)


class IntegrityScanResponse(BaseModel):
    created_incidents: list[IntegrityIncidentResponse]
    scanned_gifts: int
    scanned_rewards: int


class IntegrityResolveRequest(BaseModel):
    resolution_note: str = Field(min_length=2, max_length=2000)
