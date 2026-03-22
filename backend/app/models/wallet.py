from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, JSON, Numeric, String, UniqueConstraint, event
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class LedgerUnit(StrEnum):
    COIN = "coin"
    CREDIT = "credit"


class LedgerAccountKind(StrEnum):
    USER = "user"
    SYSTEM = "system"
    ESCROW = "escrow"


class LedgerEntryReason(StrEnum):
    DEPOSIT = "deposit"
    WITHDRAWAL_HOLD = "withdrawal_hold"
    WITHDRAWAL_SETTLEMENT = "withdrawal_settlement"
    ADJUSTMENT = "adjustment"
    TRADE_SETTLEMENT = "trade_settlement"
    COMPETITION_ENTRY = "competition_entry"
    COMPETITION_REWARD = "competition_reward"


class LedgerSourceTag(StrEnum):
    FANCOIN_PURCHASE = "fancoin_purchase"
    MARKET_TOPUP = "market_topup"
    PLATFORM_COMPETITION_REWARD = "platform_competition_reward"
    NATIONAL_COMPETITION_REWARD = "national_competition_reward"
    GTEX_PLATFORM_GIFT_INCOME = "gtex_platform_gift_income"
    USER_HOSTED_GIFT_INCOME_FANCOIN = "user_hosted_gift_income_fancoin"
    MATCH_VIEW_REVENUE = "match_view_revenue"
    HOSTING_FEE_SPEND = "hosting_fee_spend"
    USER_COMPETITION_ENTRY_SPEND = "user_competition_entry_spend"
    VIDEO_VIEW_SPEND = "video_view_spend"
    STADIUM_UPGRADE_SPEND = "stadium_upgrade_spend"
    COSMETIC_SPEND = "cosmetic_spend"
    PLAYER_CARD_SALE = "player_card_sale"
    PLAYER_CARD_PURCHASE = "player_card_purchase"
    CLUB_SALE_SALE = "club_sale_sale"
    CLUB_SALE_PURCHASE = "club_sale_purchase"
    CLUB_SALE_PLATFORM_FEE = "club_sale_platform_fee"
    TRADING_FEE_BURN = "trading_fee_burn"
    GIFT_RAKE_BURN = "gift_rake_burn"
    WITHDRAWAL_FEE_BURN = "withdrawal_fee_burn"
    PROMO_POOL_CREDIT = "promo_pool_credit"
    ADMIN_ADJUSTMENT = "admin_adjustment"
    HIGHLIGHT_DOWNLOAD_SPEND = "highlight_download_spend"


class PaymentProvider(StrEnum):
    MONNIFY = "monnify"
    FLUTTERWAVE = "flutterwave"
    PAYSTACK = "paystack"


class PaymentStatus(StrEnum):
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"
    REVERSED = "reversed"


class PayoutStatus(StrEnum):
    REQUESTED = "requested"
    REVIEWING = "reviewing"
    HELD = "held"
    PROCESSING = "processing"
    COMPLETED = "completed"
    REJECTED = "rejected"
    FAILED = "failed"


class LedgerAccount(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ledger_accounts"
    __table_args__ = (
        UniqueConstraint("owner_user_id", "unit", "kind", name="uq_ledger_accounts_owner_unit_kind"),
    )

    owner_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    unit: Mapped[LedgerUnit] = mapped_column(
        Enum(LedgerUnit, name="ledger_unit", native_enum=False),
        nullable=False,
    )
    kind: Mapped[LedgerAccountKind] = mapped_column(
        Enum(LedgerAccountKind, name="ledger_account_kind", native_enum=False),
        nullable=False,
        default=LedgerAccountKind.USER,
    )
    allow_negative: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")

    owner: Mapped["User | None"] = relationship(back_populates="ledger_accounts")
    entries: Mapped[list["LedgerEntry"]] = relationship(back_populates="account")
    payout_requests: Mapped[list["PayoutRequest"]] = relationship(back_populates="account")


class LedgerEntry(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "ledger_entries"

    transaction_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    account_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ledger_accounts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    created_by_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    unit: Mapped[LedgerUnit] = mapped_column(
        Enum(LedgerUnit, name="ledger_unit", native_enum=False),
        nullable=False,
    )
    source_tag: Mapped[LedgerSourceTag] = mapped_column(
        Enum(LedgerSourceTag, name="ledger_source_tag", native_enum=False),
        nullable=False,
        default=LedgerSourceTag.ADMIN_ADJUSTMENT,
        server_default=LedgerSourceTag.ADMIN_ADJUSTMENT.value,
    )
    reason: Mapped[LedgerEntryReason] = mapped_column(
        Enum(LedgerEntryReason, name="ledger_entry_reason", native_enum=False),
        nullable=False,
    )
    reference: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    external_reference: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    account: Mapped["LedgerAccount"] = relationship(back_populates="entries")
    created_by: Mapped["User | None"] = relationship(
        back_populates="ledger_entries_created",
        foreign_keys=[created_by_user_id],
    )


class PaymentEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "payment_events"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[PaymentProvider] = mapped_column(
        Enum(PaymentProvider, name="payment_provider", native_enum=False),
        nullable=False,
    )
    provider_reference: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    provider_event_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    pack_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    unit: Mapped[LedgerUnit] = mapped_column(
        Enum(LedgerUnit, name="ledger_unit", native_enum=False),
        nullable=False,
        default=LedgerUnit.COIN,
    )
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status", native_enum=False),
        nullable=False,
        default=PaymentStatus.PENDING,
    )
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ledger_transaction_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)

    user: Mapped["User"] = relationship(back_populates="payment_events")


class PayoutRequest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "payout_requests"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    account_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ledger_accounts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    unit: Mapped[LedgerUnit] = mapped_column(
        Enum(LedgerUnit, name="ledger_unit", native_enum=False),
        nullable=False,
    )
    status: Mapped[PayoutStatus] = mapped_column(
        Enum(PayoutStatus, name="payout_status", native_enum=False),
        nullable=False,
        default=PayoutStatus.REQUESTED,
    )
    destination_reference: Mapped[str] = mapped_column(String(255), nullable=False)
    hold_transaction_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    settlement_transaction_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)

    user: Mapped["User"] = relationship(back_populates="payout_requests")
    account: Mapped["LedgerAccount"] = relationship(back_populates="payout_requests")


@event.listens_for(LedgerEntry, "before_update", propagate=True)
def _prevent_ledger_entry_updates(_: Any, __: Any, ___: Any) -> None:
    raise ValueError("Ledger entries are append-only and cannot be updated.")


@event.listens_for(LedgerEntry, "before_delete", propagate=True)
def _prevent_ledger_entry_deletes(_: Any, __: Any, ___: Any) -> None:
    raise ValueError("Ledger entries are append-only and cannot be deleted.")
