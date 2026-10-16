from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Index, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PredictionOutcome(StrEnum):
    HOME_WIN = "home_win"
    AWAY_WIN = "away_win"
    DRAW = "draw"


class Prediction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "predictions"
    __table_args__ = (
        UniqueConstraint("user_id", "match_id", name="uq_predictions_user_match"),
        Index("ix_predictions_match_id", "match_id"),
        Index("ix_predictions_user_id", "user_id"),
        Index("ix_predictions_resolved_at", "resolved_at"),
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    match_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("competition_matches.id", ondelete="CASCADE"),
        nullable=False,
    )
    predicted_outcome: Mapped[PredictionOutcome] = mapped_column(
        Enum(PredictionOutcome, name="prediction_outcome", native_enum=False),
        nullable=False,
    )
    confidence_level: Mapped[float] = mapped_column(Float, nullable=False, default=0.5, server_default="0.5")
    reward_earned: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    difficulty_multiplier: Mapped[float] = mapped_column(Float, nullable=False, default=1.0, server_default="1.0")
    actual_outcome: Mapped[PredictionOutcome | None] = mapped_column(
        Enum(PredictionOutcome, name="prediction_actual_outcome", native_enum=False),
        nullable=True,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = ["Prediction", "PredictionOutcome"]
