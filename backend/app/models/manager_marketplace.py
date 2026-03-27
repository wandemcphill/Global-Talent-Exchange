from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ManagerControlMode(StrEnum):
    HUMAN = "human"
    REAL_MANAGER = "real_manager"


class ManagerContractStatus(StrEnum):
    ACTIVE = "active"
    ENDED = "ended"


class ManagerProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "manager_profiles"
    __table_args__ = (
        UniqueConstraint("manager_id", name="uq_manager_profiles_manager_id"),
    )

    manager_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    preferred_style: Mapped[str] = mapped_column(String(64), nullable=False, default="balanced", server_default="balanced")
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
    "ManagerProfile",
]
