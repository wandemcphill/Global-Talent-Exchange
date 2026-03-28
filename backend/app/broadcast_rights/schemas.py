from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import Field

from app.common.schemas.base import CommonSchema


class BroadcastRightOwnerView(CommonSchema):
    owner_id: str
    owner_name: str | None = None
    owner_type: str


class BroadcastRightView(CommonSchema):
    id: str
    competition_id: str
    owner: BroadcastRightOwnerView
    acquisition_price: Decimal
    revenue_share_percentage: Decimal
    exclusivity: bool
    start_date: date
    end_date: date
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    revenue_generated: Decimal = Decimal("0.0000")
    viewers: int = 0


class BroadcastRightsAuctionBidView(CommonSchema):
    id: str
    bidder_user_id: str
    bidder_name: str | None = None
    amount: Decimal
    status: str
    created_at: datetime


class BroadcastRightsAuctionView(CommonSchema):
    id: str
    competition_id: str
    seller_owner_id: str
    reserve_price: Decimal
    revenue_share_percentage: Decimal
    exclusivity: bool
    start_date: date
    end_date: date
    starts_at: datetime
    ends_at: datetime
    status: str
    bids: list[BroadcastRightsAuctionBidView] = Field(default_factory=list)


class BroadcastRightsSummaryView(CommonSchema):
    competition_id: str
    competition_name: str | None = None
    owner: BroadcastRightOwnerView | None = None
    revenue_generated: Decimal
    viewers: int
    active_rights: list[BroadcastRightView] = Field(default_factory=list)
    auctions: list[BroadcastRightsAuctionView] = Field(default_factory=list)


class BroadcastRightsAcquireRequest(CommonSchema):
    acquisition_price: Decimal = Field(gt=0)
    revenue_share_percentage: Decimal = Field(gt=0, le=95)
    exclusivity: bool = True
    start_date: date
    end_date: date
    viewing_fee_coin: Decimal = Field(default=Decimal("2.5000"), ge=0)
    premium_features: dict[str, bool] = Field(default_factory=dict)
    ad_inventory: list[dict[str, Any]] = Field(default_factory=list)
    sponsored_overlays: list[dict[str, Any]] = Field(default_factory=list)


class BroadcastRightsAuctionCreateRequest(CommonSchema):
    reserve_price: Decimal = Field(gt=0)
    revenue_share_percentage: Decimal = Field(gt=0, le=95)
    exclusivity: bool = True
    start_date: date
    end_date: date
    ends_at: datetime
    viewing_fee_coin: Decimal = Field(default=Decimal("2.5000"), ge=0)
    premium_features: dict[str, bool] = Field(default_factory=dict)
    ad_inventory: list[dict[str, Any]] = Field(default_factory=list)
    sponsored_overlays: list[dict[str, Any]] = Field(default_factory=list)


class BroadcastRightsBidCreateRequest(CommonSchema):
    amount: Decimal = Field(gt=0)


class BroadcastAccessGrantRequest(CommonSchema):
    user_id: str = Field(min_length=1, max_length=36)
    expires_at: datetime | None = None


class BroadcastMatchAccessView(CommonSchema):
    match_id: str
    competition_id: str | None = None
    has_access: bool
    access_source: str | None = None
    requires_payment: bool = False
    viewing_fee_coin: Decimal = Decimal("0.0000")
    exclusive: bool = False
    rights_owner_id: str | None = None
    premium_features: dict[str, bool] = Field(default_factory=dict)
    sponsored_overlays: list[dict[str, Any]] = Field(default_factory=list)
    stadium_ads: list[dict[str, Any]] = Field(default_factory=list)


class BroadcastRevenueDistributionView(CommonSchema):
    match_id: str
    competition_id: str | None = None
    total_revenue: Decimal
    rights_holder_share: Decimal
    platform_share: Decimal
    participating_club_share: Decimal
    recipients: list[dict[str, Any]] = Field(default_factory=list)


class BroadcastJobRunView(CommonSchema):
    processed_matches: int = 0
    expired_rights: int = 0
    relisted_auctions: int = 0
    settled_auctions: int = 0
