from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.avatar import PlayerAvatarView


class PlayerCardMarketplaceListingView(BaseModel):
    listing_id: str
    listing_type: str
    player_card_id: str
    player_id: str
    player_name: str
    club_name: str | None
    position: str | None
    average_rating: float | None
    latest_value_credits: float | None = None
    avatar: PlayerAvatarView
    tier_code: str
    tier_name: str
    rarity_rank: int
    edition_code: str
    listing_owner_user_id: str
    status: str
    availability: str
    is_negotiable: bool
    asset_origin: str
    is_regen_newgen: bool
    is_creator_linked: bool
    quantity: int | None = None
    available_quantity: int | None = None
    sale_price_credits: Decimal | None = None
    loan_fee_credits: Decimal | None = None
    loan_duration_days: int | None = None
    requested_player_card_id: str | None = None
    requested_player_id: str | None = None
    requested_filters_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    expires_at: datetime | None = None


class PlayerCardMarketplaceSearchResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[PlayerCardMarketplaceListingView]


class PlayerCardMarketplaceSaleListingCreateRequest(BaseModel):
    player_card_id: str = Field(min_length=2)
    quantity: int = Field(default=1, ge=1)
    price_per_card_credits: Decimal = Field(gt=0)
    is_negotiable: bool = False
    expires_at: datetime | None = None


class PlayerCardMarketplaceSaleExecutionView(BaseModel):
    sale_id: str
    listing_id: str | None
    player_card_id: str
    seller_user_id: str
    buyer_user_id: str
    quantity: int
    price_per_card_credits: Decimal
    gross_credits: Decimal
    fee_credits: Decimal
    seller_net_credits: Decimal
    status: str
    settlement_reference: str
    created_at: datetime


class PlayerCardMarketplaceSalePurchaseRequest(BaseModel):
    quantity: int | None = Field(default=None, ge=1)


class PlayerCardMarketplaceLoanListingCreateRequest(BaseModel):
    player_card_id: str = Field(min_length=2)
    total_slots: int = Field(default=1, ge=1, le=25)
    duration_days: int = Field(default=7, ge=1, le=30)
    loan_fee_credits: Decimal = Field(default=Decimal("0.0000"), ge=0)
    is_negotiable: bool = False
    usage_restrictions_json: dict[str, Any] = Field(default_factory=dict)
    borrower_rights_json: dict[str, Any] = Field(default_factory=dict)
    lender_restrictions_json: dict[str, Any] = Field(default_factory=dict)
    terms_json: dict[str, Any] = Field(default_factory=dict)
    expires_at: datetime | None = None


class PlayerCardMarketplaceLoanListingView(BaseModel):
    listing_id: str
    player_card_id: str
    player_id: str
    player_name: str
    club_name: str | None
    position: str | None
    average_rating: float | None
    avatar: PlayerAvatarView
    tier_code: str
    tier_name: str
    rarity_rank: int
    edition_code: str
    owner_user_id: str
    total_slots: int
    available_slots: int
    duration_days: int
    loan_fee_credits: Decimal
    currency: str
    status: str
    is_negotiable: bool
    asset_origin: str
    is_regen_newgen: bool
    is_creator_linked: bool
    usage_restrictions_json: dict[str, Any] = Field(default_factory=dict)
    borrower_rights_json: dict[str, Any] = Field(default_factory=dict)
    lender_restrictions_json: dict[str, Any] = Field(default_factory=dict)
    terms_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    expires_at: datetime | None = None


class PlayerCardMarketplaceLoanNegotiationCreateRequest(BaseModel):
    proposed_duration_days: int = Field(ge=1, le=30)
    proposed_loan_fee_credits: Decimal = Field(default=Decimal("0.0000"), ge=0)
    requested_terms_json: dict[str, Any] = Field(default_factory=dict)
    note: str | None = Field(default=None, max_length=1_000)


class PlayerCardMarketplaceLoanNegotiationView(BaseModel):
    negotiation_id: str
    listing_id: str
    player_card_id: str
    owner_user_id: str
    borrower_user_id: str
    proposer_user_id: str
    counterparty_user_id: str
    proposed_duration_days: int
    proposed_loan_fee_credits: Decimal
    status: str
    note: str | None
    requested_terms_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    responded_at: datetime | None = None
    expires_at: datetime | None = None


class PlayerCardMarketplaceLoanContractView(BaseModel):
    loan_contract_id: str
    listing_id: str
    accepted_negotiation_id: str | None
    player_card_id: str
    player_id: str
    player_name: str
    club_name: str | None
    position: str | None
    average_rating: float | None
    avatar: PlayerAvatarView
    tier_code: str
    tier_name: str
    rarity_rank: int
    edition_code: str
    owner_user_id: str
    borrower_user_id: str
    status: str
    asset_origin: str
    is_regen_newgen: bool
    is_creator_linked: bool
    currency: str
    loan_duration_days: int
    requested_loan_fee_credits: Decimal
    effective_loan_fee_credits: Decimal
    platform_fee_credits: Decimal
    lender_net_credits: Decimal
    platform_fee_bps: int
    fee_floor_applied: bool
    accepted_at: datetime | None = None
    settled_at: datetime | None = None
    borrowed_at: datetime | None = None
    due_at: datetime | None = None
    returned_at: datetime | None = None
    settlement_reference: str | None = None
    accepted_terms_json: dict[str, Any] = Field(default_factory=dict)
    borrower_rights_json: dict[str, Any] = Field(default_factory=dict)
    lender_rights_json: dict[str, Any] = Field(default_factory=dict)
    lender_restrictions_json: dict[str, Any] = Field(default_factory=dict)
    usage_snapshot_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class PlayerCardMarketplaceLoanContractListResponse(BaseModel):
    total: int
    items: list[PlayerCardMarketplaceLoanContractView]


class PlayerCardMarketplaceSwapListingCreateRequest(BaseModel):
    player_card_id: str = Field(min_length=2)
    requested_player_card_id: str | None = None
    requested_player_id: str | None = None
    desired_filters_json: dict[str, Any] = Field(default_factory=dict)
    terms_json: dict[str, Any] = Field(default_factory=dict)
    is_negotiable: bool = False
    expires_at: datetime | None = None


class PlayerCardMarketplaceSwapListingView(BaseModel):
    listing_id: str
    player_card_id: str
    player_id: str
    player_name: str
    club_name: str | None
    position: str | None
    average_rating: float | None
    avatar: PlayerAvatarView
    tier_code: str
    tier_name: str
    rarity_rank: int
    edition_code: str
    owner_user_id: str
    status: str
    is_negotiable: bool
    asset_origin: str
    is_regen_newgen: bool
    is_creator_linked: bool
    requested_player_card_id: str | None = None
    requested_player_id: str | None = None
    desired_filters_json: dict[str, Any] = Field(default_factory=dict)
    terms_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    expires_at: datetime | None = None


class PlayerCardMarketplaceSwapExecuteRequest(BaseModel):
    counterparty_player_card_id: str = Field(min_length=2)


class PlayerCardMarketplaceSwapExecutionView(BaseModel):
    swap_execution_id: str
    listing_id: str
    owner_user_id: str
    counterparty_user_id: str
    owner_player_card_id: str
    counterparty_player_card_id: str
    status: str
    settled_at: datetime
    snapshot_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
