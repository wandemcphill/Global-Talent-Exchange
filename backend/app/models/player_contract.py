from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PlayerContract(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "player_contracts"

    player_id: Mapped[str] = mapped_column(String(36), ForeignKey("ingestion_players.id", ondelete="CASCADE"), nullable=False, index=True)
    club_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("club_profiles.id", ondelete="SET NULL"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active", server_default="active", index=True)
    wage_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"), server_default="0")
    bonus_terms: Mapped[str | None] = mapped_column(String(255), nullable=True)
    release_clause_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    signed_on: Mapped[date] = mapped_column(Date, nullable=False)
    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    ends_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    extension_option_until: Mapped[date | None] = mapped_column(Date, nullable=True)
