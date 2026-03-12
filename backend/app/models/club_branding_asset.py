from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ClubBrandingAsset(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "club_branding_assets"

    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    asset_type: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    asset_name: Mapped[str] = mapped_column(String(120), nullable=False)
    asset_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    catalog_item_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    slot_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
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
