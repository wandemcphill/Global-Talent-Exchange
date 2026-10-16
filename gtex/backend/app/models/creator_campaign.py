from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CreatorCampaign(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "creator_campaigns"
    __table_args__ = (
        UniqueConstraint("creator_profile_id", "name", name="uq_creator_campaigns_creator_name"),
    )

    creator_profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("creator_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    share_code_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("share_codes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    linked_competition_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
