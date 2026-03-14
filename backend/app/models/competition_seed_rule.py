from __future__ import annotations

from typing import Any

from sqlalchemy import Boolean, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CompetitionSeedRule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "competition_seed_rules"
    __table_args__ = (
        UniqueConstraint("competition_id", name="uq_competition_seed_rules_competition_id"),
    )

    competition_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("user_competitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    seed_method: Mapped[str] = mapped_column(String(24), nullable=False, default="random", server_default="random")
    seed_source: Mapped[str] = mapped_column(String(32), nullable=False, default="rating", server_default="rating")
    allow_admin_override: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    lock_after_seed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = ["CompetitionSeedRule"]
