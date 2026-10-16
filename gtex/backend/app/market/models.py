from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ListingType(StrEnum):
    TRANSFER = "transfer"
    SWAP = "swap"
    HYBRID = "hybrid"


class ListingStatus(StrEnum):
    OPEN = "open"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    EXPIRED = "expired"


class OfferStatus(StrEnum):
    PENDING = "pending"
    COUNTERED = "countered"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class TradeIntentDirection(StrEnum):
    BUY = "buy"
    SELL = "sell"
    SWAP = "swap"


class TradeIntentStatus(StrEnum):
    ACTIVE = "active"
    WITHDRAWN = "withdrawn"
    FULFILLED = "fulfilled"


@dataclass(frozen=True, slots=True)
class Listing:
    listing_id: str
    asset_id: str
    seller_user_id: str
    listing_type: ListingType
    ask_price: int | None
    desired_asset_ids: tuple[str, ...]
    note: str | None
    status: ListingStatus
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class Offer:
    offer_id: str
    asset_id: str
    listing_id: str | None
    seller_user_id: str
    buyer_user_id: str
    proposer_user_id: str
    recipient_user_id: str
    cash_amount: int
    offered_asset_ids: tuple[str, ...]
    note: str | None
    status: OfferStatus
    parent_offer_id: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class TradeIntent:
    intent_id: str
    user_id: str
    asset_id: str
    direction: TradeIntentDirection
    price_floor: int | None
    price_ceiling: int | None
    offered_asset_ids: tuple[str, ...]
    note: str | None
    status: TradeIntentStatus
    created_at: datetime
    updated_at: datetime
