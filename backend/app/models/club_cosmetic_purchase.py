from __future__ import annotations

from typing import Any

from sqlalchemy import Boolean, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ClubCosmeticPurchase(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "club_cosmetic_purchases"
    __table_args__ = (
        UniqueConstraint("purchase_ref", name="uq_club_cosmetic_purchases_purchase_ref"),
    )

    purchase_ref: Mapped[str] = mapped_column(String(72), nullable=False, index=True)
    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    buyer_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    catalog_item_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_cosmetic_catalog_items.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    purchase_type: Mapped[str] = mapped_column(String(48), nullable=False)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency_code: Mapped[str] = mapped_column(String(8), nullable=False, default="USD", server_default="USD")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="completed", server_default="completed")
    review_status: Mapped[str] = mapped_column(String(24), nullable=False, default="clear", server_default="clear")
    review_notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payment_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    fraud_flagged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
