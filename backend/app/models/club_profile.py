from __future__ import annotations

from datetime import date

from sqlalchemy import Date, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.common.enums.club_identity_visibility import ClubIdentityVisibility
from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ClubProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "club_profiles"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_club_profiles_slug"),
    )

    owner_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    club_name: Mapped[str] = mapped_column(String(120), nullable=False)
    short_name: Mapped[str | None] = mapped_column(String(40), nullable=True)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    crest_asset_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    primary_color: Mapped[str] = mapped_column(String(16), nullable=False)
    secondary_color: Mapped[str] = mapped_column(String(16), nullable=False)
    accent_color: Mapped[str] = mapped_column(String(16), nullable=False)
    home_venue_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    visibility: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=ClubIdentityVisibility.PUBLIC.value,
        server_default=ClubIdentityVisibility.PUBLIC.value,
    )
    founded_at: Mapped[date | None] = mapped_column(Date, nullable=True)
