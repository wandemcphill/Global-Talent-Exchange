from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import Field, field_validator

from app.common.schemas.base import CommonSchema

_POSITIONS = {"GK", "CB", "RB", "LB", "DM", "CM", "AM", "RW", "LW", "ST"}
_POSITION_ALIASES = {
    "CDM": "DM",
    "CAM": "AM",
    "LCB": "CB",
    "RCB": "CB",
    "LWB": "LB",
    "RWB": "RB",
    "LM": "LW",
    "RM": "RW",
    "CF": "ST",
}


class RequestSonDraftRequest(CommonSchema):
    parent_player_id: str
    selected_traits: list[str]
    requested_name: str | None = Field(default=None, max_length=160)
    requested_country_code: str | None = Field(default=None, max_length=8)
    requested_position: str | None = Field(default=None, max_length=32)

    @field_validator("selected_traits", mode="before")
    @classmethod
    def _normalize_selected_traits(cls, value: object) -> list[str]:
        if not isinstance(value, list):
            raise ValueError("selected_traits must contain exactly 3 traits")
        normalized: list[str] = []
        seen: set[str] = set()
        for item in value:
            if not isinstance(item, str):
                raise ValueError("selected_traits must contain trait names")
            trait = " ".join(item.split())
            if not trait:
                raise ValueError("selected_traits cannot contain empty traits")
            key = trait.lower()
            if key in seen:
                raise ValueError("selected_traits cannot contain duplicate traits")
            seen.add(key)
            normalized.append(trait)
        if len(normalized) != 3:
            raise ValueError("selected_traits must contain exactly 3 traits")
        return normalized

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
        trimmed = _POSITION_ALIASES.get(value.strip().upper(), value.strip().upper())
        if trimmed and trimmed not in _POSITIONS:
            raise ValueError(
                "requested_position must be one of GK, CB, RB, LB, DM, CM, AM, RW, LW, ST "
                "or a supported tactical alias"
            )
        return trimmed or None


class RequestSonPreviewRequest(RequestSonDraftRequest):
    payment_method: str = Field(default="wallet", max_length=32)

    @field_validator("payment_method")
    @classmethod
    def _normalize_preview_payment_method(cls, value: str) -> str:
        trimmed = value.strip().lower()
        if trimmed != "wallet":
            raise ValueError("payment_method must be wallet")
        return trimmed


class RequestSonCreateRequest(RequestSonDraftRequest):
    payment_method: str = Field(default="wallet", max_length=32)

    @field_validator("payment_method")
    @classmethod
    def _normalize_payment_method(cls, value: str) -> str:
        trimmed = value.strip().lower()
        if trimmed != "wallet":
            raise ValueError("payment_method must be wallet")
        return trimmed


class RegenCreationPricingView(CommonSchema):
    base_cost_coin: Decimal
    name_cost_coin: Decimal
    customization_cost_coin: Decimal


class RequestSonCountryOptionView(CommonSchema):
    code: str
    name: str
    alpha2_code: str | None = None
    alpha3_code: str | None = None
    fifa_code: str | None = None
    flag_url: str | None = None
    market_region: str | None = None
    is_default: bool = False


class RequestSonPositionOptionView(CommonSchema):
    code: str
    label: str
    aliases: list[str] = Field(default_factory=list)
    group: str | None = None
    is_default: bool = False


class RegenCreationParentPlayerView(CommonSchema):
    player_id: str
    full_name: str
    image_url: str | None = None
    portrait_url: str | None = None
    position: str | None = None
    current_rating: int | None = None
    country_code: str | None = None
    country_name: str | None = None
    nationality: str | None = None
    club_id: str | None = None
    club_name: str | None = None
    traits: list[str] = Field(default_factory=list)
    lineage: dict[str, object] = Field(default_factory=dict)
    generation: int | None = None
    dna_profile: dict[str, object] = Field(default_factory=dict)


class RequestSonOptionsView(CommonSchema):
    club_id: str
    club_name: str
    currency: str
    pricing: RegenCreationPricingView
    nationality_options: list[RequestSonCountryOptionView] = Field(default_factory=list)
    position_options: list[RequestSonPositionOptionView] = Field(default_factory=list)
    default_country_code: str | None = None
    default_position: str | None = None
    eligible_parents: list[RegenCreationParentPlayerView] = Field(default_factory=list)


class RequestSonWalletAvailabilityView(CommonSchema):
    available_balance: Decimal
    reserved_balance: Decimal
    locked_balance: Decimal = Decimal("0.0000")
    pending_withdrawal_balance: Decimal = Decimal("0.0000")
    lock_reasons: list[str] = Field(default_factory=list)
    total_balance: Decimal
    currency: str
    can_pay_with_wallet: bool
    blocked_reason: str | None = None


class RequestSonPreviewView(CommonSchema):
    club_id: str
    club_name: str
    parent: RegenCreationParentPlayerView
    selected_traits: list[str]
    projected_dna: dict[str, int] = Field(default_factory=dict)
    projected_dna_profile: dict[str, object] = Field(default_factory=dict)
    projected_ovr: int
    projected_pot: int
    parent_generation: int | None = None
    projected_generation: int
    generation_label: str
    total_cost_coin: Decimal
    wallet: RequestSonWalletAvailabilityView
    blocked_reason: str | None = None


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
    generation_number: int | None = None
    generation_label: str | None = None
    traits: list[str] = Field(default_factory=list)
    lineage: list[str] = Field(default_factory=list)
    dna_profile: dict[str, int] = Field(default_factory=dict)
    origin_story: str | None = None
    projected_value_coin: int | None = None
    rarity_tier: str | None = None


class RegenCreationWalletReservationView(CommonSchema):
    kind: str
    key: str
    status: str
    amount_coin: Decimal
    currency: str
    reference: str | None = None
    lock_reason: str | None = None
    updated_at: datetime | None = None


class RegenCreationOrderView(CommonSchema):
    id: str
    user_id: str
    club_id: str | None = None
    request_type: str
    parent_player_id: str | None = None
    selected_traits: list[str] = Field(default_factory=list)
    requested_name: str | None = None
    requested_country_code: str | None = None
    requested_position: str | None = None
    amount_coin: Decimal
    amount_minor: int | None = None
    currency: str
    payment_method: str
    payment_provider: str | None = None
    payment_reference: str | None = None
    audit_reference: str | None = None
    status: str
    generated_player_id: str | None = None
    generated_regen_profile_id: str | None = None
    payment_link: str | None = None
    mock_payment: bool = False
    wallet_reservation: RegenCreationWalletReservationView | None = None
    created_at: datetime
    updated_at: datetime
    paid_at: datetime | None = None
    generated_at: datetime | None = None
    generated_player: RegenCreationGeneratedPlayerView | None = None


class RegenCreationOrderListView(CommonSchema):
    items: list[RegenCreationOrderView] = Field(default_factory=list)
