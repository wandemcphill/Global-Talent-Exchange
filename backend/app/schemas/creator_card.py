from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import Field

from backend.app.common.schemas.base import CommonSchema


class CreatorCardAssignRequest(CommonSchema):
    player_id: str = Field(min_length=1, max_length=36)
    owner_user_id: str = Field(min_length=1, max_length=36)


class CreatorCardListingCreateRequest(CommonSchema):
    price_credits: Decimal = Field(gt=Decimal("0"))


class CreatorCardSwapRequest(CommonSchema):
    offered_card_id: str = Field(min_length=1, max_length=36)
    requested_card_id: str = Field(min_length=1, max_length=36)


class CreatorCardLoanCreateRequest(CommonSchema):
    borrower_user_id: str = Field(min_length=1, max_length=36)
    duration_days: int = Field(ge=1, le=30)
    loan_fee_credits: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))


class CreatorCardView(CommonSchema):
    creator_card_id: str
    player_id: str
    player_name: str
    owner_creator_profile_id: str
    owner_user_id: str
    owner_handle: str
    status: str
    active_loan_id: str | None = None
    metadata_json: dict[str, object] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class CreatorCardListingView(CommonSchema):
    listing_id: str
    creator_card_id: str
    seller_creator_profile_id: str
    seller_user_id: str
    seller_handle: str
    player_id: str
    player_name: str
    price_credits: Decimal
    status: str
    expires_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class CreatorCardSaleView(CommonSchema):
    sale_id: str
    creator_card_id: str
    seller_creator_profile_id: str
    buyer_creator_profile_id: str
    seller_user_id: str
    buyer_user_id: str
    player_id: str
    player_name: str
    price_credits: Decimal
    settlement_reference: str
    status: str
    created_at: datetime


class CreatorCardSwapView(CommonSchema):
    swap_id: str
    proposer_creator_profile_id: str
    counterparty_creator_profile_id: str
    proposer_card_id: str
    counterparty_card_id: str
    status: str
    created_at: datetime
    updated_at: datetime


class CreatorCardLoanView(CommonSchema):
    loan_id: str
    creator_card_id: str
    lender_creator_profile_id: str
    borrower_creator_profile_id: str
    lender_user_id: str
    borrower_user_id: str
    player_id: str
    player_name: str
    loan_fee_credits: Decimal
    status: str
    starts_at: datetime
    ends_at: datetime
    returned_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


__all__ = [
    "CreatorCardAssignRequest",
    "CreatorCardListingCreateRequest",
    "CreatorCardListingView",
    "CreatorCardLoanCreateRequest",
    "CreatorCardLoanView",
    "CreatorCardSaleView",
    "CreatorCardSwapRequest",
    "CreatorCardSwapView",
    "CreatorCardView",
]
