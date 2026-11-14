from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin, utcnow


class OwnerClubState(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "owner_club_states"

    club_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    owner_user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    club_name: Mapped[str] = mapped_column(String(120), nullable=False)
    stage: Mapped[str] = mapped_column(String(32), nullable=False, default="squad")
    division_level: Mapped[str] = mapped_column(
        String(32), nullable=False, default="foundation", server_default="foundation"
    )
    division_season_ids: Mapped[list[Any]] = mapped_column(
        JSON, nullable=False, default=list, server_default=text("'[]'")
    )
    manager_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    facilities_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    fans: Mapped[int] = mapped_column(Integer, nullable=False, default=1200)
    prestige: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    mentality: Mapped[str] = mapped_column(String(16), nullable=False, default="balanced")
    value_history_json: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    world_day: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_tick_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Last GTEX world-calendar date simulated by the autonomous owner tick. Null
    # means this state has not yet been anchored to the shared clock calendar.
    last_world_tick_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    academy_intake_sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now()
    )


class OwnerSquadPlayer(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "owner_squad_players"

    club_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    player_ref: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    position: Mapped[str] = mapped_column(String(32), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False, default=24)
    rating: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    potential: Mapped[int] = mapped_column(Integer, nullable=False, default=65)
    value_coin: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False, default=Decimal("0"))
    morale: Mapped[int] = mapped_column(Integer, nullable=False, default=70)
    minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    injured_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_regen: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    personality_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    growth_log_json: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    acquired_via: Mapped[str] = mapped_column(String(32), nullable=False, default="market")
    acquired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class OwnerInboxItem(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "owner_inbox_items"

    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    club_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    priority: Mapped[str] = mapped_column(String(12), nullable=False, default="normal")
    sender: Mapped[str] = mapped_column(String(120), nullable=False, default="GTEX")
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    what: Mapped[str] = mapped_column(Text, nullable=False)
    why: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_generated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    actions_json: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    save_context_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    category: Mapped[str] = mapped_column(String(40), nullable=False, default="requests", index=True)
    is_decision: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open")
    resolution: Mapped[str | None] = mapped_column(String(40), nullable=True)
    outcome_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class LedgerEvent(UUIDPrimaryKeyMixin, Base):
    """Canonical money journal. Rows are insert-only; corrections are new reversal rows."""

    __tablename__ = "owner_ledger_events"

    event_type: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    source_account: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    destination_account: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    club_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    currency: Mapped[str] = mapped_column(String(16), nullable=False)
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    platform_fee: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False, default=Decimal("0"))
    net_amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    balance_class: Mapped[str] = mapped_column(String(24), nullable=False, default="earned")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="completed")
    related_object_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    related_object_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    memo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class OwnerDepositIntent(UUIDPrimaryKeyMixin, Base):
    """One Paystack (or sibling) checkout. (provider, reference) is the credit lock."""

    __tablename__ = "owner_deposit_intents"
    __table_args__ = (UniqueConstraint("provider", "reference", name="uq_owner_deposit_intents_provider_reference"),)

    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    reference: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    requested_amount_ngn: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    credited_amount_kobo: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ledger_event_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now()
    )


