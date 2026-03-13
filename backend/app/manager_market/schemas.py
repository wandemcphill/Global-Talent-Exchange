from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ManagerCatalogItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    manager_id: str
    display_name: str
    rarity: str
    mentality: str
    tactics: list[str]
    traits: list[str]
    substitution_tendency: str
    philosophy_summary: str
    club_associations: list[str] = Field(default_factory=list)
    supply_total: int
    supply_available: int


class ManagerCatalogPage(BaseModel):
    items: list[ManagerCatalogItem]
    total: int


class ManagerAssetView(BaseModel):
    asset_id: str
    manager_id: str
    display_name: str
    rarity: str
    tactics: list[str]
    traits: list[str]
    mentality: str
    slot: str | None = None
    acquired_at: datetime


class TeamManagersView(BaseModel):
    main_manager: ManagerAssetView | None = None
    academy_manager: ManagerAssetView | None = None
    bench: list[ManagerAssetView] = Field(default_factory=list)
    total_owned: int = 0


class RecruitManagerRequest(BaseModel):
    manager_id: str
    slot: Literal["main", "academy", "bench"] = "bench"


class AssignManagerRequest(BaseModel):
    asset_id: str
    slot: Literal["main", "academy"]


class TradeListingRequest(BaseModel):
    asset_id: str
    asking_price_credits: Decimal = Field(gt=0)


class SwapTradeRequest(BaseModel):
    proposer_asset_id: str
    requested_asset_id: str
    cash_adjustment_credits: Decimal = Field(default=Decimal("0"), ge=0)


class ManagerListingView(BaseModel):
    listing_id: str
    asset_id: str
    manager_id: str
    display_name: str
    seller_user_id: str
    seller_name: str
    asking_price_credits: Decimal
    created_at: datetime


class ManagerTradeResultView(BaseModel):
    trade_id: str
    mode: str
    fee_credits: Decimal
    seller_net_credits: Decimal
    gross_credits: Decimal
    created_at: datetime
    settlement_reference: str | None = None
    immediate_withdrawal_eligible: bool = True
    settlement_status: str = "settled"


class ManagerRecommendationView(BaseModel):
    manager: str | None
    summary: str
    recommended_positions: list[str] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)
    selected_tactic: str | None = None
    style_fit_score: int = 0
    squad_strength_score: int = 0
    depth_score: int = 0
    rationale: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)


class ManagerComparisonView(BaseModel):
    left_manager_id: str
    right_manager_id: str
    left_name: str
    right_name: str
    tactic_overlap: list[str] = Field(default_factory=list)
    trait_overlap: list[str] = Field(default_factory=list)
    style_fit_left: int = 0
    style_fit_right: int = 0
    verdict: str


class ManagerHistoryEntryView(BaseModel):
    trade_id: str
    manager_id: str
    display_name: str
    mode: str
    gross_credits: Decimal
    fee_credits: Decimal
    seller_net_credits: Decimal
    settlement_status: str
    settlement_reference: str | None = None
    created_at: datetime


class CompetitionScheduleMatchView(BaseModel):
    seed: int
    slot: int
    home_label: str
    away_label: str


class CompetitionOrchestrationView(BaseModel):
    code: str
    can_run: bool
    entrants: int
    minimum_viable_participants: int
    qualified_regions: list[str] = Field(default_factory=list)
    fallback_used: bool = False
    fallback_reason: str | None = None
    bracket_size: int = 0
    byes: int = 0
    auto_seeded: bool = True
    schedule: list[CompetitionScheduleMatchView] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class ManagerSupplyUpdateRequest(BaseModel):
    supply_total: int = Field(ge=0)
    reason: str = Field(min_length=3, max_length=240)


class CompetitionAdminView(BaseModel):
    code: str
    label: str
    enabled: bool
    minimum_viable_participants: int
    geo_locked_regions: list[str]
    allow_fallback_fill: bool
    fallback_source_regions: list[str]
    schedule_mode: str = "adaptive"
    auto_seed_enabled: bool = True


class CompetitionAdminUpdateRequest(BaseModel):
    enabled: bool | None = None
    minimum_viable_participants: int | None = Field(default=None, ge=2)
    geo_locked_regions: list[str] | None = None
    allow_fallback_fill: bool | None = None
    fallback_source_regions: list[str] | None = None


class ManagerAuditEventView(BaseModel):
    event_id: str
    event_type: str
    actor_user_id: str
    actor_email: str
    created_at: datetime
    payload: dict[str, str | int | float | bool | None | list[str]] | dict[str, object]


class CompetitionRuntimeView(BaseModel):
    code: str
    participants: int
    can_run: bool
    minimum_viable_participants: int
    reason: str
    fallback_used: bool = False
    qualified_regions: list[str] = Field(default_factory=list)
    adaptive_pool_size: int = 0
    bracket_size: int = 0
    byes: int = 0
    schedule_preview: list[CompetitionScheduleMatchView] = Field(default_factory=list)



class ManagerFilterMetadataView(BaseModel):
    tactics: list[str] = Field(default_factory=list)
    traits: list[str] = Field(default_factory=list)
    mentalities: list[str] = Field(default_factory=list)
    rarities: list[str] = Field(default_factory=list)
