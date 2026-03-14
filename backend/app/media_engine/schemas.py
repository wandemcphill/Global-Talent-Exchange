from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field


class MatchViewCreateRequest(BaseModel):
    match_key: str = Field(min_length=2)
    competition_key: str | None = None
    watch_seconds: int = Field(default=30, ge=1, le=7200)
    premium_unlocked: bool = False


class PremiumVideoPurchaseRequest(BaseModel):
    match_key: str = Field(min_length=2)
    competition_key: str | None = None


class RevenueSnapshotCreateRequest(BaseModel):
    match_key: str = Field(min_length=2)
    competition_key: str | None = None
    home_club_id: str | None = None
    away_club_id: str | None = None


class MatchViewView(BaseModel):
    id: str
    user_id: str
    match_key: str
    competition_key: str | None
    view_date_key: str
    watch_seconds: int
    premium_unlocked: bool
    metadata_json: dict[str, object]


class PremiumVideoPurchaseView(BaseModel):
    id: str
    user_id: str
    match_key: str
    competition_key: str | None
    price_coin: Decimal
    price_fancoin_equivalent: Decimal
    metadata_json: dict[str, object]


class MatchRevenueSnapshotView(BaseModel):
    id: str
    match_key: str
    competition_key: str | None
    home_club_id: str | None
    away_club_id: str | None
    total_views: int
    premium_purchases: int
    total_revenue_coin: Decimal
    home_club_share_coin: Decimal
    away_club_share_coin: Decimal
    metadata_json: dict[str, object]
