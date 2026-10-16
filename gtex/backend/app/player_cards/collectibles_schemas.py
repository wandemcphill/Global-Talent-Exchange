from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class PlayerCardPackView(BaseModel):
    pack_key: str
    title: str
    description: str | None = None
    price_credits: Decimal
    cards_per_pack: int
    drop_odds_json: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class PlayerCardPackOpeningView(BaseModel):
    opening_id: str
    pack_key: str
    user_id: str
    status: str
    price_credits: Decimal
    opened_cards: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime


class PlayerCardPackOpenRequest(BaseModel):
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class PlayerCardBurnRequest(BaseModel):
    player_card_id: str
    quantity: int = Field(default=1, ge=1)
    reason: str | None = Field(default=None, max_length=120)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class PlayerCardBurnView(BaseModel):
    burn_event_id: str
    player_card_id: str
    user_id: str
    quantity: int
    reason: str | None = None
    remaining_quantity: int
    created_at: datetime


class PlayerCardUpgradeRequest(BaseModel):
    source_player_card_ids: list[str] = Field(min_length=2, max_length=10)
    target_tier_code: str = Field(min_length=2, max_length=32)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class PlayerCardUpgradeView(BaseModel):
    upgrade_event_id: str
    source_player_card_ids: list[str]
    target_player_card_id: str
    user_id: str
    burn_quantity: int
    status: str
    created_at: datetime
