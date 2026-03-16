from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, Enum as SqlEnum, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class LiveThreadStatus(str, Enum):
    OPEN = "open"
    LOCKED = "locked"
    ARCHIVED = "archived"


class MessageVisibility(str, Enum):
    PUBLIC = "public"
    MOD_REVIEW = "mod_review"
    HIDDEN = "hidden"


class PrivateMessageThreadStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    BLOCKED = "blocked"


class CompetitionWatchlist(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "competition_watchlists"
    __table_args__ = (
        UniqueConstraint("user_id", "competition_key", name="uq_competition_watchlists_user_competition"),
    )

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    competition_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    competition_title: Mapped[str] = mapped_column(String(180), nullable=False)
    competition_type: Mapped[str] = mapped_column(String(80), nullable=False, default="general")
    notify_on_story: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notify_on_launch: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class LiveThread(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "live_threads"

    thread_key: Mapped[str] = mapped_column(String(140), nullable=False, unique=True, index=True)
    competition_key: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    created_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    status: Mapped[LiveThreadStatus] = mapped_column(SqlEnum(LiveThreadStatus, name="livethreadstatus"), nullable=False, default=LiveThreadStatus.OPEN)
    pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class LiveThreadMessage(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "live_thread_messages"

    thread_id: Mapped[str] = mapped_column(ForeignKey("live_threads.id", ondelete="CASCADE"), nullable=False, index=True)
    author_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    visibility: Mapped[MessageVisibility] = mapped_column(SqlEnum(MessageVisibility, name="communitymessagevisibility"), nullable=False, default=MessageVisibility.PUBLIC)
    like_count: Mapped[int] = mapped_column(nullable=False, default=0)
    reply_count: Mapped[int] = mapped_column(nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class PrivateMessageThread(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "private_message_threads"

    thread_key: Mapped[str] = mapped_column(String(140), nullable=False, unique=True, index=True)
    created_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[PrivateMessageThreadStatus] = mapped_column(SqlEnum(PrivateMessageThreadStatus, name="privatemessagethreadstatus"), nullable=False, default=PrivateMessageThreadStatus.ACTIVE)
    subject: Mapped[str] = mapped_column(String(180), nullable=False, default="")
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class PrivateMessageParticipant(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "private_message_participants"
    __table_args__ = (
        UniqueConstraint("thread_id", "user_id", name="uq_private_message_participant_thread_user"),
    )

    thread_id: Mapped[str] = mapped_column(ForeignKey("private_message_threads.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    is_muted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class PrivateMessage(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "private_messages"

    thread_id: Mapped[str] = mapped_column(ForeignKey("private_message_threads.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
