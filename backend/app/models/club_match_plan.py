from __future__ import annotations

from typing import Any

from sqlalchemy import ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ClubMatchPlan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An owner-chosen formation + starting XI for a club's matches.

    One plan per club. Consumed by the match team factory, which always falls
    back to a safe auto-selection if the saved plan can't be satisfied.
    """

    __tablename__ = "club_match_plans"
    __table_args__ = (UniqueConstraint("club_id", name="uq_club_match_plan_club"),)

    club_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("club_profiles.id", ondelete="CASCADE"), nullable=False
    )
    formation: Mapped[str] = mapped_column(
        String(16), nullable=False, default="4-3-3", server_default="4-3-3"
    )
    starter_player_ids_json: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list, server_default="[]"
    )
    bench_player_ids_json: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list, server_default="[]"
    )
    updated_by_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )


__all__ = ["ClubMatchPlan"]
