from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import Field

from app.common.schemas.base import CommonSchema


class OwnershipGroupClubView(CommonSchema):
    club_id: str
    club_name: str | None = None
    owner_user_id: str
    added_at: datetime | None = None


class OwnershipGroupEventView(CommonSchema):
    id: str
    event_type: str
    headline: str
    impact_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class OwnershipGroupView(CommonSchema):
    id: str
    owner_user_id: str
    name: str
    clubs: list[OwnershipGroupClubView] = Field(default_factory=list)
    total_value: Decimal = Decimal("0.0000")
    reputation: float = 0.0
    budget_pool: Decimal = Decimal("0.0000")
    philosophy: str | None = None
    global_brand_strength: float = 0.0
    scouting_network_boost: float = 0.0
    branding_boost: float = 0.0
    shared_budget_enabled: bool = True
    budget_allocations: dict[str, Decimal] = Field(default_factory=dict)
    recent_events: list[OwnershipGroupEventView] = Field(default_factory=list)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class OwnershipGroupCreateRequest(CommonSchema):
    name: str = Field(min_length=2, max_length=160)
    club_ids: list[str] = Field(default_factory=list)
    budget_pool: Decimal = Field(default=Decimal("0.0000"), ge=0)
    philosophy: str | None = Field(default=None, max_length=120)
    shared_budget_enabled: bool = True


class OwnershipGroupAddClubRequest(CommonSchema):
    club_id: str = Field(min_length=1, max_length=36)


class OwnershipGroupBudgetAllocateRequest(CommonSchema):
    club_id: str = Field(min_length=1, max_length=36)
    amount: Decimal = Field(gt=0)


class OwnershipGroupBudgetTransferRequest(CommonSchema):
    source_club_id: str = Field(min_length=1, max_length=36)
    target_club_id: str = Field(min_length=1, max_length=36)
    amount: Decimal = Field(gt=0)


class OwnershipGroupValidationView(CommonSchema):
    blocked: bool = False
    reason: str | None = None
    group_id: str | None = None
    fair_value: Decimal | None = None
    min_allowed: Decimal | None = None
    max_allowed: Decimal | None = None
    recent_internal_transfer_count: int = 0
