from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class PlayerCardTierView(BaseModel):
    tier_id: str
    code: str
    name: str
    rarity_rank: int
    max_supply: int | None
    supply_multiplier: float
    base_mint_price_credits: float
    color_hex: str | None
    is_active: bool


class PlayerCardView(BaseModel):
    card_id: str
    player_id: str
    tier: PlayerCardTierView | None
    edition_code: str
    display_name: str
    season_label: str | None
    card_variant: str
    supply_total: int
    supply_available: int
    is_active: bool


class PlayerCardEffectView(BaseModel):
    effect_id: str
    player_card_id: str
    effect_type: str
    effect_value: float
    applied_at: datetime | None
    expires_at: datetime | None
    source: str | None
    metadata_json: dict[str, Any]


class PlayerCardFormBuffView(BaseModel):
    buff_id: str
    player_card_id: str
    buff_type: str
    buff_value: float
    started_at: datetime | None
    expires_at: datetime | None
    source: str | None
    metadata_json: dict[str, Any]


class PlayerCardMomentumView(BaseModel):
    momentum_id: str
    player_id: str
    last_trade_price_credits: float | None
    momentum_7d_pct: float
    momentum_30d_pct: float
    trend_direction: str
    metadata_json: dict[str, Any]


class PlayerStatsSnapshotView(BaseModel):
    snapshot_id: str
    player_id: str
    as_of: datetime
    competition_id: str | None
    season_id: str | None
    source_type: str
    stats_json: dict[str, Any]


class PlayerMarketValueSnapshotView(BaseModel):
    snapshot_id: str
    player_id: str
    as_of: datetime
    last_trade_price_credits: float | None
    avg_trade_price_credits: float | None
    volume_24h: int
    listing_floor_price_credits: float | None
    listing_count: int
    high_24h_price_credits: float | None
    low_24h_price_credits: float | None
    metadata_json: dict[str, Any]


class PlayerCardPlayerSummaryView(BaseModel):
    player_id: str
    player_name: str
    position: str | None
    nationality_code: str | None
    current_club_name: str | None
    card_supply_total: int
    latest_value_credits: float | None


class PlayerCardPlayerDetailView(BaseModel):
    player_id: str
    player_name: str
    position: str | None
    nationality_code: str | None
    current_club_name: str | None
    aliases: list[str]
    monikers: list[str]
    cards: list[PlayerCardView]
    effects: list[PlayerCardEffectView]
    form_buffs: list[PlayerCardFormBuffView]
    momentum: PlayerCardMomentumView | None
    latest_stats_snapshot: PlayerStatsSnapshotView | None
    latest_market_snapshot: PlayerMarketValueSnapshotView | None


class PlayerCardHoldingView(BaseModel):
    holding_id: str
    player_card_id: str
    player_id: str
    player_name: str
    tier_code: str
    tier_name: str
    edition_code: str
    quantity_total: int
    quantity_reserved: int
    quantity_available: int
    last_acquired_at: datetime | None


class PlayerCardListingView(BaseModel):
    listing_id: str
    player_card_id: str
    player_id: str
    player_name: str
    tier_code: str
    tier_name: str
    edition_code: str
    seller_user_id: str
    quantity: int
    price_per_card_credits: float
    status: str
    created_at: datetime


class PlayerCardSaleView(BaseModel):
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


class PlayerCardWatchlistView(BaseModel):
    id: str
    player_id: str
    player_card_id: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class PlayerCardListingCreateRequest(BaseModel):
    player_card_id: str = Field(min_length=2)
    quantity: int = Field(default=1, ge=1)
    price_per_card_credits: Decimal = Field(gt=0)


class PlayerCardListingBuyRequest(BaseModel):
    quantity: int | None = Field(default=None, ge=1)


class PlayerCardWatchlistCreateRequest(BaseModel):
    player_id: str = Field(min_length=2)
    player_card_id: str | None = None
    notes: str | None = None
