from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ClubOpsStateSnapshot(Base):
    """Durable compatibility snapshot for the legacy typed ClubOps aggregate.

    The normalized ClubOps tables remain the queryable projections. This row
    preserves the complete typed state (including regen and youth-pipeline
    metadata not represented by those tables) across worker restarts.
    """

    __tablename__ = "club_ops_state_snapshots"

    state_key: Mapped[str] = mapped_column(String(32), primary_key=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )


__all__ = ["ClubOpsStateSnapshot"]
