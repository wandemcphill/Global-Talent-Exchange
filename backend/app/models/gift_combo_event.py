from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, String, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.economy_config import GiftCatalogItem
    from backend.app.models.gift_transaction import GiftTransaction
    from backend.app.models.gift_combo_rule import GiftComboRule
    from backend.app.models.user import User


class GiftComboEvent(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "gift_combo_events"
    __table_args__ = (
        Index("ix_gift_combo_events_sender", "sender_user_id"),
        Index("ix_gift_combo_events_recipient", "recipient_user_id"),
        Index("ix_gift_combo_events_created_at", "created_at"),
    )

    gift_transaction_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("gift_transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recipient_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    gift_catalog_item_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("gift_catalog.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    combo_rule_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("gift_combo_rules.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    combo_rule_key: Mapped[str] = mapped_column(String(64), nullable=False)
    combo_count: Mapped[int] = mapped_column(nullable=False)
    window_seconds: Mapped[int] = mapped_column(nullable=False)
    bonus_bps: Mapped[int] = mapped_column(nullable=False, default=0)
    bonus_amount: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=Decimal("0.0000"))

    gift_transaction: Mapped["GiftTransaction"] = relationship("GiftTransaction", foreign_keys=[gift_transaction_id])
    sender: Mapped["User"] = relationship("User", foreign_keys=[sender_user_id])
    recipient: Mapped["User"] = relationship("User", foreign_keys=[recipient_user_id])
    gift_catalog_item: Mapped["GiftCatalogItem"] = relationship("GiftCatalogItem")
    combo_rule: Mapped["GiftComboRule | None"] = relationship("GiftComboRule")


__all__ = ["GiftComboEvent"]
