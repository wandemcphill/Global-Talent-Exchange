from __future__ import annotations

from typing import Any

from sqlalchemy import Boolean, ForeignKey, Index, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class HighlightShareTemplate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "highlight_share_templates"
    __table_args__ = (
        UniqueConstraint("code", name="uq_highlight_share_templates_code"),
        Index("ix_highlight_share_templates_aspect_ratio", "aspect_ratio"),
    )

    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    aspect_ratio: Mapped[str] = mapped_column(String(16), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    overlay_defaults_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class HighlightShareExport(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "highlight_share_exports"
    __table_args__ = (
        Index("ix_highlight_share_exports_user_id", "user_id"),
        Index("ix_highlight_share_exports_match_key", "match_key"),
        Index("ix_highlight_share_exports_status", "status"),
    )

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    template_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("highlight_share_templates.id", ondelete="SET NULL"), nullable=True)
    match_key: Mapped[str] = mapped_column(String(120), nullable=False)
    source_storage_key: Mapped[str] = mapped_column(String(255), nullable=False)
    export_storage_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="generated", server_default="generated")
    aspect_ratio: Mapped[str] = mapped_column(String(16), nullable=False)
    watermark_label: Mapped[str | None] = mapped_column(String(80), nullable=True)
    share_title: Mapped[str | None] = mapped_column(String(160), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class HighlightShareAmplification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "highlight_share_amplifications"
    __table_args__ = (
        Index("ix_highlight_share_amplifications_export_id", "export_id"),
        Index("ix_highlight_share_amplifications_user_id", "user_id"),
        Index("ix_highlight_share_amplifications_story_feed_item_id", "story_feed_item_id"),
        Index("ix_highlight_share_amplifications_subject", "subject_type", "subject_id"),
        Index("ix_highlight_share_amplifications_channel_status", "channel", "status"),
    )

    export_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("highlight_share_exports.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    story_feed_item_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("story_feed_items.id", ondelete="SET NULL"),
        nullable=True,
    )
    channel: Mapped[str] = mapped_column(String(32), nullable=False, default="story_feed", server_default="story_feed")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="published", server_default="published")
    subject_type: Mapped[str | None] = mapped_column(String(48), nullable=True)
    subject_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = ["HighlightShareAmplification", "HighlightShareExport", "HighlightShareTemplate"]
