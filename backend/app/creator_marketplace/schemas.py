from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.creator_marketplace import (
    CreatorMarketplaceCampaignPayoutBasis,
    CreatorMarketplaceCampaignPayoutType,
    CreatorMarketplaceCampaignStatus,
    CreatorMarketplaceOfferStatus,
)


class CampaignCreateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    budget: Decimal = Field(gt=Decimal("0"))
    target_formats: list[str] = Field(default_factory=list)
    target_audience: dict[str, Any] | list[str] | str = Field(default_factory=dict)
    payout_type: CreatorMarketplaceCampaignPayoutType
    payout_rate: Decimal = Field(ge=Decimal("0"))
    payout_basis: CreatorMarketplaceCampaignPayoutBasis = CreatorMarketplaceCampaignPayoutBasis.VIEWS
    platform_fee_bps: int = Field(default=1000, ge=0, le=10_000)
    status: CreatorMarketplaceCampaignStatus = CreatorMarketplaceCampaignStatus.OPEN


class CampaignView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    brand_id: str
    title: str
    budget: Decimal
    remaining_budget: Decimal
    target_formats: list[str]
    target_audience: dict[str, Any]
    payout_type: CreatorMarketplaceCampaignPayoutType
    payout_rate: Decimal
    payout_basis: CreatorMarketplaceCampaignPayoutBasis
    platform_fee_bps: int
    status: CreatorMarketplaceCampaignStatus
    offer_count: int = 0
    accepted_creators: int = 0
    my_offer_status: CreatorMarketplaceOfferStatus | None = None
    created_at: datetime
    updated_at: datetime


class CampaignApplyRequest(BaseModel):
    proposed_price: Decimal = Field(gt=Decimal("0"))
    message: str = Field(min_length=1, max_length=2000)


class CreatorOfferView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    creator_id: str
    campaign_id: str
    proposed_price: Decimal
    message: str
    status: CreatorMarketplaceOfferStatus
    match_score: float
    match_factors: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class CampaignClipSubmissionRequest(BaseModel):
    clip_id: str = Field(min_length=1, max_length=128)
    title: str | None = Field(default=None, max_length=160)
    clip_url: str | None = Field(default=None, max_length=500)
    views: int = Field(default=0, ge=0)
    engagement: int = Field(default=0, ge=0)
    conversions: int = Field(default=0, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CampaignAcceptRequest(BaseModel):
    creator_id: str = Field(min_length=1, max_length=36)
    agreed_price: Decimal | None = Field(default=None, gt=Decimal("0"))
    clip_submissions: list[CampaignClipSubmissionRequest] = Field(default_factory=list)
    brand_feedback_score: float | None = Field(default=None, ge=0.0, le=5.0)


class CampaignParticipationView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    creator_id: str
    campaign_id: str
    clips_submitted: list[dict[str, Any]] = Field(default_factory=list)
    performance_metrics: dict[str, Any] = Field(default_factory=dict)
    gross_payout: Decimal
    payout_earned: Decimal
    platform_fee_amount: Decimal
    wallet_transaction_id: str | None = None
    brand_feedback_score: Decimal | None = None
    reputation_score_snapshot: float | None = None
    created_at: datetime
    updated_at: datetime


class CampaignMarketplaceItemView(BaseModel):
    campaign: CampaignView
    match_score: float
    format_strength_score: float
    audience_match_score: float
    past_performance_score: float
    reasons: list[str] = Field(default_factory=list)
    offer_status: CreatorMarketplaceOfferStatus | None = None
    proposed_price: Decimal | None = None


class CreatorReputationView(BaseModel):
    creator_id: str
    creator_reputation_score: float
    delivery_success_score: float
    campaign_performance_score: float
    brand_feedback_score: float
    completed_campaigns: int
    updated_at: datetime


class CampaignPerformanceParticipantView(BaseModel):
    creator_id: str
    creator_handle: str
    creator_display_name: str
    clips_submitted: list[dict[str, Any]] = Field(default_factory=list)
    performance_metrics: dict[str, Any] = Field(default_factory=dict)
    gross_payout: Decimal
    payout_earned: Decimal
    platform_fee_amount: Decimal
    wallet_transaction_id: str | None = None


class CampaignPerformanceView(BaseModel):
    campaign: CampaignView
    totals: dict[str, Any] = Field(default_factory=dict)
    participants: list[CampaignPerformanceParticipantView] = Field(default_factory=list)
