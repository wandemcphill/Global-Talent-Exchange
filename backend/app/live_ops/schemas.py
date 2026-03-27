from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.common.schemas.base import CommonSchema
from app.live_ops.models import SeasonPassTier


class SeasonPassClaimRequest(CommonSchema):
    level: int = Field(ge=1)
    season_id: str | None = Field(default=None, min_length=1, max_length=64)


class SeasonPassClaimView(CommonSchema):
    id: str
    season_pass_id: str
    user_id: str
    level: int
    reward_payload_json: dict[str, object]
    claimed_at: datetime


class SeasonPassXpGrantView(CommonSchema):
    id: str
    source_type: str
    amount: int
    reference_key: str
    metadata_json: dict[str, object]
    created_at: datetime


class SeasonPassView(CommonSchema):
    id: str
    user_id: str
    season_id: str
    tier: SeasonPassTier
    xp: int
    level: int
    rewards_json: dict[str, object]
    claims: list[SeasonPassClaimView]
    recent_xp_grants: list[SeasonPassXpGrantView]
    created_at: datetime
    updated_at: datetime


class LiveEventView(CommonSchema):
    id: str
    name: str
    start_date: datetime
    end_date: datetime
    rules_json: dict[str, object]
    rewards_json: dict[str, object]
    active: bool
    created_at: datetime
    updated_at: datetime
