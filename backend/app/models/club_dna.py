from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class DNAPhilosophy(StrEnum):
    YOUTH_DEVELOPMENT = "youth_development"
    SELLING_CLUB = "selling_club"
    ACADEMY_FIRST = "academy_first"
    SUPERSTAR = "superstar"
    BIG_SPENDING = "big_spending"
    FINANCIALLY_SUSTAINABLE = "sustainable"
    NATIONALITY_FOCUSED = "nationality_focused"
    REGIONAL_IDENTITY = "regional"
    BALANCED = "balanced"


class PolicyNationalityMode(StrEnum):
    NONE = "none"
    PREFERRED = "preferred"
    EXCLUSIVE = "exclusive"


class PolicyAgeMode(StrEnum):
    NONE = "none"
    PREFERRED = "preferred"
    STRICT = "strict"


class TransferStrategy(StrEnum):
    BUY_YOUNG_DEVELOP_SELL = "buy_young_develop_sell"
    ACADEMY_PRODUCTION = "academy_production"
    BUY_ESTABLISHED = "buy_established"
    BUY_UNDERVALUED = "buy_undervalued"
    FIRST_TEAM_PROMOTION = "first_team_promotion"
    SUPERSTARS = "superstars"
    BALANCED = "balanced"


class FinancialPhilosophy(StrEnum):
    SUSTAINABLE = "sustainable"
    BIG_SPENDING = "big_spending"
    ACADEMY_FOCUSED = "academy_focused"
    BALANCED = "balanced"


class ExceptionStatus(StrEnum):
    APPROVED = "approved"
    REVOKED = "revoked"


class ClubDNAPolicy(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "club_dna_policies"
    __table_args__ = (
        UniqueConstraint("club_id", name="uq_club_dna_policies_club_id"),
        Index("ix_club_dna_policies_club_id", "club_id"),
        Index("ix_club_dna_policies_primary_philosophy", "primary_philosophy"),
        Index("ix_club_dna_policies_nationality_mode", "nationality_mode"),
        Index("ix_club_dna_policies_age_mode", "age_mode"),
    )

    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    primary_philosophy: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=DNAPhilosophy.BALANCED.value,
        server_default=DNAPhilosophy.BALANCED.value,
    )
    secondary_philosophies: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    nationality_mode: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=PolicyNationalityMode.NONE.value,
        server_default=PolicyNationalityMode.NONE.value,
    )
    target_nationalities: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    allow_dual_nationality: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
    )
    age_mode: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=PolicyAgeMode.NONE.value,
        server_default=PolicyAgeMode.NONE.value,
    )
    preferred_max_age: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    allow_age_exceptions: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
    )
    transfer_strategy: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=TransferStrategy.BALANCED.value,
        server_default=TransferStrategy.BALANCED.value,
    )
    financial_philosophy: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=FinancialPhilosophy.BALANCED.value,
        server_default=FinancialPhilosophy.BALANCED.value,
    )
    club_vision_narrative: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )


class ClubGovernanceException(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "club_governance_exceptions"
    __table_args__ = (
        Index("ix_club_governance_exceptions_club_id", "club_id"),
        Index("ix_club_governance_exceptions_policy_type", "policy_type"),
        Index("ix_club_governance_exceptions_player_id", "player_id"),
    )

    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    policy_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    player_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
    )
    player_name: Mapped[str] = mapped_column(
        String(160),
        nullable=False,
    )
    player_nationality: Mapped[str | None] = mapped_column(
        String(96),
        nullable=True,
    )
    player_age: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    approved_by_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ExceptionStatus.APPROVED.value,
        server_default=ExceptionStatus.APPROVED.value,
    )
    approved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
