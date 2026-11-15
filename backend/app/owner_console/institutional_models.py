from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Integer, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def _uuid() -> str:
    return str(uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class OwnerSupporterProfile(Base):
    """Persistent club-wide supporter identity, sentiment memory, and matchday atmosphere state."""

    __tablename__ = "owner_supporter_profiles"
    __table_args__ = (UniqueConstraint("club_id", name="uq_owner_supporter_profiles_club_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    club_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    owner_user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    supporter_culture_label: Mapped[str] = mapped_column(String(120), default="Community & Youth Traditionalists")
    overall_sentiment: Mapped[int] = mapped_column(Integer, default=65)
    confidence_in_owner: Mapped[int] = mapped_column(Integer, default=65)
    confidence_in_manager: Mapped[int] = mapped_column(Integer, default=68)
    loyalty_index: Mapped[int] = mapped_column(Integer, default=72)
    matchday_enthusiasm: Mapped[int] = mapped_column(Integer, default=66)
    accumulated_frustration: Mapped[int] = mapped_column(Integer, default=0)
    consecutive_disappointments: Mapped[int] = mapped_column(Integer, default=0)
    consecutive_victories: Mapped[int] = mapped_column(Integer, default=0)
    ticket_price_tier: Mapped[str] = mapped_column(String(24), default="standard")
    matchday_experience_rating: Mapped[int] = mapped_column(Integer, default=62)
    active_protest_stage: Mapped[str] = mapped_column(String(32), default="none")
    active_campaign_headline: Mapped[str | None] = mapped_column(String(240), nullable=True)
    attendance_modifier_pct: Mapped[int] = mapped_column(Integer, default=0)
    owner_credibility_score: Mapped[int] = mapped_column(Integer, default=72)
    expectations_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    atmosphere_profile_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    last_reconciled_world_day: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class OwnerSupporterSegment(Base):
    """Persistent supporter segment with distinct expectations, priorities, and sentiment memory."""

    __tablename__ = "owner_supporter_segments"
    __table_args__ = (UniqueConstraint("club_id", "segment_key", name="uq_owner_supporter_segments_club_segment"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    club_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    segment_key: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    segment_name: Mapped[str] = mapped_column(String(80), nullable=False)
    population_share_pct: Mapped[int] = mapped_column(Integer, default=16)
    member_count: Mapped[int] = mapped_column(Integer, default=200)
    sentiment: Mapped[int] = mapped_column(Integer, default=65)
    loyalty: Mapped[int] = mapped_column(Integer, default=70)
    enthusiasm: Mapped[int] = mapped_column(Integer, default=65)
    owner_approval: Mapped[int] = mapped_column(Integer, default=65)
    scar_tissue: Mapped[int] = mapped_column(Integer, default=0)
    status_label: Mapped[str] = mapped_column(String(40), default="content")
    priorities_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    expectations_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    recent_memory_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class OwnerSupporterEvent(Base):
    """Durable log of supporter reactions, protests, campaigns, and owner engagement outcomes."""

    __tablename__ = "owner_supporter_events"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_owner_supporter_events_idempotency"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    club_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    world_day: Mapped[int] = mapped_column(Integer, index=True, default=1)
    event_type: Mapped[str] = mapped_column(String(48), index=True, nullable=False)
    trigger_source_type: Mapped[str] = mapped_column(String(48), default="club_event")
    trigger_source_id: Mapped[str] = mapped_column(String(128), default="")
    headline: Mapped[str] = mapped_column(String(240), nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="")
    overall_sentiment_delta: Mapped[int] = mapped_column(Integer, default=0)
    credibility_delta: Mapped[int] = mapped_column(Integer, default=0)
    attendance_impact_pct: Mapped[int] = mapped_column(Integer, default=0)
    segment_deltas_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    contradiction_detected: Mapped[bool] = mapped_column(Boolean, default=False)
    contradiction_reason: Mapped[str | None] = mapped_column(String(240), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(160), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)


class OwnerMediaOutlet(Base):
    """Persistent media outlet and journalist identity with editorial focus and credibility."""

    __tablename__ = "owner_media_outlets"
    __table_args__ = (UniqueConstraint("outlet_key", name="uq_owner_media_outlets_outlet_key"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    outlet_key: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    outlet_name: Mapped[str] = mapped_column(String(120), nullable=False)
    journalist_name: Mapped[str] = mapped_column(String(120), nullable=False)
    journalist_role: Mapped[str] = mapped_column(String(80), default="Senior Football Correspondent")
    editorial_focus: Mapped[str] = mapped_column(String(48), index=True, nullable=False)
    credibility_tier: Mapped[str] = mapped_column(String(32), default="tier_1_authoritative")
    credibility_score: Mapped[int] = mapped_column(Integer, default=88)
    tone_style: Mapped[str] = mapped_column(String(48), default="analytical")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class OwnerMediaStory(Base):
    """Persistent football media story distinguishing verified events, reported info, rumours, and opinion."""

    __tablename__ = "owner_media_stories"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_owner_media_stories_idempotency"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    club_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    world_day: Mapped[int] = mapped_column(Integer, index=True, default=1)
    outlet_key: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    outlet_name: Mapped[str] = mapped_column(String(120), nullable=False)
    journalist_name: Mapped[str] = mapped_column(String(120), nullable=False)
    editorial_focus: Mapped[str] = mapped_column(String(48), default="local_club_reporting")
    credibility_score: Mapped[int] = mapped_column(Integer, default=85)
    story_type: Mapped[str] = mapped_column(String(48), index=True, nullable=False)
    classification: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    is_confirmed_fact: Mapped[bool] = mapped_column(Boolean, default=True)
    headline: Mapped[str] = mapped_column(String(240), nullable=False)
    subheadline: Mapped[str] = mapped_column(String(320), default="")
    body: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(48), default="club_event")
    source_id: Mapped[str] = mapped_column(String(128), default="")
    established_facts_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    grounding_report_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    reputation_delta: Mapped[int] = mapped_column(Integer, default=0)
    supporter_sentiment_delta: Mapped[int] = mapped_column(Integer, default=0)
    commercial_attractiveness_delta: Mapped[int] = mapped_column(Integer, default=0)
    sponsorship_interest_delta: Mapped[int] = mapped_column(Integer, default=0)
    leadership_pressure_delta: Mapped[int] = mapped_column(Integer, default=0)
    owner_response_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(160), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)


class OwnerClubHistoryEntry(Base):
    """Permanent institutional history ledger entry that survives ownership, staff, and season changes."""

    __tablename__ = "owner_club_history_entries"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_owner_club_history_entries_idempotency"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    club_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    season_number: Mapped[int] = mapped_column(Integer, index=True, default=1)
    world_day: Mapped[int] = mapped_column(Integer, index=True, default=1)
    category: Mapped[str] = mapped_column(String(48), index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    narrative_summary: Mapped[str] = mapped_column(Text, default="")
    entity_type: Mapped[str | None] = mapped_column(String(48), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    entity_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    established_facts_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    is_major_milestone: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(160), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)


class OwnerClubSeasonArchive(Base):
    """Permanent season archive record for a club's competition campaigns."""

    __tablename__ = "owner_club_season_archives"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_owner_club_season_archives_idempotency"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    club_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    season_number: Mapped[int] = mapped_column(Integer, index=True, default=1)
    season_label: Mapped[str] = mapped_column(String(64), default="Season 1")
    competition_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    competition_name: Mapped[str] = mapped_column(String(120), nullable=False)
    competition_format: Mapped[str] = mapped_column(String(24), default="league")
    division_level: Mapped[int] = mapped_column(Integer, default=4)
    final_position: Mapped[int] = mapped_column(Integer, default=1)
    played: Mapped[int] = mapped_column(Integer, default=0)
    won: Mapped[int] = mapped_column(Integer, default=0)
    drawn: Mapped[int] = mapped_column(Integer, default=0)
    lost: Mapped[int] = mapped_column(Integer, default=0)
    goals_for: Mapped[int] = mapped_column(Integer, default=0)
    goals_against: Mapped[int] = mapped_column(Integer, default=0)
    points: Mapped[int] = mapped_column(Integer, default=0)
    trophy_won: Mapped[bool] = mapped_column(Boolean, default=False)
    promotion_status: Mapped[str] = mapped_column(String(32), default="retained")
    manager_name: Mapped[str] = mapped_column(String(120), default="First-Team Manager")
    top_scorer_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    top_scorer_goals: Mapped[int] = mapped_column(Integer, default=0)
    prize_money_gtex: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    average_attendance: Mapped[int] = mapped_column(Integer, default=0)
    narrative_summary: Mapped[str] = mapped_column(Text, default="")
    records_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    idempotency_key: Mapped[str] = mapped_column(String(160), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)


class OwnerClubManagerialTenure(Base):
    """Permanent managerial and senior staff tenure record with W/D/L, trophies, and departure reason."""

    __tablename__ = "owner_club_managerial_tenures"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    club_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    manager_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    manager_name: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[str] = mapped_column(String(48), default="first_team_manager")
    tactical_style: Mapped[str] = mapped_column(String(48), default="balanced")
    appointed_world_day: Mapped[int] = mapped_column(Integer, default=1)
    departed_world_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(24), index=True, default="active")
    matches_managed: Mapped[int] = mapped_column(Integer, default=0)
    wins: Mapped[int] = mapped_column(Integer, default=0)
    draws: Mapped[int] = mapped_column(Integer, default=0)
    losses: Mapped[int] = mapped_column(Integer, default=0)
    goals_for: Mapped[int] = mapped_column(Integer, default=0)
    goals_against: Mapped[int] = mapped_column(Integer, default=0)
    trophies_won: Mapped[int] = mapped_column(Integer, default=0)
    departure_reason: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # Historical GTEX severance remains separate from the new Fan Coin contract settlement field.
    severance_paid_gtex: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    severance_paid_fan_coin: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    honors_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    tenure_summary: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class OwnerClubTransferRecord(Base):
    """Permanent club transfer arrival and departure ledger."""

    __tablename__ = "owner_club_transfer_records"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_owner_club_transfer_records_idempotency"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    club_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    direction: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    transfer_type: Mapped[str] = mapped_column(String(32), default="market_signing")
    player_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    player_name: Mapped[str] = mapped_column(String(120), nullable=False)
    position: Mapped[str] = mapped_column(String(16), default="MID")
    age: Mapped[int] = mapped_column(Integer, default=22)
    overall_rating: Mapped[int] = mapped_column(Integer, default=70)
    fee_gtex: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    wage_gtex: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    counterparty_club_name: Mapped[str] = mapped_column(String(120), default="GTEX Transfer Market")
    season_number: Mapped[int] = mapped_column(Integer, default=1)
    world_day: Mapped[int] = mapped_column(Integer, index=True, default=1)
    is_record_signing: Mapped[bool] = mapped_column(Boolean, default=False)
    is_record_sale: Mapped[bool] = mapped_column(Boolean, default=False)
    narrative_note: Mapped[str] = mapped_column(String(240), default="")
    idempotency_key: Mapped[str] = mapped_column(String(160), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)


class OwnerClubAcademyGraduate(Base):
    """Permanent academy prospect, graduate, and first-team debut tracker."""

    __tablename__ = "owner_club_academy_graduates"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_owner_club_academy_graduates_idempotency"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    club_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    player_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    player_name: Mapped[str] = mapped_column(String(120), nullable=False)
    position: Mapped[str] = mapped_column(String(16), default="MID")
    intake_world_day: Mapped[int] = mapped_column(Integer, default=1)
    promoted_world_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    debut_world_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    debut_match_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    debut_opponent_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    initial_rating: Mapped[int] = mapped_column(Integer, default=55)
    current_rating: Mapped[int] = mapped_column(Integer, default=55)
    potential_rating: Mapped[int] = mapped_column(Integer, default=78)
    first_team_appearances: Mapped[int] = mapped_column(Integer, default=0)
    first_team_goals: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), index=True, default="academy_prospect")
    narrative_note: Mapped[str] = mapped_column(String(240), default="")
    idempotency_key: Mapped[str] = mapped_column(String(160), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class OwnerClubRivalry(Base):
    """Permanent historic rivalry record evolving from repeated encounters and competitive stakes."""

    __tablename__ = "owner_club_rivalries"
    __table_args__ = (UniqueConstraint("club_id", "rival_club_id", name="uq_owner_club_rivalries_club_rival"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    club_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    rival_club_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    rival_club_name: Mapped[str] = mapped_column(String(120), nullable=False)
    rivalry_name: Mapped[str] = mapped_column(String(160), default="Competitive Fixture")
    origin_reason: Mapped[str] = mapped_column(String(120), default="repeated_encounters")
    intensity_score: Mapped[int] = mapped_column(Integer, default=20)
    rivalry_tier: Mapped[str] = mapped_column(String(32), default="emerging")
    matches_played: Mapped[int] = mapped_column(Integer, default=0)
    wins: Mapped[int] = mapped_column(Integer, default=0)
    draws: Mapped[int] = mapped_column(Integer, default=0)
    losses: Mapped[int] = mapped_column(Integer, default=0)
    goals_for: Mapped[int] = mapped_column(Integer, default=0)
    goals_against: Mapped[int] = mapped_column(Integer, default=0)
    last_meeting_world_day: Mapped[int] = mapped_column(Integer, default=1)
    notable_encounters_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