class OwnerWithdrawal(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "owner_withdrawals"

    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    amount_coin: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    amount_ngn: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    bank_name: Mapped[str] = mapped_column(String(120), nullable=False)
    account_number: Mapped[str] = mapped_column(String(20), nullable=False)
    account_name: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending_review")
    checks_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    ledger_event_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    review_note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class IntegrityFlag(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "owner_integrity_flags"

    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    club_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    flag_type: Mapped[str] = mapped_column(String(48), nullable=False)
    severity: Mapped[str] = mapped_column(String(12), nullable=False, default="medium")
    detail: Mapped[str] = mapped_column(Text, nullable=False)
    score_impact: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open")
    related_object_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class RelatedPartyTransfer(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "owner_related_party_transfers"

    owner_user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    from_club_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    to_club_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    player_name: Mapped[str] = mapped_column(String(160), nullable=False)
    player_ref: Mapped[str | None] = mapped_column(String(64), nullable=True)
    fair_value: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    fee: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class OwnerCompetition(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "owner_competitions"

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    host_type: Mapped[str] = mapped_column(String(12), nullable=False, default="gtex")
    host_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    format: Mapped[str] = mapped_column(String(16), nullable=False, default="league")
    tier: Mapped[str] = mapped_column(String(40), nullable=False, default="Open")
    entry_fee: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False, default=Decimal("0"))
    sponsored_pool: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False, default=Decimal("0"))
    platform_fee_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=1000)
    max_clubs: Mapped[int] = mapped_column(Integer, nullable=False, default=8)
    allow_same_owner: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    prize_sensitive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    invite_code: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open")
    current_round: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_rounds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class OwnerCompetitionEntry(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "owner_competition_entries"

    competition_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    club_id: Mapped[str] = mapped_column(String(64), nullable=False)
    club_name: Mapped[str] = mapped_column(String(120), nullable=False)
    owner_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    is_ai: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    strength: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    played: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    won: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    drawn: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lost: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    goals_for: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    goals_against: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    eliminated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    final_position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class OwnerMatch(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "owner_matches"

    competition_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    home_club_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    away_club_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    home_name: Mapped[str] = mapped_column(String(120), nullable=False)
    away_name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="scheduled")
    home_goals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_goals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    events_json: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    narrative_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    played_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def attendance(self) -> int | None:
        val = (self.narrative_json or {}).get("attendance")
        return int(val) if val is not None else None

    @property
    def stadium_capacity(self) -> int | None:
        val = (self.narrative_json or {}).get("stadium_capacity")
        return int(val) if val is not None else None

    @property
    def tv_revenue(self) -> int | None:
        narrative = self.narrative_json or {}
        val = narrative.get("tv_revenue")
        if val is None:
            val = narrative.get("tv_revenue_gtex")
        if val is None:
            val = narrative.get("home_tv_revenue_gtex")
        if val is None:
            val = narrative.get("away_tv_revenue_gtex")
        return int(val) if val is not None else None


class OwnerSponsorDeal(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "owner_sponsor_deals"

    club_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    sponsor_name: Mapped[str] = mapped_column(String(120), nullable=False)
    slot: Mapped[str] = mapped_column(String(40), nullable=False)
    per_match_gross: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    player_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    matches_remaining: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class SupportUnitHolding(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "owner_support_units"

    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    club_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    units: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class OwnerBroadcastEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "owner_broadcast_events"

    save_context_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    club_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    club_name: Mapped[str] = mapped_column(String(120), nullable=False)
    club_crest_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    owner_user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    owner_display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    event_type: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    item_name: Mapped[str] = mapped_column(String(160), nullable=False)
    item_model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    item_image_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    player_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    player_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    player_portrait_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    verified_price_gtex: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    currency: Mapped[str] = mapped_column(String(16), nullable=False, default="GTEX")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", index=True)
    headline: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    ledger_event_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True, index=True)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class OwnerShowroomAsset(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "owner_showroom_assets"

    club_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    owner_user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    catalog_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    custom_name: Mapped[str] = mapped_column(String(160), nullable=False)
    category: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    purchase_price_gtex: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    gifted_to_player_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    gifted_to_player_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", index=True)
    ledger_event_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class OwnerNewsroomArticle(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "owner_newsroom_articles"

    save_context_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    club_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    visibility: Mapped[str] = mapped_column(String(16), nullable=False, default="global", index=True)
    category: Mapped[str] = mapped_column(String(40), nullable=False, default="editorial", index=True)
    headline: Mapped[str] = mapped_column(String(220), nullable=False)
    subheadline: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    hero_image_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    club_crest_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    player_portrait_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    established_facts_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    editorial_narration: Mapped[str] = mapped_column(Text, nullable=False)
    grounding_report_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    verified_price_gtex: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    source_event_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="published", index=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class OwnerScoutingWatchlist(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "owner_scouting_watchlists"

    club_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    save_context_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    player_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    player_name: Mapped[str] = mapped_column(String(120), nullable=False)
    position: Mapped[str] = mapped_column(String(16), nullable=False, default="MID")
    age: Mapped[int] = mapped_column(Integer, nullable=False, default=18)
    current_rating: Mapped[int] = mapped_column(Integer, nullable=False, default=65)
    potential_rating: Mapped[int] = mapped_column(Integer, nullable=False, default=80)
    estimated_value_gtex: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=Decimal("100"))
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="medium")
    scout_notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    recommendation: Mapped[str] = mapped_column(String(120), nullable=False, default="Monitor")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class OwnerClubEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "owner_club_events"

    club_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="routine")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active", index=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, default="system")
    source_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    participants_json: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    world_day: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True)
    consequences_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True, index=True)
    actions_json: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_action: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )


