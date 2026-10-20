from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin, utcnow


class OwnerClubState(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "owner_club_states"

    club_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    owner_user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    club_name: Mapped[str] = mapped_column(String(120), nullable=False)
    stage: Mapped[str] = mapped_column(String(32), nullable=False, default="squad")
    manager_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    facilities_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    fans: Mapped[int] = mapped_column(Integer, nullable=False, default=1200)
    prestige: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    mentality: Mapped[str] = mapped_column(String(16), nullable=False, default="balanced")
    value_history_json: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    world_day: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_tick_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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


OWNER_CONSOLE_TABLES = (
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
    OwnerNewsroomArticle.__table__,
    OwnerScoutingWatchlist.__table__,
)
