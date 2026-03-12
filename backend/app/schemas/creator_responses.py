from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import ConfigDict, Field

from backend.app.common.schemas.base import CommonSchema


class CreatorProfileView(CommonSchema):
    model_config = ConfigDict(from_attributes=True)

    creator_id: str
    user_id: str
    handle: str
    display_name: str
    tier: str
    status: str
    default_share_code: str | None = None
    default_competition_id: str | None = None
    revenue_share_percent: Decimal | None = None
    created_at: datetime
    updated_at: datetime


class CreatorCompetitionView(CommonSchema):
    model_config = ConfigDict(from_attributes=True)

    competition_id: str
    title: str
    linked_share_code: str | None = None
    active_participants: int = 0
    attributed_signups: int = 0
    qualified_joins: int = 0


class CreatorSummaryView(CommonSchema):
    model_config = ConfigDict(from_attributes=True)

    profile: CreatorProfileView
    total_signups: int = 0
    qualified_joins: int = 0
    active_participants: int = 0
    pending_rewards: int = 0
    approved_rewards: int = 0
    featured_competitions: list[CreatorCompetitionView] = Field(default_factory=list)
