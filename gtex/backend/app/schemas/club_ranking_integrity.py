from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from app.common.schemas.base import CommonSchema


class ClubRankingEventView(CommonSchema):
    id: str
    event_key: str
    event_kind: str
    club_id: str
    competition_id: str
    match_id: str | None = None
    opponent_club_id: str | None = None
    result: str
    base_points: Decimal
    opponent_strength_multiplier: Decimal
    competition_size_multiplier: Decimal
    competition_tier_multiplier: Decimal
    stage_multiplier: Decimal
    anti_farm_multiplier: Decimal
    placement_bonus: Decimal
    raw_points_delta: Decimal
    final_points_delta: Decimal
    integrity_status: str
    reason: str
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ClubRankingEventsResponse(CommonSchema):
    events: tuple[ClubRankingEventView, ...]


class ClubRankingAbuseFlagView(CommonSchema):
    id: str
    flag_key: str
    club_id: str
    user_id: str | None = None
    competition_id: str | None = None
    match_id: str | None = None
    flag_type: str
    severity: str
    description: str
    status: str
    reviewed_at: datetime | None = None
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ClubRankingAbuseFlagsResponse(CommonSchema):
    flags: tuple[ClubRankingAbuseFlagView, ...]
