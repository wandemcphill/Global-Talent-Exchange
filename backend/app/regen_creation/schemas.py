from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import Field, field_validator

from app.common.schemas.base import CommonSchema

_POSITIONS = {"GK", "CB", "RB", "LB", "DM", "CM", "AM", "RW", "LW", "ST"}


class RequestSonCreateRequest(CommonSchema):
    parent_player_id: str
    requested_name: str | None = Field(default=None, max_length=160)
    requested_country_code: str | None = Field(default=None, max_length=8)
    requested_position: str | None = Field(default=None, max_length=32)
    payment_method: str = Field(default="wallet", max_length=32)

    @field_validator("requested_name")
    @classmethod
    def _normalize_requested_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = " ".join(value.split())
        return trimmed or None

    @field_validator("requested_country_code")
    @classmethod
    def _normalize_country_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip().upper()
        return trimmed or None

    @field_validator("requested_position")
    @classmethod
    def _normalize_position(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip().upper()
        if trimmed and trimmed not in _POSITIONS:
            raise ValueError("requested_position must be one of GK, CB, RB, LB, DM, CM, AM, RW, LW, ST")
        return trimmed or None

    @field_validator("payment_method")
    @classmethod
    def _normalize_payment_method(cls, value: str) -> str:
        trimmed = value.strip().lower()
        if trimmed not in {"wallet", "korapay"}:
            raise ValueError("payment_method must be wallet or korapay")
        return trimmed


class RegenCreationPricingView(CommonSchema):
    base_cost_coin: Decimal
    name_cost_coin: Decimal
    customization_cost_coin: Decimal


class RegenCreationParentPlayerView(CommonSchema):
    player_id: str
    full_name: str
    image_url: str | None = None
    portrait_url: str | None = None
    position: str | None = None
    country_code: str | None = None
    country_name: str | None = None
    club_id: str | None = None
    club_name: str | None = None


class RequestSonOptionsView(CommonSchema):
    club_id: str
    club_name: str
    currency: str
    pricing: RegenCreationPricingView
    eligible_parents: list[RegenCreationParentPlayerView] = Field(default_factory=list)


class RegenCreationGeneratedPlayerView(CommonSchema):
    player_id: str
    regen_profile_id: str
    full_name: str
    image_url: str | None = None
    portrait_url: str | None = None
    age: int
    position: str
    country_code: str | None = None
    country_name: str | None = None
    club_id: str | None = None
    club_name: str | None = None
    current_rating: int
    potential_rating: int
    card_id: str | None = None


class RegenCreationOrderView(CommonSchema):
    id: str
    user_id: str
    club_id: str | None = None
    request_type: str
    parent_player_id: str | None = None
    requested_name: str | None = None
    requested_country_code: str | None = None
    requested_position: str | None = None
    amount_coin: Decimal
    amount_minor: int | None = None
    currency: str
    payment_method: str
    payment_provider: str | None = None
    payment_reference: str | None = None
    status: str
    generated_player_id: str | None = None
    generated_regen_profile_id: str | None = None
    payment_link: str | None = None
    mock_payment: bool = False
    created_at: datetime
    updated_at: datetime
    paid_at: datetime | None = None
    generated_at: datetime | None = None
    generated_player: RegenCreationGeneratedPlayerView | None = None


class RegenCreationOrderListView(CommonSchema):
    items: list[RegenCreationOrderView] = Field(default_factory=list)
