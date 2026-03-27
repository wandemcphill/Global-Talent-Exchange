from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ManagerDuel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "manager_duels"

    competition_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="manager_duel",
        server_default="manager_duel",
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default="scheduled",
        server_default="scheduled",
        index=True,
    )
    home_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    away_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    home_manager_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    away_manager_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    home_manager_name: Mapped[str] = mapped_column(String(160), nullable=False)
    away_manager_name: Mapped[str] = mapped_column(String(160), nullable=False)
    home_manager_source: Mapped[str] = mapped_column(String(24), nullable=False, default="hired", server_default="hired")
    away_manager_source: Mapped[str] = mapped_column(String(24), nullable=False, default="hired", server_default="hired")
    home_manager_asset_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    away_manager_asset_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    controller_home: Mapped[str] = mapped_column(String(24), nullable=False, default="manager", server_default="manager")
    controller_away: Mapped[str] = mapped_column(String(24), nullable=False, default="manager", server_default="manager")
    user_control_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    home_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    away_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    winner_manager_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    winner_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reputation_delta_home: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    reputation_delta_away: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class ManagerDuelProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "manager_duel_profiles"

    manager_key: Mapped[str] = mapped_column(String(160), nullable=False, unique=True, index=True)
    manager_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    source_type: Mapped[str] = mapped_column(String(24), nullable=False)
    owner_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reputation_score: Mapped[float] = mapped_column(Float, nullable=False, default=100.0, server_default="100")
    duel_wins: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    duel_draws: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    duel_losses: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    matches_played: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_duel_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = ["ManagerDuel", "ManagerDuelProfile"]
