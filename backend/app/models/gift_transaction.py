from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.economic_conversion import EconomicConversion
from app.models.wallet import LedgerUnit

if TYPE_CHECKING:
    from app.models.economy_config import GiftCatalogItem
    from app.models.user import User


class GiftTransactionStatus(StrEnum):
    SETTLED = "settled"
    REFUNDED = "refunded"


class GiftTransaction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "gift_transactions"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_gift_transactions_idempotency_key"),)

    sender_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recipient_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    gift_catalog_item_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("gift_catalog.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    recipient_type: Mapped[str] = mapped_column(String(32), nullable=False, default="user", server_default="user")
    recipient_entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    chat_thread_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    discussion_thread_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    discussion_reply_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    match_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    competition_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=1, server_default="1.0000")
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    platform_rake_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    recipient_net_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    source_scope: Mapped[str] = mapped_column(
        String(32), nullable=False, default="user_hosted", server_default="user_hosted"
    )
    # Deprecated compatibility field. New code must use source_ledger_unit and destination_ledger_unit.
    ledger_unit: Mapped[LedgerUnit] = mapped_column(
        Enum(LedgerUnit, name="ledger_unit", native_enum=False),
        nullable=False,
        default=LedgerUnit.CREDIT,
    )
    source_ledger_unit: Mapped[LedgerUnit] = mapped_column(
        Enum(LedgerUnit, name="gift_source_ledger_unit", native_enum=False),
        nullable=False,
        default=LedgerUnit.CREDIT,
        server_default=LedgerUnit.CREDIT.value,
    )
    destination_ledger_unit: Mapped[LedgerUnit] = mapped_column(
        Enum(LedgerUnit, name="gift_destination_ledger_unit", native_enum=False),
        nullable=False,
        default=LedgerUnit.COIN,
        server_default=LedgerUnit.COIN.value,
    )
    economic_conversion_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("economic_conversions.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
        index=True,
    )
    conversion_rate: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False, default=1, server_default="1")
    ledger_transaction_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    wallet_debit_ledger_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    wallet_credit_ledger_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    platform_fee_ledger_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    animation_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sound_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    abuse_status: Mapped[str] = mapped_column(String(32), nullable=False, default="clean", server_default="clean")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[GiftTransactionStatus] = mapped_column(
        Enum(GiftTransactionStatus, name="gift_transaction_status", native_enum=False),
        nullable=False,
        default=GiftTransactionStatus.SETTLED,
        server_default="settled",
    )

    sender_user: Mapped["User"] = relationship(foreign_keys=[sender_user_id])
    recipient_user: Mapped["User"] = relationship(foreign_keys=[recipient_user_id])
    gift_catalog_item: Mapped["GiftCatalogItem"] = relationship()


class GiftStats(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "gift_stats"
    __table_args__ = (UniqueConstraint("entity_type", "entity_id", name="uq_gift_stats_entity"),)

    entity_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    total_gifts_received: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    total_fan_coin_received: Mapped[Decimal] = mapped_column(
        Numeric(20, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0.0000",
    )
    total_unique_senders: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    top_gift_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mythic_gifts_received: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")


class GiftAbuseFlag(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "gift_abuse_flags"
    __table_args__ = (UniqueConstraint("flag_key", name="uq_gift_abuse_flags_flag_key"),)

    flag_key: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    sender_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    recipient_type: Mapped[str] = mapped_column(String(32), nullable=False, default="user", server_default="user")
    recipient_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    gift_transaction_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("gift_transactions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    flag_type: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="medium", server_default="medium")
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="open", server_default="open")
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
