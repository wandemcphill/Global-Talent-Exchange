from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class DailyChallengeView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    challenge_key: str
    title: str
    description: str
    reward_amount: Decimal
    reward_unit: str
    claim_limit_per_day: int
    sort_order: int
    status: str
    metadata_json: dict[str, object] = Field(default_factory=dict)


class DailyChallengeClaimView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    challenge_id: str
    claim_date: date
    reward_amount: Decimal
    reward_unit: str
    reward_settlement_id: str | None = None
    metadata_json: dict[str, object] = Field(default_factory=dict)
    claimed_at: datetime


class DailyChallengeListResponse(BaseModel):
    feature_enabled: bool
    challenges: list[DailyChallengeView]


class DailyChallengeMeResponse(BaseModel):
    feature_enabled: bool
    claims_today: list[DailyChallengeClaimView]
    available_challenge_keys: list[str]


class DailyChallengeClaimResponse(BaseModel):
    challenge: DailyChallengeView
    claim: DailyChallengeClaimView
    reward_summary: str
