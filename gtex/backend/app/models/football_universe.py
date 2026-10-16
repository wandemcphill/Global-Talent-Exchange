from __future__ import annotations

from enum import StrEnum
from typing import Any

from sqlalchemy import Enum, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ClubPhilosophy(StrEnum):
    YOUTH_DEVELOPMENT = "youth_development"
    ATTACKING = "attacking"
    DEFENSIVE = "defensive"
    POSSESSION = "possession"
    COUNTER_ATTACK = "counter_attack"


class FanSentiment(StrEnum):
    HAPPY = "happy"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    VERY_NEGATIVE = "very_negative"


class MediaEventType(StrEnum):
    HEADLINE = "headline"
    INTERVIEW = "interview"
    CONTROVERSY = "controversy"
    TRANSFER_NEWS = "transfer_news"


class BroadcastSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "broadcast_sessions"
    __table_args__ = (
        UniqueConstraint("match_id", name="uq_broadcast_sessions_match_id"),
        Index("ix_broadcast_sessions_match_id", "match_id"),
    )

    match_id: Mapped[str] = mapped_column(String(120), nullable=False)
    commentators: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    overlay_state: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class FanBase(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "fan_bases"
    __table_args__ = (
        UniqueConstraint("club_id", name="uq_fan_bases_club_id"),
        Index("ix_fan_bases_sentiment", "sentiment"),
        Index("ix_fan_bases_expectation_level", "expectation_level"),
    )

    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    fan_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    loyalty_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0, server_default="50.0")
    expectation_level: Mapped[str] = mapped_column(String(32), nullable=False, default="balanced", server_default="balanced")
    sentiment: Mapped[FanSentiment] = mapped_column(
        Enum(FanSentiment, name="fan_sentiment", native_enum=False),
        nullable=False,
        default=FanSentiment.NEUTRAL,
        server_default=FanSentiment.NEUTRAL.value,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class ClubIdentity(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "club_identity_profiles"
    __table_args__ = (
        UniqueConstraint("club_id", name="uq_club_identity_profiles_club_id"),
        Index("ix_club_identity_profiles_philosophy", "philosophy"),
    )

    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    philosophy: Mapped[ClubPhilosophy] = mapped_column(
        Enum(ClubPhilosophy, name="club_philosophy", native_enum=False),
        nullable=False,
        default=ClubPhilosophy.POSSESSION,
        server_default=ClubPhilosophy.POSSESSION.value,
    )
    culture_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0, server_default="50.0")
    tactical_consistency: Mapped[float] = mapped_column(Float, nullable=False, default=50.0, server_default="50.0")
    brand_strength: Mapped[float] = mapped_column(Float, nullable=False, default=50.0, server_default="50.0")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class MediaEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "media_events"
    __table_args__ = (
        Index("ix_media_events_type", "type"),
        Index("ix_media_events_match_id", "match_id"),
        Index("ix_media_events_club_id", "club_id"),
    )

    type: Mapped[MediaEventType] = mapped_column(
        Enum(MediaEventType, name="media_event_type", native_enum=False),
        nullable=False,
        default=MediaEventType.HEADLINE,
        server_default=MediaEventType.HEADLINE.value,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    impact: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    match_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    club_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )


__all__ = [
    "BroadcastSession",
    "ClubIdentity",
    "ClubPhilosophy",
    "FanBase",
    "FanSentiment",
    "MediaEvent",
    "MediaEventType",
]
