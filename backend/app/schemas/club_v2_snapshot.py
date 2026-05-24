from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import Field

from app.club_growth.schemas import ClubGrowthDashboardView
from app.club_infra_engine.schemas import ClubInfraDashboardResponse
from app.club_lifecycle.schemas import ClubOperatingDashboardView
from app.common.schemas.base import CommonSchema


class ClubV2ClubView(CommonSchema):
    id: str
    club_name: str
    short_name: str | None = None
    slug: str
    owner_user_id: str
    owner_display_name: str | None = None
    lifecycle_status: str
    club_type: str
    visibility: str
    crest_asset_ref: str | None = None
    primary_color: str
    secondary_color: str
    accent_color: str
    home_venue_name: str | None = None
    country_code: str | None = None
    region_name: str | None = None
    city_name: str | None = None
    description: str | None = None
    created_at: datetime
    updated_at: datetime


class ClubV2SquadPlayerView(CommonSchema):
    player_id: str
    name: str
    short_name: str | None = None
    position: str | None = None
    position_group: str
    nationality: str | None = None
    age: int | None = None
    shirt_number: int | None = None
    market_value_credits: int = 0
    market_value_source: str | None = None
    market_value_eur: float | None = None
    rating: float | None = None
    is_regen: bool = False
    is_tradable: bool = True
    updated_at: datetime


class ClubV2SquadView(CommonSchema):
    available: Literal[True] = True
    player_count: int
    registered_player_count: int = 0
    squad_value_credits: int
    players: list[ClubV2SquadPlayerView] = Field(default_factory=list)


class ClubV2CompetitionView(CommonSchema):
    competition_id: str
    name: str
    status: str
    stage: str
    format: str
    visibility: str
    participant_status: str
    seed: int | None = None
    played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0
    goal_diff: int = 0
    points: int = 0
    entry_fee_minor: int = 0
    currency: str
    scheduled_start_at: datetime | None = None
    updated_at: datetime


class ClubV2CompetitionsView(CommonSchema):
    available: Literal[True] = True
    active_count: int
    pending_entries_count: int
    upcoming_match_count: int
    items: list[ClubV2CompetitionView] = Field(default_factory=list)


class ClubV2WalletBalanceView(CommonSchema):
    unit: str
    available_balance: Decimal
    reserved_balance: Decimal
    total_balance: Decimal


class ClubV2WalletView(CommonSchema):
    available: Literal[True] = True
    owner_user_id: str
    primary_unit: str = "credit"
    wallet_credits: int
    balances: list[ClubV2WalletBalanceView] = Field(default_factory=list)


class ClubV2RankingView(CommonSchema):
    available: Literal[True] = True
    reputation_score: int
    highest_reputation_score: int
    prestige_tier: str
    ranking_points: Decimal
    global_rank: int | None = None
    wins: int = 0
    draws: int = 0
    losses: int = 0
    trophies: int = 0
    recent_form: str = ""
    event_count: int = 0
    open_integrity_flags: int = 0


class ClubV2TransferActivityView(CommonSchema):
    id: str
    kind: str
    status: str
    player_id: str | None = None
    player_name: str | None = None
    amount_credits: Decimal | None = None
    counterparty_club_id: str | None = None
    direction: Literal["incoming", "outgoing", "neutral"]
    updated_at: datetime


class ClubV2TransfersView(CommonSchema):
    available: Literal[True] = True
    outgoing_listing_count: int = 0
    incoming_bid_count: int = 0
    outgoing_offer_count: int = 0
    incoming_offer_count: int = 0
    transfer_request_count: int = 0
    watchlist_count: int = 0
    activity: list[ClubV2TransferActivityView] = Field(default_factory=list)


class ClubV2SnapshotView(CommonSchema):
    live: Literal[True] = True
    fixture: Literal[False] = False
    demo: Literal[False] = False
    source: Literal["live"] = "live"
    club_id: str
    generated_at: datetime
    club: ClubV2ClubView
    squad: ClubV2SquadView
    competitions: ClubV2CompetitionsView
    wallet: ClubV2WalletView
    ranking: ClubV2RankingView
    facilities: ClubInfraDashboardResponse
    transfers: ClubV2TransfersView
    growth: ClubGrowthDashboardView
    lifecycle: ClubOperatingDashboardView
    metadata: dict[str, Any] = Field(default_factory=dict)
