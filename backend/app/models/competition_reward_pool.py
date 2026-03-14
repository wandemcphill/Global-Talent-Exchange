from __future__ import annotations

from typing import Any

from sqlalchemy import ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CompetitionRewardPool(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "competition_reward_pools"

    competition_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("user_competitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pool_type: Mapped[str] = mapped_column(String(32), nullable=False, default="entry_fee", server_default="entry_fee")
    currency: Mapped[str] = mapped_column(String(12), nullable=False)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="planned", server_default="planned")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = ["CompetitionRewardPool"]
