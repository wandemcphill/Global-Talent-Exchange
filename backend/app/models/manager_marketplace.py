from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import Boolean, Date, DateTime, Enum, Float, ForeignKey, Integer, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ManagerControlMode(StrEnum):
    HUMAN = "human"
    REAL_MANAGER = "real_manager"


class ManagerContractStatus(StrEnum):
    ACTIVE = "active"
    ENDED = "ended"


class ManagerPersonalityTacticalStyle(StrEnum):
    ATTACKING = "attacking"
    DEFENSIVE = "defensive"
    BALANCED = "balanced"


class ManagerDisciplineStyle(StrEnum):
    STRICT = "strict"
    BALANCED = "balanced"
    EMPOWERING = "empowering"


class ManagerProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "manager_profiles"
    __table_args__ = (
        UniqueConstraint("manager_id", name="uq_manager_profiles_manager_id"),
        UniqueConstraint("gtex_ai_id", name="uq_manager_profiles_gtex_ai_id"),
    )

    manager_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    gtex_ai_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("gtex_ai_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    preferred_style: Mapped[str] = mapped_column(String(64), nullable=False, default="balanced", server_default="balanced")
    tactical_style: Mapped[ManagerPersonalityTacticalStyle] = mapped_column(
        Enum(ManagerPersonalityTacticalStyle, name="manager_personality_tactical_style", native_enum=False),
        nullable=False,
        default=ManagerPersonalityTacticalStyle.BALANCED,
        server_default=ManagerPersonalityTacticalStyle.BALANCED.value,
    )
    risk_tolerance: Mapped[float] = mapped_column(Float, nullable=False, default=0.5, server_default="0.5")
    adaptability: Mapped[float] = mapped_column(Float, nullable=False, default=0.5, server_default="0.5")
    ego_level: Mapped[float] = mapped_column(Float, nullable=False, default=0.5, server_default="0.5")
    youth_preference: Mapped[float] = mapped_column(Float, nullable=False, default=0.5, server_default="0.5")
    discipline_style: Mapped[ManagerDisciplineStyle] = mapped_column(
        Enum(ManagerDisciplineStyle, name="manager_discipline_style", native_enum=False),
        nullable=False,
        default=ManagerDisciplineStyle.BALANCED,
        server_default=ManagerDisciplineStyle.BALANCED.value,
    )
    formation_preferences_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    substitution_logic: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="balanced_rotation",
        server_default="balanced_rotation",
    )
    tempo_control: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default="balanced",
        server_default="balanced",
    )
    control_mode: Mapped[ManagerControlMode] = mapped_column(
        Enum(ManagerControlMode, name="manager_control_mode", native_enum=False),
        nullable=False,
        default=ManagerControlMode.HUMAN,
        server_default=ManagerControlMode.HUMAN.value,
    )
    matches_managed: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    wins: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    losses: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    reputation_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    hourly_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"), server_default="0")
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    current_losing_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")


class ManagerContract(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "manager_contracts"

    manager_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    club_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    agreed_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"), server_default="0")
    payment_unit: Mapped[str] = mapped_column(String(16), nullable=False, default="credit", server_default="credit")
    settlement_status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending", server_default="pending")
    ledger_transaction_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    settlement_metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[ManagerContractStatus] = mapped_column(
        Enum(ManagerContractStatus, name="manager_contract_status", native_enum=False),
        nullable=False,
        default=ManagerContractStatus.ACTIVE,
        server_default=ManagerContractStatus.ACTIVE.value,
        index=True,
    )


__all__ = [
    "ManagerContract",
    "ManagerContractStatus",
    "ManagerControlMode",
    "ManagerDisciplineStyle",
    "ManagerPersonalityTacticalStyle",
    "ManagerProfile",
]
