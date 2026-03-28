from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class FxRate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "fx_rates"
    __table_args__ = (UniqueConstraint("currency", name="uq_fx_rates_currency"),)

    currency: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    rate_to_naira: Mapped[Decimal] = mapped_column(
        Numeric(20, 6),
        nullable=False,
        default=Decimal("1.000000"),
        server_default="1.000000",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    updated_by_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    updated_by_user: Mapped["User | None"] = relationship("User")


class RegionalPricingRule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "regional_pricing_rules"
    __table_args__ = (UniqueConstraint("region_code", name="uq_regional_pricing_rules_region_code"),)

    region_code: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(64), nullable=False)
    price_multiplier: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        nullable=False,
        default=Decimal("1.0000"),
        server_default="1.0000",
    )
    withdrawal_limit_multiplier: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        nullable=False,
        default=Decimal("1.0000"),
        server_default="1.0000",
    )
    kyc_tier_label: Mapped[str] = mapped_column(String(32), nullable=False, default="standard", server_default="standard")
    tax_tracking_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    compliance_note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_by_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    updated_by_user: Mapped["User | None"] = relationship("User")


__all__ = ["FxRate", "RegionalPricingRule"]
