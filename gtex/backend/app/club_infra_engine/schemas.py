from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field


class ClubStadiumView(BaseModel):
    id: str
    club_id: str
    name: str
    level: int
    capacity: int
    theme_key: str
    gift_retention_bonus_bps: int
    revenue_multiplier_bps: int
    prestige_bonus_bps: int


class ClubFacilityView(BaseModel):
    id: str
    club_id: str
    training_level: int
    academy_level: int
    medical_level: int
    branding_level: int
    upkeep_cost_fancoin: Decimal


class ClubSupporterTokenView(BaseModel):
    id: str
    club_id: str
    token_name: str
    token_symbol: str
    circulating_supply: int
    holder_count: int
    influence_points: int
    status: str
    description: str | None
    metadata_json: dict[str, object]


class ClubSupporterHoldingView(BaseModel):
    id: str
    club_id: str
    user_id: str
    token_balance: int
    influence_points: int
    is_founding_supporter: bool
    metadata_json: dict[str, object]


class ClubInfraDashboardResponse(BaseModel):
    club_id: str
    club_name: str
    stadium: ClubStadiumView
    facilities: ClubFacilityView
    supporter_token: ClubSupporterTokenView
    my_holding: ClubSupporterHoldingView | None = None
    projected_matchday_revenue_coin: Decimal
    projected_gift_retention_ratio: Decimal
    prestige_index: int
    insights: list[str]


class StadiumUpgradeRequest(BaseModel):
    target_level: int = Field(ge=1, le=10)


class FacilityUpgradeRequest(BaseModel):
    facility_key: str = Field(min_length=1)
    increment: int = Field(default=1, ge=1, le=5)


class SupportClubRequest(BaseModel):
    quantity: int = Field(default=1, ge=1, le=100)


class ClubInfraActionResponse(BaseModel):
    dashboard: ClubInfraDashboardResponse
    message: str
