from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class StaffContractStatus(StrEnum):
    OFFERED = "offered"
    ACTIVE = "active"
    TERMINATED = "terminated"
    EXPIRED = "expired"


class AcademyProspectStatus(StrEnum):
    DISCOVERED = "discovered"
    TRIAL = "trial"
    ACADEMY = "academy"
    CONTRACT_OFFERED = "contract_offered"
    CONTRACT_REJECTED = "contract_rejected"
    YOUTH_SIGNED = "youth_signed"
    PROMOTED_TO_SENIOR = "promoted_to_senior"
    RELEASED = "released"
    POACHED = "poached"


class AcademyContractOfferStatus(StrEnum):
    OFFERED = "offered"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class StaffProfileView(BaseModel):
    id: str
    display_name: str
    staff_type: str
    rarity: str
    skills: list[str] = Field(default_factory=list)
    salary_minor: int
    commission_bps: int
    rating: int
    active: bool
    metadata: dict[str, Any] = Field(default_factory=dict)


class StaffContractView(BaseModel):
    id: str
    club_id: str
    staff_profile: StaffProfileView
    status: StaffContractStatus
    salary_minor: int
    commission_bps: int
    duration_days: int
    role_scope: str
    exclusive: bool
    started_at: datetime | None = None
    ends_at: datetime | None = None
    accepted_at: datetime | None = None
    terminated_at: datetime | None = None
    updated_at: datetime


class StaffOfferRequest(BaseModel):
    salary_minor: int | None = Field(default=None, ge=0)
    commission_bps: int | None = Field(default=None, ge=0, le=10000)
    duration_days: int = Field(default=90, ge=7, le=1095)
    role_scope: str = Field(default="club", min_length=1, max_length=64)
    exclusive: bool = True


class AcademyProfileView(BaseModel):
    id: str
    club_id: str
    level: int
    investment_minor: int
    generation_cooldown_until: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime


class AcademyProspectView(BaseModel):
    id: str
    club_id: str
    display_name: str
    nationality: str | None = None
    position: str
    age: int
    personality: dict[str, Any] = Field(default_factory=dict)
    current_ability: int
    potential: int
    portrait_asset_ref: str | None = None
    senior_player_id: str | None = None
    status: AcademyProspectStatus
    metadata: dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime


class AcademyContractOfferView(BaseModel):
    id: str
    club_id: str
    prospect_id: str
    status: AcademyContractOfferStatus
    wage_minor: int
    duration_months: int
    response_reason: str | None = None
    updated_at: datetime


class AcademyGenerateProspectsRequest(BaseModel):
    count: int = Field(default=3, ge=1, le=6)
    seed: str | None = Field(default=None, max_length=128)


class AcademyContractOfferRequest(BaseModel):
    wage_minor: int = Field(default=0, ge=0)
    duration_months: int = Field(default=24, ge=6, le=84)


class AcademyContractResponseRequest(BaseModel):
    accepted: bool
    reason: str | None = Field(default=None, max_length=1000)


class AcademyGenerationRunView(BaseModel):
    id: str
    club_id: str
    run_seed: str
    prospects_created: int
    status: str
    created_at: datetime


class SponsorshipClubSummaryView(BaseModel):
    active_contracts: int = 0
    pending_contracts: int = 0
    settled_payout_minor: int = 0
    outstanding_payout_minor: int = 0
    open_leads: int = 0


class ClubGrowthDashboardView(BaseModel):
    club_id: str
    staff_market: list[StaffProfileView] = Field(default_factory=list)
    staff_contracts: list[StaffContractView] = Field(default_factory=list)
    staff_effects: dict[str, int] = Field(default_factory=dict)
    academy_profile: AcademyProfileView
    academy_prospects: list[AcademyProspectView] = Field(default_factory=list)
    academy_runs: list[AcademyGenerationRunView] = Field(default_factory=list)
    sponsorship: SponsorshipClubSummaryView = Field(default_factory=SponsorshipClubSummaryView)
    updated_at: datetime
