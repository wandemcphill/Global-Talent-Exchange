from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import Field

from app.common.schemas.base import CommonSchema
from app.models.manager_marketplace import ManagerContractStatus, ManagerControlMode


class ManagerCardView(CommonSchema):
    id: str
    manager_id: str
    name: str
    rating: float = Field(ge=0.0, le=100.0)
    win_rate: float = Field(ge=0.0, le=100.0)
    preferred_style: str
    fee: Decimal = Field(ge=0)
    availability: bool


class ManagerContractView(CommonSchema):
    id: str
    manager_id: str
    club_user_id: str
    start_date: date
    end_date: date
    agreed_fee: Decimal = Field(ge=0)
    status: ManagerContractStatus


class ManagerProfileView(ManagerCardView):
    bio: str | None = None
    matches_managed: int = Field(default=0, ge=0)
    wins: int = Field(default=0, ge=0)
    losses: int = Field(default=0, ge=0)
    reputation_score: int = 0
    control_mode: ManagerControlMode
    active_contract: ManagerContractView | None = None


class ManagerHireRequest(CommonSchema):
    end_date: date | None = None


class ManagerHireResponse(CommonSchema):
    profile: ManagerProfileView
    contract: ManagerContractView


class ManagerReleaseResponse(CommonSchema):
    profile: ManagerProfileView
    contract: ManagerContractView


class ManagerLeaderboardEntryView(CommonSchema):
    rank: int = Field(ge=1)
    id: str
    manager_id: str
    name: str
    rating: float = Field(ge=0.0, le=100.0)
    win_rate: float = Field(ge=0.0, le=100.0)
    preferred_style: str
    matches_managed: int = Field(default=0, ge=0)
    reputation_score: int
    fee: Decimal = Field(ge=0)
