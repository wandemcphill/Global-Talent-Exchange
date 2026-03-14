from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.user import User


class GiftComboRule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "gift_combo_rules"
    __table_args__ = (UniqueConstraint("rule_key", name="uq_gift_combo_rules_rule_key"),)

    rule_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    min_combo_count: Mapped[int] = mapped_column(Integer, nullable=False, default=2, server_default="2")
    window_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=120, server_default="120")
    bonus_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=10, server_default="10")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    updated_by_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    updated_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[updated_by_user_id])


__all__ = ["GiftComboRule"]
