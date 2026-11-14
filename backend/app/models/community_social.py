from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin


class CommunityChannel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "community_channels"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_community_channels_slug"),
        Index("ix_community_channels_category", "category"),
        Index("ix_community_channels_is_archived", "is_archived"),
    )

    slug: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(48), nullable=False, default="general", server_default="general")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    icon: Mapped[str | None] = mapped_column(String(48), nullable=True)
    is_official: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    is_read_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    last_message_seq: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class CommunityChannelMessage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "community_channel_messages"
    __table_args__ = (
        Index("ix_community_channel_messages_channel_seq", "channel_id", "seq"),
        Index("ix_community_channel_messages_visibility", "visibility"),
    )

    channel_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("community_channels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    seq: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    sender_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reply_to_message_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("community_channel_messages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    visibility: Mapped[str] = mapped_column(String(24), nullable=False, default="public", server_default="public")
    pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    pinned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    mentions_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    linked_entities_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class CommunityPost(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "community_posts"
    __table_args__ = (
        Index("ix_community_posts_post_type", "post_type"),
        Index("ix_community_posts_visibility_created", "visibility", "created_at"),
        Index("ix_community_posts_club_id", "club_id"),
        Index("ix_community_posts_player_id", "player_id"),
        Index("ix_community_posts_competition_id", "competition_id"),
    )

    author_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    post_type: Mapped[str] = mapped_column(
        String(48),
        nullable=False,
        default="football_discussion",
        server_default="football_discussion",
    )
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    channel_slug: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    club_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    player_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    competition_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    competition_source: Mapped[str | None] = mapped_column(String(24), nullable=True)
    tags_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    mentions_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    poll_options_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    visibility: Mapped[str] = mapped_column(String(24), nullable=False, default="public", server_default="public")
    is_pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    is_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    is_official: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    comment_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    reaction_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    bookmark_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class CommunityPostComment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "community_post_comments"
    __table_args__ = (Index("ix_community_post_comments_post_created", "post_id", "created_at"),)

    post_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("community_posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_comment_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("community_post_comments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    visibility: Mapped[str] = mapped_column(String(24), nullable=False, default="public", server_default="public")
    mentions_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class CommunityBookmark(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "community_bookmarks"
    __table_args__ = (UniqueConstraint("user_id", "post_id", name="uq_community_bookmarks_user_post"),)

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    post_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("community_posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )


class CommunityPollVote(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "community_poll_votes"
    __table_args__ = (UniqueConstraint("post_id", "user_id", name="uq_community_poll_votes_post_user"),)

    post_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("community_posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    option_id: Mapped[str] = mapped_column(String(64), nullable=False)


class CommunityUserMute(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "community_user_mutes"
    __table_args__ = (UniqueConstraint("user_id", "muted_user_id", name="uq_community_user_mutes_pair"),)

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    muted_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reason: Mapped[str | None] = mapped_column(String(240), nullable=True)


class CommunityCompetitionApplication(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "community_competition_applications"
    __table_args__ = (
        UniqueConstraint("competition_id", "applicant_user_id", name="uq_community_comp_app_comp_user"),
        Index("ix_community_comp_app_status", "competition_id", "status"),
    )

    competition_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("user_hosted_competitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    applicant_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    club_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending", server_default="pending")
    reviewed_by_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_note: Mapped[str | None] = mapped_column(String(240), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = [
    "CommunityBookmark",
    "CommunityChannel",
    "CommunityChannelMessage",
    "CommunityCompetitionApplication",
    "CommunityPollVote",
    "CommunityPost",
    "CommunityPostComment",
    "CommunityUserMute",
]
