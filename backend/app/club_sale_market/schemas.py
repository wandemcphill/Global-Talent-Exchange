from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import Field

from app.common.schemas.base import CommonSchema


class ClubSaleValuationBreakdownView(CommonSchema):
    first_team_value: Decimal
    reserve_squad_value: Decimal
    u19_squad_value: Decimal
    academy_value: Decimal
    stadium_value: Decimal
    paid_enhancements_value: Decimal
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class ClubSaleValuationView(CommonSchema):
    club_id: str
    club_name: str
    currency: str
    system_valuation: Decimal
    system_valuation_minor: int
    breakdown: ClubSaleValuationBreakdownView
    last_refreshed_at: datetime | None = None


class ClubSaleListingCreateRequest(CommonSchema):
    asking_price: Decimal = Field(gt=0)
    visibility: str = Field(default="public", min_length=3, max_length=24)
    note: str | None = Field(default=None, max_length=2_000)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class ClubSaleListingUpdateRequest(CommonSchema):
    asking_price: Decimal = Field(gt=0)
    visibility: str = Field(default="public", min_length=3, max_length=24)
    note: str | None = Field(default=None, max_length=2_000)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class ClubSaleListingCancelRequest(CommonSchema):
    reason: str | None = Field(default=None, max_length=1_000)


class ClubSaleListingSummaryView(CommonSchema):
    listing_id: str
    club_id: str
    club_name: str
    seller_user_id: str
    status: str
    visibility: str
    currency: str
    asking_price: Decimal
    system_valuation: Decimal
    system_valuation_minor: int
    valuation_last_refreshed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ClubSaleListingDetailView(ClubSaleListingSummaryView):
    valuation_breakdown: ClubSaleValuationBreakdownView
    note: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class ClubSaleListingCollectionView(CommonSchema):
    total: int
    items: list[ClubSaleListingSummaryView] = Field(default_factory=list)


class ClubSaleInquiryCreateRequest(CommonSchema):
    message: str = Field(min_length=4, max_length=4_000)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class ClubSaleInquiryRespondRequest(CommonSchema):
    response_message: str = Field(min_length=2, max_length=4_000)
    close_thread: bool = True
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class ClubSaleInquiryView(CommonSchema):
    inquiry_id: str
    club_id: str
    listing_id: str | None = None
    seller_user_id: str
    buyer_user_id: str
    status: str
    message: str
    response_message: str | None = None
    responded_by_user_id: str | None = None
    responded_at: datetime | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class ClubSaleInquiryCollectionView(CommonSchema):
    total: int
    items: list[ClubSaleInquiryView] = Field(default_factory=list)


class ClubSaleOfferCreateRequest(CommonSchema):
    offer_price: Decimal = Field(gt=0)
    inquiry_id: str | None = None
    message: str | None = Field(default=None, max_length=4_000)
    expires_at: datetime | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class ClubSaleOfferCounterRequest(CommonSchema):
    offer_price: Decimal = Field(gt=0)
    message: str | None = Field(default=None, max_length=4_000)
    expires_at: datetime | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class ClubSaleOfferRespondRequest(CommonSchema):
    message: str | None = Field(default=None, max_length=4_000)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class ClubSaleOfferView(CommonSchema):
    offer_id: str
    club_id: str
    listing_id: str | None = None
    inquiry_id: str | None = None
    parent_offer_id: str | None = None
    seller_user_id: str
    buyer_user_id: str
    proposer_user_id: str
    counterparty_user_id: str
    offer_type: str
    status: str
    currency: str
    offer_price: Decimal
    message: str | None = None
    responded_message: str | None = None
    responded_by_user_id: str | None = None
    responded_at: datetime | None = None
    accepted_at: datetime | None = None
    rejected_at: datetime | None = None
    expires_at: datetime | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class ClubSaleOfferCollectionView(CommonSchema):
    total: int
    items: list[ClubSaleOfferView] = Field(default_factory=list)


class ClubSaleTransferExecuteRequest(CommonSchema):
    offer_id: str = Field(min_length=1)
    executed_sale_price: Decimal = Field(gt=0)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class ClubSaleOwnershipTransitionView(CommonSchema):
    previous_owner_user_id: str | None = None
    new_owner_user_id: str | None = None
    ownership_lineage_index: int
    shareholder_count_preserved: int
    shareholder_rights_preserved: bool


class ClubSaleTransferExecutionView(CommonSchema):
    transfer_id: str
    club_id: str
    listing_id: str | None = None
    offer_id: str
    seller_user_id: str
    buyer_user_id: str
    currency: str
    executed_sale_price: Decimal
    platform_fee_amount: Decimal
    seller_net_amount: Decimal
    platform_fee_bps: int
    status: str
    settlement_reference: str
    ledger_transaction_id: str | None = None
    story_feed_item_id: str | None = None
    calendar_event_id: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    ownership_transition: ClubSaleOwnershipTransitionView | None = None
    created_at: datetime


class ClubSaleAuditEventView(CommonSchema):
    id: str
    club_id: str
    listing_id: str | None = None
    inquiry_id: str | None = None
    offer_id: str | None = None
    transfer_id: str | None = None
    actor_user_id: str | None = None
    action: str
    status_from: str | None = None
    status_to: str | None = None
    payload_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class ClubSaleOwnershipHistoryEventView(CommonSchema):
    transfer_id: str
    seller_user_id: str
    buyer_user_id: str
    executed_sale_price: Decimal
    created_at: datetime
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class ClubSaleOwnershipHistoryView(CommonSchema):
    current_owner_user_id: str
    transfer_count: int
    ownership_eras: int
    shareholder_count: int
    active_governance_proposal_count: int
    last_transfer_id: str | None = None
    last_transfer_at: datetime | None = None
    previous_owner_user_ids: list[str] = Field(default_factory=list)
    recent_transfers: list[ClubSaleOwnershipHistoryEventView] = Field(default_factory=list)


class ClubSaleDynastySnapshotView(CommonSchema):
    dynasty_score: int
    dynasty_level: int
    dynasty_title: str
    seasons_completed: int
    last_season_label: str | None = None
    ownership_eras: int
    shareholder_continuity_transfers: int
    showcase_summary_json: dict[str, Any] = Field(default_factory=dict)


class ClubSaleHistoryView(CommonSchema):
    club_id: str
    listings: list[ClubSaleListingSummaryView] = Field(default_factory=list)
    offers: list[ClubSaleOfferView] = Field(default_factory=list)
    transfers: list[ClubSaleTransferExecutionView] = Field(default_factory=list)
    audit_events: list[ClubSaleAuditEventView] = Field(default_factory=list)
    ownership_history: ClubSaleOwnershipHistoryView
    dynasty_snapshot: ClubSaleDynastySnapshotView