class OwnerClubRelationship(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "owner_club_relationships"
    __table_args__ = (UniqueConstraint("club_id", "pairing_key", name="uq_owner_club_relationships_club_pairing"),)

    club_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    pairing_key: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    participant_a_type: Mapped[str] = mapped_column(String(32), nullable=False)
    participant_a_id: Mapped[str] = mapped_column(String(64), nullable=False)
    participant_a_name: Mapped[str] = mapped_column(String(160), nullable=False)
    participant_b_type: Mapped[str] = mapped_column(String(32), nullable=False)
    participant_b_id: Mapped[str] = mapped_column(String(64), nullable=False)
    participant_b_name: Mapped[str] = mapped_column(String(160), nullable=False)
    trust: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    respect: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    affinity: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    tension: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    alignment: Mapped[int] = mapped_column(Integer, nullable=False, default=60, server_default="60")
    influence: Mapped[int] = mapped_column(Integer, nullable=False, default=50, server_default="50")
    loyalty: Mapped[int] = mapped_column(Integer, nullable=False, default=60, server_default="60")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )


class OwnerClubRelationshipHistory(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "owner_club_relationship_history"

    relationship_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    club_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    world_day: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    source_event_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    delta_trust: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    delta_respect: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    delta_affinity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    delta_tension: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    delta_alignment: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    delta_influence: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    delta_loyalty: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class OwnerClubDirective(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "owner_club_directives"

    club_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    department: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    directive_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    instruction: Mapped[str] = mapped_column(Text, nullable=False)
    target_scope: Mapped[str | None] = mapped_column(String(64), nullable=True)
    target_scope_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active", index=True)
    issued_day: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True)
    deadline_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    acknowledged_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    acknowledgement_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    consequences_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )


class ClubDelegationPolicy(UUIDPrimaryKeyMixin, Base):
    """Authoritative club responsibility and owner delegation policy."""

    __tablename__ = "owner_club_delegation_policies"

    club_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    owner_user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    mode: Mapped[str] = mapped_column(String(32), nullable=False, default="balanced")
    is_suspended: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    suspension_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    financial_thresholds_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    activity_assignments_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    reserved_decisions_json: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    temporary_overrides_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )


