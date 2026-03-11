from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class PlayerValueSnapshotRecord(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "player_value_snapshots"
    __table_args__ = (
        UniqueConstraint("player_id", "as_of", name="uq_player_value_snapshots_player_as_of"),
    )

    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    player_name: Mapped[str] = mapped_column(String(160), nullable=False)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    previous_credits: Mapped[float] = mapped_column(Float, nullable=False)
    target_credits: Mapped[float] = mapped_column(Float, nullable=False)
    movement_pct: Mapped[float] = mapped_column(Float, nullable=False)
    football_truth_value_credits: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    market_signal_value_credits: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    breakdown_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    drivers_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
