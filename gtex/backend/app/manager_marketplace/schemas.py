from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import Field

from app.common.schemas.base import CommonSchema
from app.models.manager_marketplace import ManagerContractStatus, ManagerControlMode


class ManagerCardView(CommonSchema):
    id: str
    manager_id: str | None = None
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
    payment_unit: str = "credit"
    payment_unit_label: str = "Fan Coin"
    settlement_status: str = "pending"
    ledger_transaction_id: str | None = None
    status: ManagerContractStatus


class ManagerProfileView(ManagerCardView):
    bio: str | None = None
    matches_managed: int = Field(default=0, ge=0)
    wins: int = Field(default=0, ge=0)
    losses: int = Field(default=0, ge=0)
    reputation_score: int = 0
    control_mode: ManagerControlMode
    gtex_ai_id: str | None = None
    tactical_style: str
    risk_tolerance: float = Field(ge=0.0, le=1.0)
    adaptability: float = Field(ge=0.0, le=1.0)
    ego_level: float = Field(ge=0.0, le=1.0)
    youth_preference: float = Field(ge=0.0, le=1.0)
    discipline_style: str
    formation_preferences: list[str] = Field(default_factory=list)
    substitution_logic: str
    tempo_control: str
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
    manager_id: str | None = None
    name: str
    rating: float = Field(ge=0.0, le=100.0)
    win_rate: float = Field(ge=0.0, le=100.0)
    preferred_style: str
    matches_managed: int = Field(default=0, ge=0)
    reputation_score: int
    fee: Decimal = Field(ge=0)


class ManagerHistoryEntryView(CommonSchema):
    id: str
    source_match_id: str
    source_match_type: str
    team_side: str
    result: str
    intensity_score: float = Field(ge=0.0, le=1.0)
    rivalry_score: float = Field(ge=0.0, le=1.0)
    opponent_manager_id: str | None = None
    opponent_name: str | None = None
    tactical_snapshot: dict[str, object] = Field(default_factory=dict)
    narrative_summary: str | None = None
    rivalry: dict[str, object] | None = None
    metadata_json: dict[str, object] = Field(default_factory=dict)
