from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ClubJerseyDesign(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "club_jersey_designs"

    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    slot_type: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    base_template_id: Mapped[str] = mapped_column(String(64), nullable=False)
    primary_color: Mapped[str] = mapped_column(String(16), nullable=False)
    secondary_color: Mapped[str] = mapped_column(String(16), nullable=False)
    trim_color: Mapped[str] = mapped_column(String(16), nullable=False)
    sleeve_style: Mapped[str | None] = mapped_column(String(32), nullable=True)
    motto_text: Mapped[str | None] = mapped_column(String(80), nullable=True)
    number_style: Mapped[str | None] = mapped_column(String(32), nullable=True)
    crest_placement: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="left_chest",
        server_default="left_chest",
    )
    preview_asset_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    moderation_status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default="approved",
        server_default="approved",
    )
    moderation_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reviewed_by_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
