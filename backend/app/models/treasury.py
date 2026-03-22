from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any, TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, JSON, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.user import KycStatus
from app.models.wallet import LedgerUnit

if TYPE_CHECKING:
    from app.models.user import User


class RateDirection(StrEnum):
    FIAT_PER_COIN = "fiat_per_coin"
    COIN_PER_FIAT = "coin_per_fiat"


class PaymentMode(StrEnum):
    MANUAL = "manual"
    AUTOMATIC = "automatic"


class DepositStatus(StrEnum):
    AWAITING_PAYMENT = "awaiting_payment"
    PAYMENT_SUBMITTED = "payment_submitted"
    UNDER_REVIEW = "under_review"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    EXPIRED = "expired"
    DISPUTED = "disputed"


class TreasuryWithdrawalStatus(StrEnum):
    DRAFT = "draft"
    PENDING_KYC = "pending_kyc"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    PROCESSING = "processing"
    PAID = "paid"
    DISPUTED = "disputed"
    CANCELLED = "cancelled"


class TreasurySettings(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "treasury_settings"
    __table_args__ = (
        UniqueConstraint("settings_key", name="uq_treasury_settings_key"),
    )

    settings_key: Mapped[str] = mapped_column(String(32), nullable=False, default="default", server_default="default")
    currency_code: Mapped[str] = mapped_column(String(8), nullable=False, default="NGN", server_default="NGN")

    deposit_rate_value: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False, default=Decimal("0.0000"))
    deposit_rate_direction: Mapped[RateDirection] = mapped_column(
        Enum(RateDirection, name="rate_direction", native_enum=False),
        nullable=False,
        default=RateDirection.FIAT_PER_COIN,
    )
    withdrawal_rate_value: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False, default=Decimal("0.0000"))
    withdrawal_rate_direction: Mapped[RateDirection] = mapped_column(
        Enum(RateDirection, name="rate_direction", native_enum=False),
        nullable=False,
        default=RateDirection.FIAT_PER_COIN,
    )

    min_deposit: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=Decimal("0.0000"))
    max_deposit: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=Decimal("0.0000"))
    min_withdrawal: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=Decimal("0.0000"))
    max_withdrawal: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=Decimal("0.0000"))

    deposit_mode: Mapped[PaymentMode] = mapped_column(
        Enum(PaymentMode, name="payment_mode", native_enum=False),
        nullable=False,
        default=PaymentMode.MANUAL,
    )
    withdrawal_mode: Mapped[PaymentMode] = mapped_column(
        Enum(PaymentMode, name="payment_mode", native_enum=False),
        nullable=False,
        default=PaymentMode.MANUAL,
    )

    maintenance_message: Mapped[str | None] = mapped_column(String(255), nullable=True)
    whatsapp_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    active_bank_account_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("treasury_bank_accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    updated_by_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    active_bank_account: Mapped["TreasuryBankAccount | None"] = relationship(
        "TreasuryBankAccount",
        foreign_keys=[active_bank_account_id],
    )
    updated_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[updated_by_user_id],
    )


class TreasuryBankAccount(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "treasury_bank_accounts"

    currency_code: Mapped[str] = mapped_column(String(8), nullable=False, default="NGN", server_default="NGN")
    bank_name: Mapped[str] = mapped_column(String(120), nullable=False)
    account_number: Mapped[str] = mapped_column(String(32), nullable=False)
    account_name: Mapped[str] = mapped_column(String(120), nullable=False)
    bank_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")


class DepositRequest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "deposit_requests"
    __table_args__ = (
        UniqueConstraint("reference", name="uq_deposit_requests_reference"),
        Index("ix_deposit_requests_status", "status"),
        Index("ix_deposit_requests_created_at", "created_at"),
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reference: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[DepositStatus] = mapped_column(
        Enum(DepositStatus, name="deposit_status", native_enum=False),
        nullable=False,
        default=DepositStatus.AWAITING_PAYMENT,
    )
    amount_fiat: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    amount_coin: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(8), nullable=False, default="NGN", server_default="NGN")
    rate_value: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    rate_direction: Mapped[RateDirection] = mapped_column(
        Enum(RateDirection, name="rate_direction", native_enum=False),
        nullable=False,
    )

    bank_name: Mapped[str] = mapped_column(String(120), nullable=False)
    bank_account_number: Mapped[str] = mapped_column(String(32), nullable=False)
    bank_account_name: Mapped[str] = mapped_column(String(120), nullable=False)
    bank_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    bank_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    payer_name: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    sender_bank: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    transfer_reference: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    proof_attachment_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("attachments.id", ondelete="SET NULL"),
        nullable=True,
    )

    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    admin_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    admin_notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ledger_transaction_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    admin_user: Mapped["User | None"] = relationship("User", foreign_keys=[admin_user_id])


