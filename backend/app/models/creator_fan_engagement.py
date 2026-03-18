from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import Boolean, DateTime, Enum as SqlEnum, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CreatorMatchChatRoomStatus(str, Enum):
    SCHEDULED = "scheduled"
    OPEN = "open"
    CLOSED = "closed"
    ARCHIVED = "archived"


class CreatorMatchChatMessageVisibility(str, Enum):
    VISIBLE = "visible"
    FLAGGED = "flagged"
    HIDDEN = "hidden"


class CreatorTacticalAdviceType(str, Enum):
    SUBSTITUTION = "substitution"
    FORMATION_CHANGE = "formation_change"
    TACTICAL_ADJUSTMENT = "tactical_adjustment"


class CreatorTacticalAdviceStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class CreatorFanCompetitionStatus(str, Enum):
    ACTIVE = "active"
    CLOSED = "closed"


class CreatorRivalrySignalSurface(str, Enum):
    HOMEPAGE_PROMOTION = "homepage_promotion"
    NOTIFICATION = "notification"


class CreatorRivalrySignalStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class CreatorMatchChatRoom(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "creator_match_chat_rooms"
    __table_args__ = (
        UniqueConstraint("match_id", name="uq_creator_match_chat_rooms_match_id"),
        UniqueConstraint("room_key", name="uq_creator_match_chat_rooms_room_key"),
    )

    season_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("creator_league_seasons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    competition_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("user_competitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    match_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("competition_matches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    room_key: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    status: Mapped[CreatorMatchChatRoomStatus] = mapped_column(
        SqlEnum(CreatorMatchChatRoomStatus, name="creatormatchchatroomstatus"),
        nullable=False,
        default=CreatorMatchChatRoomStatus.SCHEDULED,
    )
    opens_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closes_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    layout_hints_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class CreatorMatchChatMessage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "creator_match_chat_messages"

    room_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("creator_match_chat_rooms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    supported_club_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    visibility: Mapped[CreatorMatchChatMessageVisibility] = mapped_column(
        SqlEnum(CreatorMatchChatMessageVisibility, name="creatormatchchatmessagevisibility"),
        nullable=False,
        default=CreatorMatchChatMessageVisibility.VISIBLE,
    )
    visibility_priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    shareholder: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    season_pass_holder: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    paying_viewer: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class CreatorMatchTacticalAdvice(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "creator_match_tactical_advice"

    season_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("creator_league_seasons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    competition_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("user_competitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    match_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("competition_matches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    supported_club_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    advice_type: Mapped[CreatorTacticalAdviceType] = mapped_column(
        SqlEnum(CreatorTacticalAdviceType, name="creatortacticaladvicetype"),
        nullable=False,
    )
    suggestion_text: Mapped[str] = mapped_column(String(255), nullable=False)
    visibility_priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    status: Mapped[CreatorTacticalAdviceStatus] = mapped_column(
        SqlEnum(CreatorTacticalAdviceStatus, name="creatortacticaladvicestatus"),
        nullable=False,
        default=CreatorTacticalAdviceStatus.ACTIVE,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class CreatorClubFollow(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "creator_club_follows"
    __table_args__ = (
        UniqueConstraint("club_id", "user_id", name="uq_creator_club_follows_club_user"),
    )

    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source: Mapped[str] = mapped_column(String(48), nullable=False, default="creator_match", server_default="creator_match")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class CreatorFanGroup(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "creator_fan_groups"
    __table_args__ = (
        UniqueConstraint("club_id", "slug", name="uq_creator_fan_groups_club_slug"),
    )

    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    slug: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    identity_label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_official: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class CreatorFanGroupMembership(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "creator_fan_group_memberships"
    __table_args__ = (
        UniqueConstraint("group_id", "user_id", name="uq_creator_fan_group_memberships_group_user"),
    )

    group_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("creator_fan_groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    member_role: Mapped[str] = mapped_column(String(32), nullable=False, default="member", server_default="member")
    fan_identity_label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class CreatorFanCompetition(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "creator_fan_competitions"

    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    match_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("competition_matches.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[CreatorFanCompetitionStatus] = mapped_column(
        SqlEnum(CreatorFanCompetitionStatus, name="creatorfancompetitionstatus"),
        nullable=False,
        default=CreatorFanCompetitionStatus.ACTIVE,
    )
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class CreatorFanCompetitionEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "creator_fan_competition_entries"
    __table_args__ = (
        UniqueConstraint("fan_competition_id", "user_id", name="uq_creator_fan_competition_entries_competition_user"),
    )

    fan_competition_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("creator_fan_competitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    fan_group_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("creator_fan_groups.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class CreatorFanWallEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "creator_fan_wall_events"

    club_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    match_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("competition_matches.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    actor_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_kind: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    headline: Mapped[str] = mapped_column(String(180), nullable=False)
    body: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reference_type: Mapped[str | None] = mapped_column(String(48), nullable=True)
    reference_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    prominence: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class CreatorRivalrySignalOutput(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "creator_rivalry_signal_outputs"
    __table_args__ = (
        UniqueConstraint("match_id", "surface", name="uq_creator_rivalry_signal_outputs_match_surface"),
    )

    match_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("competition_matches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    home_club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    away_club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    club_social_rivalry_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    surface: Mapped[CreatorRivalrySignalSurface] = mapped_column(
        SqlEnum(CreatorRivalrySignalSurface, name="creatorrivalrysignalsurface"),
        nullable=False,
    )
    signal_status: Mapped[CreatorRivalrySignalStatus] = mapped_column(
        SqlEnum(CreatorRivalrySignalStatus, name="creatorrivalrysignalstatus"),
        nullable=False,
        default=CreatorRivalrySignalStatus.INACTIVE,
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    headline: Mapped[str] = mapped_column(String(180), nullable=False)
    message: Mapped[str] = mapped_column(String(255), nullable=False)
    target_user_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    rationale_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = [
    "CreatorClubFollow",
    "CreatorFanCompetition",
    "CreatorFanCompetitionEntry",
    "CreatorFanCompetitionStatus",
    "CreatorFanGroup",
    "CreatorFanGroupMembership",
    "CreatorFanWallEvent",
    "CreatorMatchChatMessage",
    "CreatorMatchChatMessageVisibility",
    "CreatorMatchChatRoom",
    "CreatorMatchChatRoomStatus",
    "CreatorMatchTacticalAdvice",
    "CreatorRivalrySignalOutput",
    "CreatorRivalrySignalStatus",
    "CreatorRivalrySignalSurface",
    "CreatorTacticalAdviceStatus",
    "CreatorTacticalAdviceType",
]