class ClubDelegatedDecision(UUIDPrimaryKeyMixin, Base):
    """Authoritative ledger of delegated decisions, approvals, and escalations."""

    __tablename__ = "owner_club_delegated_decisions"

    club_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    owner_user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    activity_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    domain: Mapped[str] = mapped_column(String(32), nullable=False, default="sporting")
    proposed_by_role: Mapped[str] = mapped_column(String(40), nullable=False)
    proposed_by_staff_name: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    financial_amount_gtex: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    requires_owner_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    approval_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending_approval", index=True)
    execution_status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending_execution")
    decided_by_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    decision_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    outcome_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    staff_competence_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    staff_impact_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    ecosystem_event_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ClubDelegatedDecisionAuditLog(UUIDPrimaryKeyMixin, Base):
    """Immutable append-only audit trail for all delegated decision lifecycle transitions."""

    __tablename__ = "owner_club_decision_audit_logs"

    decision_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    club_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    actor_id: Mapped[str] = mapped_column(String(36), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    previous_status: Mapped[str | None] = mapped_column(String(24), nullable=True)
    new_status: Mapped[str] = mapped_column(String(24), nullable=False)
    decision_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class OwnerClubConversation(UUIDPrimaryKeyMixin, Base):
    """Durable normalized conversation thread for private Owner Inbox communications."""

    __tablename__ = "owner_club_conversations"
    __table_args__ = (
        UniqueConstraint("club_id", "thread_key", name="uq_owner_club_conversations_club_thread_key"),
        Index("ix_owner_club_conversations_club_channel", "club_id", "channel_type"),
    )

    club_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    owner_user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    channel_type: Mapped[str] = mapped_column(String(24), nullable=False, default="direct", server_default="direct")
    thread_key: Mapped[str] = mapped_column(String(120), nullable=False)
    participant_type: Mapped[str] = mapped_column(String(24), nullable=False, default="staff", server_default="staff")
    participant_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    participant_name: Mapped[str] = mapped_column(String(120), nullable=False)
    participant_role: Mapped[str] = mapped_column(String(80), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(180), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_message_seq: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class OwnerClubMessage(UUIDPrimaryKeyMixin, Base):
    """Durable normalized message record inside an Owner Inbox conversation or room."""

    __tablename__ = "owner_club_messages"
    __table_args__ = (
        Index("ix_owner_club_messages_conv_seq", "conversation_id", "seq"),
        Index("ix_owner_club_messages_club_read", "club_id", "is_read"),
    )

    conversation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("owner_club_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    club_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    seq: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    sender_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    sender_type: Mapped[str] = mapped_column(String(24), nullable=False, default="staff", server_default="staff")
    sender_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sender_name: Mapped[str] = mapped_column(String(120), nullable=False)
    sender_role: Mapped[str] = mapped_column(String(80), nullable=False)
    topic: Mapped[str | None] = mapped_column(String(120), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="staff_reply", server_default="staff_reply")
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="normal", server_default="normal")
    linked_entity_type: Mapped[str | None] = mapped_column(String(48), nullable=True)
    linked_entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    linked_event_key: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    action_payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class OwnerClubMeeting(UUIDPrimaryKeyMixin, Base):
    """Durable scheduled or completed club boardroom/staff/squad meeting."""

    __tablename__ = "owner_club_meetings"
    __table_args__ = (Index("ix_owner_club_meetings_club_created", "club_id", "created_at"),)

    club_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    owner_user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    agenda: Mapped[str] = mapped_column(Text, nullable=False, default="")
    meeting_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="boardroom", server_default="boardroom"
    )
    world_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="scheduled", server_default="scheduled")
    attendees_json: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    minutes_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    decisions_json: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    created_by_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class OwnerClubAnnouncement(UUIDPrimaryKeyMixin, Base):
    """Durable internal or official club announcement issued by an authorized club owner."""

    __tablename__ = "owner_club_announcements"
    __table_args__ = (Index("ix_owner_club_announcements_club_created", "club_id", "created_at"),)

    club_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    owner_user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    audience: Mapped[str] = mapped_column(String(32), nullable=False, default="all_club", server_default="all_club")
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="normal", server_default="normal")
    published_world_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    published_by_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


OWNER_CONSOLE_TABLES = (
    ClubDelegationPolicy.__table__,
    ClubDelegatedDecision.__table__,
    ClubDelegatedDecisionAuditLog.__table__,
    OwnerClubState.__table__,
    OwnerSquadPlayer.__table__,
    OwnerInboxItem.__table__,
    LedgerEvent.__table__,
    OwnerWithdrawal.__table__,
    IntegrityFlag.__table__,
    RelatedPartyTransfer.__table__,
    OwnerCompetition.__table__,
    OwnerCompetitionEntry.__table__,
    OwnerMatch.__table__,
    OwnerSponsorDeal.__table__,
    SupportUnitHolding.__table__,
    OwnerBroadcastEvent.__table__,
    OwnerShowroomAsset.__table__,
    OwnerNewsroomArticle.__table__,
    OwnerScoutingWatchlist.__table__,
    OwnerClubEvent.__table__,
    OwnerClubRelationship.__table__,
    OwnerClubRelationshipHistory.__table__,
    OwnerClubDirective.__table__,
    OwnerClubConversation.__table__,
    OwnerClubMessage.__table__,
    OwnerClubMeeting.__table__,
    OwnerClubAnnouncement.__table__,
)
