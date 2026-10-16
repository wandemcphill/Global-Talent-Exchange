from __future__ import annotations

from typing import Any

from sqlalchemy import Boolean, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.common.enums.club_identity_visibility import ClubIdentityVisibility
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ClubIdentityTheme(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "club_identity_themes"

    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    header_asset_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    backdrop_asset_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cabinet_theme_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    frame_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    visibility: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=ClubIdentityVisibility.PUBLIC.value,
        server_default=ClubIdentityVisibility.PUBLIC.value,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
