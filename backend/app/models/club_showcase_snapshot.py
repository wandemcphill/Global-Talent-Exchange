from __future__ import annotations

from typing import Any

from sqlalchemy import ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class ClubShowcaseSnapshot(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "club_showcase_snapshots"
    __table_args__ = (
        UniqueConstraint("snapshot_key", name="uq_club_showcase_snapshots_snapshot_key"),
    )

    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    snapshot_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    reputation_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    dynasty_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    featured_trophy_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    theme_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    showcase_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
