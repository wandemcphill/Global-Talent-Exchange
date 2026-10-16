from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class UserRegionProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_region_profiles"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_user_region_profiles_user_id"),
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    region_code: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    selected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    last_changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    change_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    permanent_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")

    user: Mapped["User"] = relationship("User")


__all__ = ["UserRegionProfile"]
