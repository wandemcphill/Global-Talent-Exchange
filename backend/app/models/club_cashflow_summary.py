from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class ClubCashflowSummary(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "club_cashflow_summaries"

    club_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(12), nullable=False, default="USD", server_default="USD")
    total_income_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    total_expense_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    net_cashflow_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    sponsorship_income_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    competition_income_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    academy_spend_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    scouting_spend_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")


__all__ = ["ClubCashflowSummary"]
