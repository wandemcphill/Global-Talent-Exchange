from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class ClubBudgetSnapshot(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "club_budget_snapshots"

    club_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    total_budget_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    academy_allocation_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    scouting_allocation_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    sponsorship_commitment_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    available_budget_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")


__all__ = ["ClubBudgetSnapshot"]
