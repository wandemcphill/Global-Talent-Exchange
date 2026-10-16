from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import ConfigDict, Field

from app.common.enums.dynasty_milestone_type import DynastyMilestoneType
from app.common.schemas.base import CommonSchema


class _ClubOrmSchema(CommonSchema):
    model_config = ConfigDict(from_attributes=True)


class ClubDynastyProgressCore(_ClubOrmSchema):
    id: str
    club_id: str
    dynasty_score: int
    dynasty_level: int
    dynasty_title: str
    seasons_completed: int
    consecutive_top_finishes: int
    participation_streak: int
    trophy_streak: int
    community_prestige_points: int
    club_loyalty_points: int
    creator_legacy_points: int
    last_season_label: str | None = None
    showcase_summary_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class ClubDynastyMilestoneCore(_ClubOrmSchema):
    id: str
    club_id: str
    milestone_type: DynastyMilestoneType
    title: str
    description: str
    required_value: int
    progress_value: int
    dynasty_points: int
    is_unlocked: bool
    unlocked_at: datetime | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
