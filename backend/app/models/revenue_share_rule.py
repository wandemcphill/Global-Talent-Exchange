from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.user import User


class RevenueShareRule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "revenue_share_rules"
    __table_args__ = (UniqueConstraint("rule_key", name="uq_revenue_share_rule_key"),)

    rule_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    scope: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    platform_share_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    creator_share_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    recipient_share_bps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    burn_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=10, server_default="10")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    updated_by_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    updated_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[updated_by_user_id])


__all__ = ["RevenueShareRule"]
