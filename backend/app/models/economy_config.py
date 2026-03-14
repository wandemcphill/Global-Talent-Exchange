from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.user import User


class GiftCatalogItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "gift_catalog"
    __table_args__ = (UniqueConstraint("key", name="uq_gift_catalog_key"),)

    key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    tier: Mapped[str] = mapped_column(String(32), nullable=False, default="standard", server_default="standard")
    fancoin_price: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False, default=0, server_default="0.0000")
    animation_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sound_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    updated_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    updated_by_user: Mapped["User | None"] = relationship()


class ServicePricingRule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "service_pricing_rules"
    __table_args__ = (UniqueConstraint("service_key", name="uq_service_pricing_rules_service_key"),)

    service_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price_coin: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False, default=0, server_default="0.0000")
    price_fancoin_equivalent: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False, default=0, server_default="0.0000")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    updated_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    updated_by_user: Mapped["User | None"] = relationship()
