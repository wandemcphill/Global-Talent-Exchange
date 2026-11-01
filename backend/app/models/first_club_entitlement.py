from __future__ import annotations

from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class FirstClubEntitlement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Authoritative record of a user's one-time first-club launch grant entitlement."""

    __tablename__ = "first_club_entitlements"
    __table_args__ = (UniqueConstraint("user_id", name="uq_first_club_entitlements_user_id"),)

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    club_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )
    gtex_grant_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("100000.0000"),
    )
    fan_grant_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("1000.0000"),
    )
    gtex_ledger_event_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
    )
    fan_ledger_event_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
    )