class UserBankAccount(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_bank_accounts"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    currency_code: Mapped[str] = mapped_column(String(8), nullable=False, default="NGN", server_default="NGN")
    bank_name: Mapped[str] = mapped_column(String(120), nullable=False)
    account_number: Mapped[str] = mapped_column(String(32), nullable=False)
    account_name: Mapped[str] = mapped_column(String(120), nullable=False)
    bank_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])


class KycProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "kyc_profiles"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_kyc_profiles_user_id"),
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[KycStatus] = mapped_column(
        Enum(KycStatus, name="kyc_status", native_enum=False),
        nullable=False,
        default=KycStatus.UNVERIFIED,
        index=True,
    )
    nin: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    bvn: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    address_line1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_line2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    state: Mapped[str | None] = mapped_column(String(120), nullable=True)
    country: Mapped[str | None] = mapped_column(String(120), nullable=True, default="Nigeria", server_default="Nigeria")
    id_document_attachment_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("attachments.id", ondelete="SET NULL"),
        nullable=True,
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewer_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    rejection_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    reviewer: Mapped["User | None"] = relationship("User", foreign_keys=[reviewer_user_id])


class TreasuryWithdrawalRequest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "treasury_withdrawal_requests"
    __table_args__ = (
        UniqueConstraint("reference", name="uq_treasury_withdrawal_reference"),
        UniqueConstraint("payout_request_id", name="uq_treasury_withdrawal_payout_request"),
        Index("ix_treasury_withdrawal_status", "status"),
        Index("ix_treasury_withdrawal_created_at", "created_at"),
    )

    payout_request_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("payout_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reference: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[TreasuryWithdrawalStatus] = mapped_column(
        Enum(TreasuryWithdrawalStatus, name="treasury_withdrawal_status", native_enum=False),
        nullable=False,
        default=TreasuryWithdrawalStatus.PENDING_REVIEW,
    )
    unit: Mapped[LedgerUnit] = mapped_column(
        Enum(LedgerUnit, name="ledger_unit", native_enum=False),
        nullable=False,
        default=LedgerUnit.COIN,
    )
    amount_coin: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    amount_fiat: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    fee_amount: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=Decimal("0.0000"), server_default="0.0000")
    net_amount: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=Decimal("0.0000"), server_default="0.0000")
    currency_code: Mapped[str] = mapped_column(String(8), nullable=False, default="NGN", server_default="NGN")
    rate_value: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    rate_direction: Mapped[RateDirection] = mapped_column(
        Enum(RateDirection, name="rate_direction", native_enum=False),
        nullable=False,
    )
    bank_name: Mapped[str] = mapped_column(String(120), nullable=False)
    bank_account_number: Mapped[str] = mapped_column(String(32), nullable=False)
    bank_account_name: Mapped[str] = mapped_column(String(120), nullable=False)
    bank_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    bank_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    kyc_status_snapshot: Mapped[str] = mapped_column(String(32), nullable=False, default="unverified")
    kyc_tier_snapshot: Mapped[str] = mapped_column(String(32), nullable=False, default="unverified")
    processor_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="manual_bank_transfer", server_default="manual_bank_transfer")
    payout_channel: Mapped[str] = mapped_column(String(64), nullable=False, default="bank_transfer", server_default="bank_transfer")
    source_scope: Mapped[str] = mapped_column(String(32), nullable=False, default="trade", server_default="trade")
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)

    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    admin_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    admin_notes: Mapped[str | None] = mapped_column(String(255), nullable=True)

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    admin_user: Mapped["User | None"] = relationship("User", foreign_keys=[admin_user_id])


class TreasuryAuditEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "treasury_audit_events"

    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    actor_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    actor_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    resource_type: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    resource_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    summary: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
