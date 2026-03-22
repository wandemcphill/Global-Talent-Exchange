from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SponsorshipPackageView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    name: str
    asset_type: str
    base_amount_minor: int
    currency: str
    default_duration_months: int
    payout_schedule: str
    description: str
    is_active: bool


class SponsorshipLeadCreateRequest(BaseModel):
    club_id: str
    package_code: str
    sponsor_name: str = Field(min_length=2, max_length=120)
    sponsor_email: str | None = None
    sponsor_company: str | None = None
    custom_amount_minor: int | None = Field(default=None, ge=0)
    duration_months: int | None = Field(default=None, ge=1, le=36)
    payout_schedule: str | None = None
    proposal_note: str = ""
    custom_copy: str | None = None
    custom_logo_url: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class SponsorshipLeadView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    contract_id: str | None
    club_id: str
    requester_user_id: str
    sponsor_name: str
    sponsor_email: str | None
    sponsor_company: str | None
    asset_type: str
    status: str
    proposal_note: str
    metadata_json: dict[str, Any]
    reviewed_by_user_id: str | None
    created_at: datetime
    updated_at: datetime


class SponsorshipContractView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    club_id: str
    package_id: str | None
    asset_type: str
    sponsor_name: str
    status: str
    contract_amount_minor: int
    currency: str
    duration_months: int
    payout_schedule: str
    start_at: datetime
    end_at: datetime
    moderation_required: bool
    moderation_status: str
    custom_copy: str | None
    custom_logo_url: str | None
    performance_bonus_minor: int
    settled_amount_minor: int
    outstanding_amount_minor: int
    created_at: datetime
    updated_at: datetime


class SponsorshipPayoutView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    contract_id: str
    due_at: datetime
    amount_minor: int
    status: str
    settled_at: datetime | None
    created_at: datetime
    updated_at: datetime


class SponsorshipReviewRequest(BaseModel):
    action: str = Field(pattern="^(approve|reject|pause|resume|complete)$")
    resolution_note: str = ""


class SponsorshipDashboardView(BaseModel):
    club_id: str
    active_contracts: int
    pending_contracts: int
    completed_contracts: int
    monthly_run_rate_minor: int
    settled_total_minor: int
    outstanding_total_minor: int
    open_leads: int
    currencies: list[str]
    headline_insights: list[str]


class SponsorshipSettlementView(BaseModel):
    contract: SponsorshipContractView
    payout: SponsorshipPayoutView
    credited_amount: Decimal
    currency: str
    destination_user_id: str


class SponsorshipPlacementRequest(BaseModel):
    home_club_id: str | None = None
    away_club_id: str | None = None
    competition_id: str | None = None
    stage_name: str | None = None
    region_code: str | None = None
    surfaces: list[str] | None = None


class SponsorshipPlacementView(BaseModel):
    surface: str
    sponsor_name: str
    campaign_code: str
    source: str
    asset_type: str | None
    creative_url: str | None
    fallback: bool
    metadata: dict[str, Any]


class SponsorshipPlacementResponse(BaseModel):
    placements: list[SponsorshipPlacementView]


class SponsorOfferCreateRequest(BaseModel):
    code: str = Field(min_length=2, max_length=64)
    offer_name: str = Field(min_length=2, max_length=120)
    sponsor_name: str = Field(min_length=2, max_length=120)
    category: str = Field(min_length=2, max_length=64)
    base_value_minor: int = Field(ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=12)
    default_duration_months: int = Field(default=3, ge=1, le=24)
    approved_surfaces_json: list[str] = Field(default_factory=list)
    creative_url: str | None = None
    category_enabled: bool = True
    is_active: bool = True
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class SponsorOfferView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    offer_name: str
    sponsor_name: str
    category: str
    base_value_minor: int
    currency: str
    default_duration_months: int
    approved_surfaces_json: list[str]
    creative_url: str | None
    category_enabled: bool
    is_active: bool
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class SponsorOfferRuleUpsertRequest(BaseModel):
    min_fan_count: int = Field(default=0, ge=0)
    min_reputation_score: int = Field(default=0, ge=0)
    min_club_valuation: Decimal = Field(default=Decimal("0.00"), ge=0)
    min_media_popularity: int = Field(default=0, ge=0)
    min_competition_count: int = Field(default=0, ge=0)
    min_rivalry_visibility: int = Field(default=0, ge=0)
    required_prestige_tier: str | None = None
    competition_allowlist_json: list[str] = Field(default_factory=list)
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


class SponsorOfferRuleView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    sponsor_offer_id: str
    min_fan_count: int
    min_reputation_score: int
    min_club_valuation: Decimal
    min_media_popularity: int
    min_competition_count: int
    min_rivalry_visibility: int
    required_prestige_tier: str | None
    competition_allowlist_json: list[str]
    metadata_json: dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ClubSponsorAssignmentRequest(BaseModel):
    club_id: str
    start_at: datetime | None = None
    duration_months: int | None = Field(default=None, ge=1, le=24)
    contract_value_minor: int | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=12)


class ClubSponsorView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    club_id: str
    sponsor_offer_id: str
    contract_id: str | None
    sponsor_name: str
    category: str
    status: str
    contract_value_minor: int
    currency: str
    duration_months: int
    start_at: datetime
    end_at: datetime
    approved_surfaces_json: list[str]
    creative_url: str | None
    analytics_json: dict[str, Any]
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class SponsorEligibilityMetricsView(BaseModel):
    club_id: str
    fan_count: int
    reputation_score: int
    prestige_tier: str
    club_valuation: float
    media_popularity: int
    competition_count: int
    rivalry_visibility: int


class SponsorEligibilityView(BaseModel):
    offer: SponsorOfferView
    club_metrics: SponsorEligibilityMetricsView
    eligible: bool
    unmet_rules: list[str]


class SponsorCategoryToggleRequest(BaseModel):
    enabled: bool


class SponsorshipOfferAnalyticsView(BaseModel):
    offer_count: int
    active_offer_count: int
    assignment_count: int
    active_sponsor_count: int
    render_event_count: int
    placements_by_surface: dict[str, int]
