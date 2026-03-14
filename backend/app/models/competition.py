from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.common.enums.competition_format import CompetitionFormat
from backend.app.common.enums.competition_start_mode import CompetitionStartMode
from backend.app.common.enums.competition_status import CompetitionStatus
from backend.app.common.enums.competition_visibility import CompetitionVisibility
from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class UserCompetition(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_competitions"

    host_user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    competition_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=CompetitionFormat.LEAGUE.value,
        server_default=CompetitionFormat.LEAGUE.value,
    )
    source_type: Mapped[str | None] = mapped_column(String(48), nullable=True, index=True)
    source_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    format: Mapped[str] = mapped_column(String(24), nullable=False)
    visibility: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default=CompetitionVisibility.PUBLIC.value,
        server_default=CompetitionVisibility.PUBLIC.value,
    )
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default=CompetitionStatus.DRAFT.value,
        server_default=CompetitionStatus.DRAFT.value,
    )
    start_mode: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default=CompetitionStartMode.SCHEDULED.value,
        server_default=CompetitionStartMode.SCHEDULED.value,
    )
    scheduled_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    seeded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    launched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stage: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="registration",
        server_default="registration",
    )

    currency: Mapped[str] = mapped_column(String(12), nullable=False)
    entry_fee_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    platform_fee_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    host_fee_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    host_creation_fee_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    gross_pool_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    net_prize_pool_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    def format_enum(self) -> CompetitionFormat:
        return CompetitionFormat(self.format)


Competition = UserCompetition

__all__ = ["Competition", "UserCompetition"]
