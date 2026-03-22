from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.club_sponsorship_contract import ClubSponsorshipContract


class ClubSponsorshipPayout(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "club_sponsorship_payouts"

    contract_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_sponsorship_contracts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending", server_default="pending")
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    contract: Mapped["ClubSponsorshipContract"] = relationship(back_populates="payouts")


__all__ = ["ClubSponsorshipPayout"]
