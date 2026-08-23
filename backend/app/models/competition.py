from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Index, Integer, JSON, String, event
from sqlalchemy.orm import Mapped, mapped_column

from app.common.enums.competition_format import CompetitionFormat
from app.common.enums.competition_start_mode import CompetitionStartMode
from app.common.enums.competition_status import CompetitionStatus
from app.common.enums.competition_visibility import CompetitionVisibility
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class UserCompetition(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_competitions"
    __table_args__ = (
        Index("ix_user_competitions_visibility_created_at", "visibility", "created_at"),
        Index("ix_user_competitions_format_visibility_created_at", "format", "visibility", "created_at"),
        Index("ix_user_competitions_host_user_id_created_at", "host_user_id", "created_at"),
        Index("ix_user_competitions_ranked_status", "is_ranked", "status"),
        Index("ix_user_competitions_mode_status", "competition_mode", "status"),
        Index("ix_user_competitions_prize_mode", "prize_mode"),
        Index("ix_user_competitions_registration_deadline", "registration_deadline"),
        Index("ix_user_competitions_featured_status", "featured", "status"),
    )

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
    registration_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
    is_ranked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    competition_mode: Mapped[str] = mapped_column(
        String(32), nullable=False, default="competition", server_default="competition"
    )
    prize_mode: Mapped[str] = mapped_column(
        String(32), nullable=False, default="entry_funded", server_default="entry_funded"
    )
    payout_mode: Mapped[str] = mapped_column(
        String(32), nullable=False, default="winner_takes_all", server_default="winner_takes_all"
    )
    host_funded_prize_total_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    host_funding_required_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    host_funding_escrowed_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    host_platform_fee_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    fixed_prizes_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    eligibility_rules_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    ranking_policy_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    manual_approval_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    online_now: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    def format_enum(self) -> CompetitionFormat:
        return CompetitionFormat(self.format)


Competition = UserCompetition


def _validate_competition_economic_contract(_: Any, __: Any, competition: UserCompetition) -> None:
    prize_mode = (competition.prize_mode or "entry_funded").strip().lower()
    currency = (competition.currency or "").strip().lower()
    entry_fee = int(competition.entry_fee_minor or 0)
    host_prize = int(competition.host_funded_prize_total_minor or 0)
    host_required = int(competition.host_funding_required_minor or 0)

    if prize_mode == "host_funded_fixed":
        if currency != "coin":
            raise ValueError("Host-funded prize competitions must use GTEX Coin.")
        if entry_fee != 0:
            raise ValueError("Host-funded GTEX Coin competitions cannot charge a participant Coin entry fee.")
        if host_prize <= 0 or host_required <= 0:
            raise ValueError("Host-funded GTEX Coin competitions require a positive funded prize.")
        return

    if entry_fee > 0 and currency != "credit":
        raise ValueError("Participant-funded competition entry fees must use FanCoin.")


event.listen(
    UserCompetition,
    "before_insert",
    _validate_competition_economic_contract,
    propagate=True,
)
event.listen(
    UserCompetition,
    "before_update",
    _validate_competition_economic_contract,
    propagate=True,
)


__all__ = ["Competition", "UserCompetition"]
