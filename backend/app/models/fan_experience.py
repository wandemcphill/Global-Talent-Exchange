from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class FanProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "fan_profiles"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_fan_profiles_user_id"),
        Index("ix_fan_profiles_fan_tier", "fan_tier"),
        Index("ix_fan_profiles_favorite_club_id", "favorite_club_id"),
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    favorite_club_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    favorite_club_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    favorite_player_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    favorite_player_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    rival_club_ids_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    loyalty_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    reputation_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    fan_tier: Mapped[str] = mapped_column(String(16), nullable=False, default="Casual", server_default="Casual")
    attendance_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    attendance_history_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    badges_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class FanExperienceTicket(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "fan_experience_tickets"
    __table_args__ = (
        UniqueConstraint("user_id", "event_key", "ticket_tier", name="uq_fan_experience_tickets_user_event_tier"),
        Index("ix_fan_experience_tickets_event_type", "event_type"),
        Index("ix_fan_experience_tickets_event_key", "event_key"),
        Index("ix_fan_experience_tickets_match_id", "match_id"),
        Index("ix_fan_experience_tickets_status", "status"),
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    fan_profile_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("fan_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(24), nullable=False)
    event_key: Mapped[str] = mapped_column(String(128), nullable=False)
    match_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("gtex_matches.id", ondelete="CASCADE"),
        nullable=True,
    )
    ticket_tier: Mapped[str] = mapped_column(String(24), nullable=False)
    access_level: Mapped[str] = mapped_column(String(24), nullable=False, default="standard", server_default="standard")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="purchased", server_default="purchased")
    seat_label: Mapped[str | None] = mapped_column(String(64), nullable=True)
    price_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0.0000")
    discount_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    priority_stream: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    exclusive_commentary_lines_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    loyalty_bonus: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    reputation_bonus: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class FanReaction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "fan_reactions"
    __table_args__ = (
        Index("ix_fan_reactions_match_id", "match_id"),
        Index("ix_fan_reactions_event_key", "event_key"),
        Index("ix_fan_reactions_fan_profile_id", "fan_profile_id"),
        Index("ix_fan_reactions_reaction_type", "reaction_type"),
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    fan_profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("fan_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    match_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("gtex_matches.id", ondelete="CASCADE"),
        nullable=True,
    )
    event_key: Mapped[str] = mapped_column(String(128), nullable=False)
    channel: Mapped[str] = mapped_column(String(24), nullable=False, default="match", server_default="match")
    reaction_type: Mapped[str] = mapped_column(String(24), nullable=False)
    supported_side: Mapped[str | None] = mapped_column(String(8), nullable=True)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    tier_at_reaction: Mapped[str] = mapped_column(String(16), nullable=False, default="Casual", server_default="Casual")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class FanTribe(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "fan_tribes"
    __table_args__ = (
        UniqueConstraint("club_id", name="uq_fan_tribes_club_id"),
        Index("ix_fan_tribes_power_score", "power_score"),
    )

    club_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    club_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    tribe_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    members: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    rivalry_targets: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    power_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class MatchChatRoom(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "gtex_match_chat_rooms"
    __table_args__ = (
        UniqueConstraint("match_id", name="uq_gtex_match_chat_rooms_match_id"),
        UniqueConstraint("room_key", name="uq_gtex_match_chat_rooms_room_key"),
        Index("ix_gtex_match_chat_rooms_moment_spike_score", "moment_spike_score"),
    )

    match_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("gtex_matches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    room_key: Mapped[str] = mapped_column(String(128), nullable=False)
    room_title: Mapped[str | None] = mapped_column(String(180), nullable=True)
    message_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    emoji_burst_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    moment_spike_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class MatchChatMessage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "gtex_match_chat_messages"
    __table_args__ = (
        Index("ix_gtex_match_chat_messages_room_id", "room_id"),
        Index("ix_gtex_match_chat_messages_match_id", "match_id"),
        Index("ix_gtex_match_chat_messages_fan_tribe_id", "fan_tribe_id"),
        Index("ix_gtex_match_chat_messages_sentiment", "sentiment"),
    )

    room_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("gtex_match_chat_rooms.id", ondelete="CASCADE"),
        nullable=False,
    )
    match_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("gtex_matches.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    fan_profile_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("fan_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    fan_tribe_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("fan_tribes.id", ondelete="SET NULL"),
        nullable=True,
    )
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    emoji: Mapped[str | None] = mapped_column(String(32), nullable=True)
    intensity: Mapped[float] = mapped_column(Float, nullable=False, default=1.0, server_default="1")
    sentiment: Mapped[str] = mapped_column(String(16), nullable=False, default="neutral", server_default="neutral")
    spike_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class NarrativeConflict(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "narrative_conflicts"
    __table_args__ = (
        UniqueConstraint("match_id", "conflict_type", name="uq_narrative_conflicts_match_type"),
        Index("ix_narrative_conflicts_status", "status"),
        Index("ix_narrative_conflicts_club_id", "club_id"),
        Index("ix_narrative_conflicts_manager_profile_id", "manager_profile_id"),
    )

    match_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("gtex_matches.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    club_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    player_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    manager_profile_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("manager_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    conflict_type: Mapped[str] = mapped_column(String(48), nullable=False)
    headline: Mapped[str] = mapped_column(String(220), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active", server_default="active")
    severity: Mapped[str] = mapped_column(String(24), nullable=False, default="medium", server_default="medium")
    impact_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    triggers_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    impact_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class MarketShockEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "market_shock_events"
    __table_args__ = (
        UniqueConstraint("match_id", "shock_type", name="uq_market_shock_events_match_type"),
        Index("ix_market_shock_events_status", "status"),
        Index("ix_market_shock_events_club_id", "club_id"),
    )

    match_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("gtex_matches.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    club_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    player_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    shock_type: Mapped[str] = mapped_column(String(48), nullable=False)
    headline: Mapped[str] = mapped_column(String(220), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active", server_default="active")
    magnitude: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    player_price_delta_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    fan_sentiment_delta: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    betting_odds_delta_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    impact_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class MegaEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "mega_events"
    __table_args__ = (
        UniqueConstraint("event_key", name="uq_mega_events_event_key"),
        Index("ix_mega_events_match_id", "match_id"),
        Index("ix_mega_events_status", "status"),
    )

    event_key: Mapped[str] = mapped_column(String(128), nullable=False)
    match_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("gtex_matches.id", ondelete="CASCADE"),
        nullable=True,
    )
    event_type: Mapped[str] = mapped_column(String(48), nullable=False)
    title: Mapped[str] = mapped_column(String(220), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="scheduled", server_default="scheduled")
    limited_tickets: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    exclusive_commentary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    global_broadcast: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    hype_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class LegacySnapshot(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "legacy_snapshots"
    __table_args__ = (
        UniqueConstraint("category", "entity_id", name="uq_legacy_snapshots_category_entity"),
        Index("ix_legacy_snapshots_category", "category"),
        Index("ix_legacy_snapshots_score", "score"),
        Index("ix_legacy_snapshots_match_id", "match_id"),
    )

    category: Mapped[str] = mapped_column(String(48), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    match_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("gtex_matches.id", ondelete="CASCADE"),
        nullable=True,
    )
    season_key: Mapped[str] = mapped_column(String(64), nullable=False, default="lifetime", server_default="lifetime")
    headline: Mapped[str] = mapped_column(String(220), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    rank_position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = [
    "FanExperienceTicket",
    "FanProfile",
    "FanReaction",
    "FanTribe",
    "LegacySnapshot",
    "MarketShockEvent",
    "MatchChatMessage",
    "MatchChatRoom",
    "MegaEvent",
    "NarrativeConflict",
]
