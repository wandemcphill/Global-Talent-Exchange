from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import Boolean, DateTime, Enum as SqlEnum, ForeignKey, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class HostedCompetitionStatus(str, Enum):
    DRAFT = "draft"
    OPEN = "open"
    LOCKED = "locked"
    LIVE = "live"
    COMPLETED = "completed"
    CANCELLED = "cancelled"




class HostedCompetitionSettlementStatus(str, Enum):
    PENDING = "pending"
    SETTLED = "settled"
    VOIDED = "voided"


class CompetitionTemplate(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "competition_templates"
    __table_args__ = (
        UniqueConstraint("template_key", name="uq_competition_templates_template_key"),
    )

    template_key: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    competition_type: Mapped[str] = mapped_column(String(80), nullable=False)
    team_type: Mapped[str] = mapped_column(String(80), nullable=False)
    age_grade: Mapped[str] = mapped_column(String(40), nullable=False, default='senior')
    cup_or_league: Mapped[str] = mapped_column(String(24), nullable=False, default='cup')
    participants: Mapped[int] = mapped_column(nullable=False, default=8)
    viewing_mode: Mapped[str] = mapped_column(String(40), nullable=False, default='standard')
    gift_rules: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    seeding_method: Mapped[str] = mapped_column(String(40), nullable=False, default='random')
    is_user_hostable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    entry_fee_fancoin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal('0.0000'))
    reward_pool_fancoin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal('0.0000'))
    platform_fee_bps: Mapped[int] = mapped_column(nullable=False, default=1000)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class UserHostedCompetition(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "user_hosted_competitions"

    template_id: Mapped[str] = mapped_column(ForeignKey("competition_templates.id", ondelete="RESTRICT"), nullable=False, index=True)
    host_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    slug: Mapped[str] = mapped_column(String(180), nullable=False, unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default='')
    status: Mapped[HostedCompetitionStatus] = mapped_column(SqlEnum(HostedCompetitionStatus, name='hostedcompetitionstatus'), nullable=False, default=HostedCompetitionStatus.DRAFT)
    visibility: Mapped[str] = mapped_column(String(24), nullable=False, default='public')
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lock_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    max_participants: Mapped[int] = mapped_column(nullable=False, default=8)
    entry_fee_fancoin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal('0.0000'))
    reward_pool_fancoin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal('0.0000'))
    platform_fee_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal('0.0000'))
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class UserHostedCompetitionParticipant(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "user_hosted_competition_participants"
    __table_args__ = (
        UniqueConstraint("competition_id", "user_id", name="uq_hosted_competition_participant_user"),
    )

    competition_id: Mapped[str] = mapped_column(ForeignKey("user_hosted_competitions.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    joined_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    entry_fee_fancoin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal('0.0000'))
    payout_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class HostedCompetitionStanding(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "hosted_competition_standings"
    __table_args__ = (
        UniqueConstraint("competition_id", "user_id", name="uq_hosted_competition_standing_user"),
    )

    competition_id: Mapped[str] = mapped_column(ForeignKey("user_hosted_competitions.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    final_rank: Mapped[int | None] = mapped_column(nullable=True)
    points: Mapped[int] = mapped_column(nullable=False, default=0)
    wins: Mapped[int] = mapped_column(nullable=False, default=0)
    draws: Mapped[int] = mapped_column(nullable=False, default=0)
    losses: Mapped[int] = mapped_column(nullable=False, default=0)
    goals_for: Mapped[int] = mapped_column(nullable=False, default=0)
    goals_against: Mapped[int] = mapped_column(nullable=False, default=0)
    payout_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal('0.0000'))
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class HostedCompetitionSettlement(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "hosted_competition_settlements"

    competition_id: Mapped[str] = mapped_column(ForeignKey("user_hosted_competitions.id", ondelete="CASCADE"), nullable=False, index=True)
    recipient_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    settlement_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[HostedCompetitionSettlementStatus] = mapped_column(SqlEnum(HostedCompetitionSettlementStatus, name='hostedcompetitionsettlementstatus'), nullable=False, default=HostedCompetitionSettlementStatus.PENDING)
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal('0.0000'))
    platform_fee_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal('0.0000'))
    net_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal('0.0000'))
    ledger_transaction_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    note: Mapped[str] = mapped_column(Text, nullable=False, default='')
    settled_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
