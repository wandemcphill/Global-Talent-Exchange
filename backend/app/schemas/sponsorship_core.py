from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.common.enums.sponsorship_asset_type import SponsorshipAssetType
from app.common.enums.sponsorship_status import SponsorshipStatus
from app.common.schemas.base import CommonSchema


class ClubSponsorshipPackageView(CommonSchema):
    id: str
    code: str
    name: str
    asset_type: SponsorshipAssetType
    base_amount_minor: int
    currency: str
    default_duration_months: int
    payout_schedule: str
    description: str


class ClubSponsorshipAssetView(CommonSchema):
    id: str
    club_id: str
    asset_type: SponsorshipAssetType
    slot_code: str
    contract_id: str | None = None
    is_visible: bool = True
    rendered_text: str | None = None
    asset_url: str | None = None
    moderation_required: bool = False
    moderation_status: str = "not_required"


class ClubSponsorshipPayoutView(CommonSchema):
    id: str
    contract_id: str
    due_at: datetime
    amount_minor: int
    status: str
    settled_at: datetime | None = None


class ClubSponsorshipContractView(CommonSchema):
    id: str
    club_id: str
    package_code: str
    asset_type: SponsorshipAssetType
    sponsor_name: str
    status: SponsorshipStatus
    contract_amount_minor: int
    currency: str
    duration_months: int
    payout_schedule: str
    start_at: datetime
    end_at: datetime
    moderation_required: bool = False
    moderation_status: str = "not_required"
    custom_copy: str | None = None
    custom_logo_url: str | None = None
    performance_bonus_minor: int = 0
    settled_amount_minor: int = 0
    outstanding_amount_minor: int = 0
    asset_slot_codes: tuple[str, ...] = Field(default_factory=tuple)
    payouts: tuple[ClubSponsorshipPayoutView, ...] = Field(default_factory=tuple)


__all__ = [
    "ClubSponsorshipAssetView",
    "ClubSponsorshipContractView",
    "ClubSponsorshipPackageView",
    "ClubSponsorshipPayoutView",
]
