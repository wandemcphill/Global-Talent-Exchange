from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CompetitionReward(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "competition_rewards"

    competition_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("user_competitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reward_pool_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("competition_reward_pools.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    participant_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("competition_participants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    club_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    placement: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reward_type: Mapped[str] = mapped_column(String(32), nullable=False, default="prize", server_default="prize")
    currency: Mapped[str] = mapped_column(String(12), nullable=False)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending", server_default="pending")
    ledger_transaction_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = ["CompetitionReward"]
