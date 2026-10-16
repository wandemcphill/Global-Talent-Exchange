from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import Field, model_validator

from app.common.schemas.base import CommonSchema


class TicketSeatTier(StrEnum):
    REGULAR = "regular"
    PREMIUM = "premium"
    VIP = "vip"


class TicketStatus(StrEnum):
    AVAILABLE = "available"
    SOLD = "sold"
    USED = "used"


class TicketWaitlistStatus(StrEnum):
    QUEUED = "queued"
    NOTIFIED = "notified"
    FULFILLED = "fulfilled"
    CANCELLED = "cancelled"


class TicketReactionType(StrEnum):
    CHEER = "cheer"
    BOO = "boo"
    REACT = "react"


class TicketTierInventoryView(CommonSchema):
    tier: TicketSeatTier
    capacity: int = Field(ge=0)
    issued: int = Field(ge=0)
    primary_available: int = Field(ge=0)
    resale_available: int = Field(ge=0)
    current_price: Decimal = Decimal("0.0000")


class StadiumDemandView(CommonSchema):
    importance_score: Decimal = Decimal("0.0000")
    rivalry_score: Decimal = Decimal("0.0000")
    player_popularity_score: Decimal = Decimal("0.0000")
    sell_through: Decimal = Decimal("0.0000")
    demand_multiplier: Decimal = Decimal("1.0000")


class StadiumEconomyView(CommonSchema):
    gross_revenue: Decimal = Decimal("0.0000")
    resale_volume: Decimal = Decimal("0.0000")
    platform_cut_total: Decimal = Decimal("0.0000")
    club_share_total: Decimal = Decimal("0.0000")
    jackpot_pool_total: Decimal = Decimal("0.0000")
    loyalty_points_distributed: int = Field(default=0, ge=0)


class AttendeeExperienceView(CommonSchema):
    badge: str
    seat_tier: TicketSeatTier
    seat_code: str
    priority_stream: bool = True
    enhanced_crowd_audio: bool = True
    exclusive_camera_angles: list[str] = Field(default_factory=list)
    influence_multiplier: Decimal = Decimal("1.0000")
    low_latency_target_ms: int = Field(default=180, ge=50)
    fairness_guardrail: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class TicketView(CommonSchema):
    ticket_id: str
    user_id: str
    match_id: str
    seat_tier: TicketSeatTier
    seat_code: str
    price: Decimal
    original_price: Decimal
    status: TicketStatus
    resale_listing_price: Decimal | None = None
    listed_at: datetime | None = None
    sold_at: datetime | None = None
    used_at: datetime | None = None
    loyalty_points_awarded: int = Field(default=0, ge=0)
    xp_awarded: int = Field(default=0, ge=0)
    exclusive_drop_code: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TicketWaitlistView(CommonSchema):
    waitlist_id: str
    match_id: str
    seat_tier: TicketSeatTier | None = None
    status: TicketWaitlistStatus
    position: int = Field(default=1, ge=1)
    requested_at: datetime
    notified_at: datetime | None = None


class StadiumEventView(CommonSchema):
    event_id: str
    stadium_id: str
    match_id: str
    title: str
    venue_name: str
    event_type: str
    event_status: str
    capacity: int = Field(ge=0)
    tickets_sold: int = Field(ge=0)
    tickets_used: int = Field(ge=0)
    resale_ticket_count: int = Field(ge=0)
    tier_distribution: dict[str, int] = Field(default_factory=dict)
    base_price_by_tier: dict[str, Decimal] = Field(default_factory=dict)
    tier_inventory: list[TicketTierInventoryView] = Field(default_factory=list)
    early_access_starts_at: datetime | None = None
    public_sales_starts_at: datetime | None = None
    sales_close_at: datetime | None = None
    early_access_enabled: bool = False
    early_access_active: bool = False
    user_has_early_access: bool = False
    demand: StadiumDemandView
    economy: StadiumEconomyView
    experience: dict[str, Any] = Field(default_factory=dict)


class TicketEventResponse(CommonSchema):
    event: StadiumEventView
    my_ticket: TicketView | None = None
    attendee_access: AttendeeExperienceView | None = None
    waitlist: TicketWaitlistView | None = None
    available_resale_tickets: list[TicketView] = Field(default_factory=list)


class TicketBuyRequest(CommonSchema):
    match_id: str
    seat_tier: TicketSeatTier | None = None
    resale_ticket_id: str | None = None

    @model_validator(mode="after")
    def validate_request(self) -> "TicketBuyRequest":
        if self.resale_ticket_id is None and self.seat_tier is None:
            raise ValueError("seat_tier is required when buying from primary inventory.")
        return self


class TicketBuyResponse(CommonSchema):
    event: StadiumEventView
    ticket: TicketView
    attendee_access: AttendeeExperienceView
    wallet_balance: Decimal


class TicketResellRequest(CommonSchema):
    ticket_id: str
    price: Decimal = Field(gt=0)


class TicketResellResponse(CommonSchema):
    event: StadiumEventView
    ticket: TicketView
    notified_waitlist_count: int = Field(default=0, ge=0)


class TicketWaitlistRequest(CommonSchema):
    match_id: str
    seat_tier: TicketSeatTier | None = None


class TicketReactionRequest(CommonSchema):
    reaction_type: TicketReactionType | str
    intensity: float = Field(default=1.0, ge=0.25, le=2.0)


class TicketReactionResponse(CommonSchema):
    match_id: str
    reaction_type: TicketReactionType
    crowd_delta: Decimal
    influence_multiplier: Decimal
    attendee_access: AttendeeExperienceView


__all__ = [
    "AttendeeExperienceView",
    "StadiumDemandView",
    "StadiumEconomyView",
    "StadiumEventView",
    "TicketBuyRequest",
    "TicketBuyResponse",
    "TicketEventResponse",
    "TicketReactionRequest",
    "TicketReactionResponse",
    "TicketReactionType",
    "TicketResellRequest",
    "TicketResellResponse",
    "TicketSeatTier",
    "TicketStatus",
    "TicketTierInventoryView",
    "TicketView",
    "TicketWaitlistRequest",
    "TicketWaitlistStatus",
    "TicketWaitlistView",
]
