from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.wallet import LedgerAccount, LedgerEntry, PaymentEvent, PayoutRequest


class UserRole(StrEnum):
    USER = "user"
    ADMIN = "admin"


class KycStatus(StrEnum):
    UNVERIFIED = "unverified"
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", native_enum=False),
        nullable=False,
        default=UserRole.USER,
    )
    kyc_status: Mapped[KycStatus] = mapped_column(
        Enum(KycStatus, name="kyc_status", native_enum=False),
        nullable=False,
        default=KycStatus.UNVERIFIED,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    ledger_accounts: Mapped[list["LedgerAccount"]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
    )
    ledger_entries_created: Mapped[list["LedgerEntry"]] = relationship(
        back_populates="created_by",
        foreign_keys="LedgerEntry.created_by_user_id",
    )
    payment_events: Mapped[list["PaymentEvent"]] = relationship(back_populates="user")
    payout_requests: Mapped[list["PayoutRequest"]] = relationship(back_populates="user")
