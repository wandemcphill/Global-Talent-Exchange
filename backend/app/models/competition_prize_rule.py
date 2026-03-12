from __future__ import annotations

from sqlalchemy import Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CompetitionPrizeRule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "competition_prize_rules"
    __table_args__ = (
        UniqueConstraint("competition_id", name="uq_competition_prize_rules_competition_id"),
    )

    competition_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    payout_mode: Mapped[str] = mapped_column(String(24), nullable=False)
    top_n: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payout_percentages: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=list)
