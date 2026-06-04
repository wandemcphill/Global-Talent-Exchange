from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import Field, model_validator

from app.common.schemas.base import CommonSchema
from app.models.wallet import LedgerUnit


CreatorContractState = Literal["confirmed", "empty", "blocked", "degraded"]
CreatorCampaignStatus = Literal["draft", "active", "review", "approved", "rejected", "settled"]
ClipModerationStatus = Literal["pending", "approved", "flagged", "rejected"]
WalletTransactionType = Literal["credit", "debit", "hold", "release"]
CreatorWithdrawalMethod = Literal["bank_transfer", "korapay"]


class CreatorContractMeta(CommonSchema):
    state: CreatorContractState = "confirmed"
    status: CreatorContractState = "confirmed"
    blocked_reason: str | None = None
    degraded_reason: str | None = None
    gap_reasons: tuple[str, ...] = ()
    audit_reference: str | None = None


class CreatorProfileContract(CommonSchema):
    id: str
    display_name: str
    verification_status: str
    total_reach: int | None = None
    engagement_rate: Decimal | None = None
    content_count: int | None = None
    joined_at: datetime


class CreatorProfileContractResponse(CreatorContractMeta):
    profile: CreatorProfileContract | None = None


class ClipRefContract(CommonSchema):
    id: str
    title: str | None = None


class CampaignPerformanceContract(CommonSchema):
    views: int | None = None
    engagement: int | None = None
    conversions: int | None = None
    engagement_rate: Decimal | None = None
    payout_earned: Decimal | None = None


class CampaignContract(CommonSchema):
    id: str
    title: str
    sponsor: str | None = None
    brief: str | None = None
    budget: Decimal | None = None
    currency: str | None = None
    status: CreatorCampaignStatus
    source: str
    source_status: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    clips: tuple[ClipRefContract, ...] = ()
    performance: CampaignPerformanceContract | None = None
    created_at: datetime
    updated_at: datetime
    audit_reference: str | None = None
    degraded_reason: str | None = None
    gap_reasons: tuple[str, ...] = ()


class CreatorCampaignsContractResponse(CreatorContractMeta):
    campaigns: tuple[CampaignContract, ...] = ()


class CreateCampaignContractRequest(CommonSchema):
    title: str = Field(min_length=2, max_length=160)
    sponsor: str | None = Field(default=None, max_length=160)
    brief: str | None = Field(default=None, max_length=2000)
    budget: Decimal | None = Field(default=None, gt=Decimal("0"))
    currency: str | None = Field(default="credit", max_length=16)
    status: CreatorCampaignStatus = "draft"
    start_date: datetime | None = None
    end_date: datetime | None = None

    @model_validator(mode="after")
    def validate_dates(self) -> "CreateCampaignContractRequest":
        if self.start_date is not None and self.end_date is not None and self.start_date > self.end_date:
            raise ValueError("start_date cannot be after end_date")
        return self


class CampaignStatusUpdateRequest(CommonSchema):
    status: CreatorCampaignStatus
    reason: str | None = Field(default=None, max_length=255)


class CampaignContractResponse(CreatorContractMeta):
    campaign: CampaignContract | None = None


class SponsoredClipContract(CommonSchema):
    id: str
    campaign_id: str | None = None
    title: str | None = None
    url: str | None = None
    thumbnail_url: str | None = None
    status: ClipModerationStatus | None = None
    moderation_note: str | None = None
    published_at: datetime | None = None
    view_count: int | None = None
    engagement_rate: Decimal | None = None
    source: str
    state: CreatorContractState = "confirmed"
    blocked_reason: str | None = None
    degraded_reason: str | None = None
    audit_reference: str | None = None
    gap_reasons: tuple[str, ...] = ()


class SponsoredClipsContractResponse(CreatorContractMeta):
    clips: tuple[SponsoredClipContract, ...] = ()


class SubmitClipContractRequest(CommonSchema):
    campaign_id: str = Field(min_length=1, max_length=36)
    title: str = Field(min_length=1, max_length=160)
    url: str = Field(min_length=4, max_length=500)
    thumbnail_url: str | None = Field(default=None, max_length=500)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SponsoredClipContractResponse(CreatorContractMeta):
    clip: SponsoredClipContract | None = None


class WalletBalanceContract(CommonSchema):
    available: Decimal | None = None
    reserved: Decimal | None = None
    currency: str
    last_synced_at: datetime | None = None


class WalletTransactionContract(CommonSchema):
    id: str
    type: WalletTransactionType
    amount: Decimal
    currency: str
    reference: str | None = None
    created_at: datetime
    status: str


class CreatorWalletContractResponse(CreatorContractMeta):
    balance: WalletBalanceContract | None = None
    pending_settlements: int | None = None
    recent_transactions: tuple[WalletTransactionContract, ...] = ()
    withdrawal_available: bool = False


class CreatorSettlementContract(CommonSchema):
    id: str
    campaign_id: str | None = None
    amount: Decimal | None = None
    currency: str
    status: str
    eta: datetime | None = None
    wallet_transaction_id: str | None = None
    created_at: datetime
    audit_reference: str | None = None
    degraded_reason: str | None = None


class CreatorSettlementsContractResponse(CreatorContractMeta):
    settlements: tuple[CreatorSettlementContract, ...] = ()


class ModerationInboxItemContract(CommonSchema):
    id: str
    item_type: str
    item_id: str
    status: str
    moderation_status: ClipModerationStatus | None = None
    reason: str | None = None
    note: str | None = None
    created_at: datetime | None = None
    source: str


class CreatorModerationInboxContractResponse(CreatorContractMeta):
    items: tuple[ModerationInboxItemContract, ...] = ()


class CreatorWithdrawalRequest(CommonSchema):
    amount: Decimal = Field(gt=Decimal("0"))
    method: CreatorWithdrawalMethod = "bank_transfer"
    destination_reference: str = Field(min_length=4, max_length=255)
    unit: LedgerUnit = LedgerUnit.CREDIT
    notes: str | None = Field(default=None, max_length=255)


class CreatorWithdrawalContractResponse(CreatorContractMeta):
    withdrawal_id: str | None = None
    payout_request_id: str | None = None
    amount: Decimal | None = None
    fee_amount: Decimal | None = None
    total_debit: Decimal | None = None
    currency: str | None = None
    method: CreatorWithdrawalMethod | None = None
    action_state: Literal["completed", "blocked"] = "completed"


__all__ = [
    "CampaignContract",
    "CampaignContractResponse",
    "CampaignStatusUpdateRequest",
    "CreateCampaignContractRequest",
    "CreatorCampaignsContractResponse",
    "CreatorModerationInboxContractResponse",
    "CreatorProfileContractResponse",
    "CreatorSettlementContract",
    "CreatorSettlementsContractResponse",
    "CreatorWalletContractResponse",
    "CreatorWithdrawalContractResponse",
    "CreatorWithdrawalRequest",
    "SponsoredClipContractResponse",
    "SponsoredClipsContractResponse",
    "SubmitClipContractRequest",
]
