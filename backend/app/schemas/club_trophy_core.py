from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import ConfigDict, Field

from backend.app.common.enums.trophy_type import TrophyType
from backend.app.common.schemas.base import CommonSchema


class _ClubOrmSchema(CommonSchema):
    model_config = ConfigDict(from_attributes=True)


class ClubTrophyCore(_ClubOrmSchema):
    id: str
    club_id: str
    trophy_type: TrophyType
    trophy_name: str
    competition_source: str
    competition_id: str | None = None
    season_label: str
    campaign_label: str | None = None
    prestige_weight: int
    awarded_at: datetime
    is_featured: bool
    display_order: int
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class ClubTrophyCabinetCore(_ClubOrmSchema):
    id: str
    club_id: str
    featured_trophy_id: str | None = None
    display_theme_code: str | None = None
    showcase_order_json: list[str] = Field(default_factory=list)
    total_trophies: int
    last_awarded_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
