from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    JSON,
    Numeric,
    String,
    UniqueConstraint,
    event,
    func,
)
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


class LedgerTransactionType(StrEnum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    MATCH_ENTRY_FEE = "match_entry_fee"
    MATCH_REWARD = "match_reward"
    LOTTERY_REWARD = "lottery_reward"
    TRADE_BUY = "trade_buy"
    TRADE_SELL = "trade_sell"
    ADJUSTMENT = "adjustment"
    CONVERSION = "conversion"
    PROMO_POOL_CREDIT = "promo_pool_credit"


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
    PLAYER_SHARE_PURCHASE = "player_share_purchase"
    PLAYER_SHARE_SALE = "player_share_sale"
    PLAYER_SHARE_DIVIDEND = "player_share_dividend"
    CLUB_SALE_SALE = "club_sale_sale"
    CLUB_SALE_PURCHASE = "club_sale_purchase"
    CLUB_SALE_PLATFORM_FEE = "club_sale_platform_fee"
    TRADING_FEE_BURN = "trading_fee_burn"
    GIFT_RAKE_BURN = "gift_rake_burn"
    WITHDRAWAL_FEE_BURN = "withdrawal_fee_burn"
    PROMO_POOL_CREDIT = "promo_pool_credit"
    ADMIN_ADJUSTMENT = "admin_adjustment"
    HIGHLIGHT_DOWNLOAD_SPEND = "highlight_download_spend"
    CREATOR_CLIP_REVENUE = "creator_clip_revenue"
    COIN_TRADER_ESCROW_LOCK = "coin_trader_escrow_lock"
    COIN_TRADER_ESCROW_RELEASE = "coin_trader_escrow_release"
    COIN_TRADER_ESCROW_REFUND = "coin_trader_escrow_refund"
    COIN_TRADER_FEE = "coin_trader_fee"
    COIN_TRADER_ADMIN_RESOLUTION = "coin_trader_admin_resolution"
    AGENT_BOOST_SPEND = "agent_boost_spend"
    AGENT_PERFORMANCE_EARNINGS = "agent_performance_earnings"


class PaymentProvider(StrEnum):
    MONNIFY = "monnify"
    FLUTTERWAVE = "flutterwave"
    PAYSTACK = "paystack"
    KORAPAY = "korapay"


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


class LedgerTransactionStatus(StrEnum):
    PENDING = "pending"
    COMMITTED = "committed"
    FAILED = "failed"


class LedgerAccount(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "wallets"
    __table_args__ = (UniqueConstraint("owner_user_id", "unit", "kind", name="uq_wallets_owner_unit_kind"),)

    owner_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    unit: Mapped[LedgerUnit] = mapped_column(Enum(LedgerUnit, name="ledger_unit", native_enum=False), nullable=False)
    kind: Mapped[LedgerAccountKind] = mapped_column(
        Enum(LedgerAccountKind, name="ledger_account_kind", native_enum=False),
        nullable=False,
        default=LedgerAccountKind.USER,
    )
    allow_negative: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")

    owner: Mapped["User | None"] = relationship(back_populates="ledger_accounts")
    entries: Mapped[list["LedgerEntry"]] = relationship(back_populates="account")
    payout_requests: Mapped[list["PayoutRequest"]] = relationship(back_populates="account")  # noqa: F821


class LedgerTransaction(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "transactions"

    status: Mapped[LedgerTransactionStatus] = mapped_column(
        Enum(LedgerTransactionStatus, name="ledger_transaction_status", native_enum=False),
        nullable=False,
        default=LedgerTransactionStatus.PENDING,
        server_default=LedgerTransactionStatus.PENDING.value,
    )
    reason: Mapped[LedgerEntryReason] = mapped_column(
        Enum(LedgerEntryReason, name="ledger_entry_reason", native_enum=False),
        nullable=False,
    )
    source_tag: Mapped[LedgerSourceTag] = mapped_column(
        Enum(LedgerSourceTag, name="ledger_source_tag", native_enum=False),
        nullable=False,
        default=LedgerSourceTag.ADMIN_ADJUSTMENT,
        server_default=LedgerSourceTag.ADMIN_ADJUSTMENT.value,
    )
    reference: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    external_reference: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_by_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    committed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    entries: Mapped[list["LedgerEntry"]] = relationship(back_populates="transaction")


class LedgerEntry(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "ledger_entries"
    __table_args__ = (CheckConstraint("amount <> 0", name="ck_ledger_entries_amount_non_zero"),)

    transaction_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("transactions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("wallets.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    created_by_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    unit: Mapped[LedgerUnit] = mapped_column(Enum(LedgerUnit, name="ledger_unit", native_enum=False), nullable=False)
    source_tag: Mapped[LedgerSourceTag] = mapped_column(
        Enum(LedgerSourceTag, name="ledger_source_tag", native_enum=False),
        nullable=False,
        default=LedgerSourceTag.ADMIN_ADJUSTMENT,
        server_default=LedgerSourceTag.ADMIN_ADJUSTMENT.value,
    )
    reason: Mapped[LedgerEntryReason] = mapped_column(
        Enum(LedgerEntryReason, name="ledger_entry_reason", native_enum=False), nullable=False
    )
    transaction_type: Mapped[LedgerTransactionType] = mapped_column(
        Enum(LedgerTransactionType, name="ledger_transaction_type", native_enum=False),
        nullable=False,
        default=LedgerTransactionType.ADJUSTMENT,
        server_default=LedgerTransactionType.ADJUSTMENT.value,
    )
    reference: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    external_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    transaction: Mapped["LedgerTransaction"] = relationship(back_populates="entries")
    account: Mapped["LedgerAccount"] = relationship(back_populates="entries")
    created_by: Mapped["User | None"] = relationship(
        back_populates="ledger_entries_created", foreign_keys=[created_by_user_id]
    )


class LedgerBalanceProjection(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ledger_balance_projections"
    __table_args__ = (UniqueConstraint("account_id", name="uq_ledger_balance_projections_account"),)

    account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    owner_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    unit: Mapped[LedgerUnit] = mapped_column(Enum(LedgerUnit, name="ledger_unit", native_enum=False), nullable=False)
    balance: Mapped[Decimal] = mapped_column(
        Numeric(20, 4), nullable=False, default=Decimal("0.0000"), server_default="0.0000"
    )
    last_transaction_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True, index=True
    )


class PaymentEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "payment_events"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[PaymentProvider] = mapped_column(
        Enum(PaymentProvider, name="payment_provider", native_enum=False), nullable=False
    )
    provider_reference: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    provider_event_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    pack_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    unit: Mapped[LedgerUnit] = mapped_column(
        Enum(LedgerUnit, name="ledger_unit", native_enum=False), nullable=False, default=LedgerUnit.COIN
    )
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status", native_enum=False), nullable=False, default=PaymentStatus.PENDING
    )
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ledger_transaction_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True, index=True
    )

    user: Mapped["User"] = relationship(back_populates="payment_events")


class PayoutRequest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "payout_requests"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("wallets.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    unit: Mapped[LedgerUnit] = mapped_column(Enum(LedgerUnit, name="ledger_unit", native_enum=False), nullable=False)
    status: Mapped[PayoutStatus] = mapped_column(
        Enum(PayoutStatus, name="payout_status", native_enum=False), nullable=False, default=PayoutStatus.REQUESTED
    )
    destination_reference: Mapped[str] = mapped_column(String(255), nullable=False)
    hold_transaction_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    settlement_transaction_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Replay protection for withdrawal submission. Nullable so historical rows
    # and internal callers that supply no intent key stay valid; the unique
    # index makes a duplicate submission fail at the database rather than
    # creating a second hold and a second payout record.
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True, unique=True)

    user: Mapped["User"] = relationship(back_populates="payout_requests")
    account: Mapped["LedgerAccount"] = relationship(back_populates="payout_requests")


@event.listens_for(LedgerEntry, "before_update", propagate=True)
def _prevent_ledger_entry_updates(_: Any, __: Any, ___: Any) -> None:
    raise ValueError("Ledger entries are append-only and cannot be updated.")


@event.listens_for(LedgerEntry, "before_delete", propagate=True)
def _prevent_ledger_entry_deletes(_: Any, __: Any, ___: Any) -> None:
    raise ValueError("Ledger entries are append-only and cannot be deleted.")


Wallet = LedgerAccount
Transaction = LedgerTransaction
