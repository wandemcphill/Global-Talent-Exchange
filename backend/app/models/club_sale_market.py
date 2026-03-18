from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from enum import StrEnum
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, JSON, Numeric, String, Text, UniqueConstraint, event, inspect
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin

AMOUNT_QUANTUM = Decimal("0.0001")
IMMUTABLE_SETTLED_TRANSFER_FIELDS = (
    "executed_sale_price",
    "platform_fee_amount",
    "seller_net_amount",
    "platform_fee_bps",
    "settlement_reference",
    "ledger_transaction_id",
    "seller_user_id",
    "buyer_user_id",
)


def _enum_values(enum_type: type[StrEnum]) -> list[str]:
    return [member.value for member in enum_type]


def _normalize_amount(value: Decimal | str | int | float | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value)).quantize(AMOUNT_QUANTUM, rounding=ROUND_HALF_UP)


class ClubSaleListingStatus(StrEnum):
    ACTIVE = "active"
    UNDER_OFFER = "under_offer"
    CANCELLED = "cancelled"
    TRANSFERRED = "transferred"
    EXPIRED = "expired"
    COMPLETED = "transferred"


class ClubSaleInquiryStatus(StrEnum):
    OPEN = "open"
    RESPONDED = "responded"
    CLOSED = "closed"
    ARCHIVED = "archived"
    REJECTED = "rejected"
    CLOSED_ON_TRANSFER = "closed_on_transfer"
    WITHDRAWN = "withdrawn"


class ClubSaleOfferStatus(StrEnum):
    PENDING = "pending"
    COUNTERED = "countered"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    SUPERSEDED = "superseded"
    CLOSED = "closed"
    EXECUTED = "executed"
    EXPIRED = "expired"
    COMPLETED = "executed"


class ClubSaleTransferStatus(StrEnum):
    PENDING = "pending"
    SETTLED = "settled"
    CANCELLED = "cancelled"
    FAILED = "failed"
    COMPLETED = "settled"


class ClubValuationSnapshot(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "club_valuation_snapshots"
    __table_args__ = (
        Index("ix_club_valuation_snapshots_club_id", "club_id"),
        Index("ix_club_valuation_snapshots_computed_by_user_id", "computed_by_user_id"),
    )

    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    computed_by_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    version_key: Mapped[str] = mapped_column(
        String(48),
        nullable=False,
        default="club_sale_v1",
        server_default="club_sale_v1",
    )
    total_value_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    first_team_value_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    reserve_squad_value_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    u19_squad_value_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    academy_value_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    stadium_value_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    paid_enhancements_value_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    total_improvements_value_coin: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0.0000",
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class ClubSaleListing(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "club_sale_listings"
    __table_args__ = (
        Index("ix_club_sale_listings_club_status", "club_id", "status"),
        Index("ix_club_sale_listings_status_visibility", "status", "visibility"),
        Index("ix_club_sale_listings_seller_status", "seller_user_id", "status"),
        UniqueConstraint("listing_id", name="uq_club_sale_listings_listing_id"),
    )

    listing_id: Mapped[str] = mapped_column(String(48), nullable=False)
    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    seller_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    visibility: Mapped[str] = mapped_column(String(24), nullable=False, default="public", server_default="public")
    status: Mapped[ClubSaleListingStatus] = mapped_column(
        Enum(ClubSaleListingStatus, name="club_sale_listing_status", native_enum=False, values_callable=_enum_values),
        nullable=False,
        default=ClubSaleListingStatus.ACTIVE,
        server_default=ClubSaleListingStatus.ACTIVE.value,
    )
    currency: Mapped[str] = mapped_column(String(12), nullable=False, default="coin", server_default="coin")
    asking_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    valuation_snapshot_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_valuation_snapshots.id", ondelete="RESTRICT"),
        nullable=False,
    )
    system_valuation_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    valuation_breakdown_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    valuation_refreshed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    @property
    def asking_price_coin(self) -> Decimal:
        return self.asking_price

    @asking_price_coin.setter
    def asking_price_coin(self, value: Decimal | str | int | float) -> None:
        normalized = _normalize_amount(value)
        self.asking_price = normalized if normalized is not None else Decimal("0.0000")

    @property
    def public_notes(self) -> str | None:
        return self.note

    @public_notes.setter
    def public_notes(self, value: str | None) -> None:
        self.note = value


class ClubSaleInquiry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "club_sale_inquiries"
    __table_args__ = (
        Index("ix_club_sale_inquiries_club_status", "club_id", "status"),
        Index("ix_club_sale_inquiries_buyer_status", "buyer_user_id", "status"),
        Index("ix_club_sale_inquiries_seller_status", "seller_user_id", "status"),
        UniqueConstraint("inquiry_id", name="uq_club_sale_inquiries_inquiry_id"),
    )

    inquiry_id: Mapped[str] = mapped_column(String(48), nullable=False)
    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    listing_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("club_sale_listings.id", ondelete="SET NULL"),
        nullable=True,
    )
    seller_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    buyer_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[ClubSaleInquiryStatus] = mapped_column(
        Enum(ClubSaleInquiryStatus, name="club_sale_inquiry_status", native_enum=False, values_callable=_enum_values),
        nullable=False,
        default=ClubSaleInquiryStatus.OPEN,
        server_default=ClubSaleInquiryStatus.OPEN.value,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    response_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    responded_by_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    @property
    def owner_user_id(self) -> str:
        return self.seller_user_id

    @owner_user_id.setter
    def owner_user_id(self, value: str) -> None:
        self.seller_user_id = value

    @property
    def inquiry_message(self) -> str:
        return self.message

    @inquiry_message.setter
    def inquiry_message(self, value: str) -> None:
        self.message = value

    @property
    def owner_response_message(self) -> str | None:
        return self.response_message

    @owner_response_message.setter
    def owner_response_message(self, value: str | None) -> None:
        self.response_message = value


class ClubSaleOffer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "club_sale_offers"
    __table_args__ = (
        Index("ix_club_sale_offers_club_status", "club_id", "status"),
        Index("ix_club_sale_offers_buyer_status", "buyer_user_id", "status"),
        Index("ix_club_sale_offers_counterparty_status", "counterparty_user_id", "status"),
        UniqueConstraint("offer_id", name="uq_club_sale_offers_offer_id"),
    )

    offer_id: Mapped[str] = mapped_column(String(48), nullable=False)
    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    listing_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("club_sale_listings.id", ondelete="SET NULL"),
        nullable=True,
    )
    inquiry_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("club_sale_inquiries.id", ondelete="SET NULL"),
        nullable=True,
    )
    parent_offer_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("club_sale_offers.id", ondelete="SET NULL"),
        nullable=True,
    )
    seller_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    buyer_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    proposer_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    counterparty_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    offer_type: Mapped[str] = mapped_column(String(24), nullable=False, default="offer", server_default="offer")
    status: Mapped[ClubSaleOfferStatus] = mapped_column(
        Enum(ClubSaleOfferStatus, name="club_sale_offer_status", native_enum=False, values_callable=_enum_values),
        nullable=False,
        default=ClubSaleOfferStatus.PENDING,
        server_default=ClubSaleOfferStatus.PENDING.value,
    )
    currency: Mapped[str] = mapped_column(String(12), nullable=False, default="coin", server_default="coin")
    offered_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    responded_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    responded_by_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    @property
    def offer_amount_coin(self) -> Decimal:
        return self.offered_price

    @offer_amount_coin.setter
    def offer_amount_coin(self, value: Decimal | str | int | float) -> None:
        normalized = _normalize_amount(value)
        self.offered_price = normalized if normalized is not None else Decimal("0.0000")

    @property
    def seller_response_message(self) -> str | None:
        return self.responded_message

    @seller_response_message.setter
    def seller_response_message(self, value: str | None) -> None:
        self.responded_message = value


class ClubSaleTransfer(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "club_sale_transfers"
    __table_args__ = (
        Index("ix_club_sale_transfers_club_id", "club_id"),
        Index("ix_club_sale_transfers_listing_id", "listing_id"),
        Index("ix_club_sale_transfers_offer_id", "offer_id"),
        Index("ix_club_sale_transfers_valuation_snapshot_id", "valuation_snapshot_id"),
        Index("ix_club_sale_transfers_seller_user_id", "seller_user_id"),
        Index("ix_club_sale_transfers_buyer_user_id", "buyer_user_id"),
        Index("ix_club_sale_transfers_status", "status"),
        Index("ix_club_sale_transfers_ledger_transaction_id", "ledger_transaction_id"),
        UniqueConstraint("transfer_id", name="uq_club_sale_transfers_transfer_id"),
        UniqueConstraint("offer_id", name="uq_club_sale_transfers_offer_id"),
        UniqueConstraint("settlement_reference", name="uq_club_sale_transfers_settlement_reference"),
    )

    transfer_id: Mapped[str] = mapped_column(String(48), nullable=False)
    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    listing_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("club_sale_listings.id", ondelete="SET NULL"),
        nullable=True,
    )
    offer_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_sale_offers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    valuation_snapshot_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("club_valuation_snapshots.id", ondelete="SET NULL"),
        nullable=True,
    )
    seller_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    buyer_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(String(12), nullable=False, default="coin", server_default="coin")
    executed_sale_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    platform_fee_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    seller_net_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    status: Mapped[ClubSaleTransferStatus] = mapped_column(
        Enum(ClubSaleTransferStatus, name="club_sale_transfer_status", native_enum=False, values_callable=_enum_values),
        nullable=False,
        default=ClubSaleTransferStatus.SETTLED,
        server_default=ClubSaleTransferStatus.SETTLED.value,
    )
    platform_fee_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=1000, server_default="1000")
    settlement_reference: Mapped[str] = mapped_column(String(128), nullable=False)
    ledger_transaction_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    @property
    def executed_sale_price_coin(self) -> Decimal:
        return self.executed_sale_price

    @executed_sale_price_coin.setter
    def executed_sale_price_coin(self, value: Decimal | str | int | float) -> None:
        normalized = _normalize_amount(value)
        self.executed_sale_price = normalized if normalized is not None else Decimal("0.0000")

    @property
    def platform_fee_coin(self) -> Decimal:
        return self.platform_fee_amount

    @platform_fee_coin.setter
    def platform_fee_coin(self, value: Decimal | str | int | float) -> None:
        normalized = _normalize_amount(value)
        self.platform_fee_amount = normalized if normalized is not None else Decimal("0.0000")

    @property
    def seller_net_coin(self) -> Decimal:
        return self.seller_net_amount

    @seller_net_coin.setter
    def seller_net_coin(self, value: Decimal | str | int | float) -> None:
        normalized = _normalize_amount(value)
        self.seller_net_amount = normalized if normalized is not None else Decimal("0.0000")

    @property
    def fee_bps(self) -> int:
        return int(self.platform_fee_bps)

    @fee_bps.setter
    def fee_bps(self, value: int) -> None:
        self.platform_fee_bps = int(value)

    @property
    def accepted_offer_id(self) -> str:
        return self.offer_id

    @accepted_offer_id.setter
    def accepted_offer_id(self, value: str) -> None:
        self.offer_id = value


class ClubSaleAuditEvent(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "club_sale_audit_events"
    __table_args__ = (
        Index("ix_club_sale_audit_events_club_action", "club_id", "action"),
        Index("ix_club_sale_audit_events_actor_user_id", "actor_user_id"),
        Index("ix_club_sale_audit_events_listing_id", "listing_id"),
        Index("ix_club_sale_audit_events_inquiry_id", "inquiry_id"),
        Index("ix_club_sale_audit_events_offer_id", "offer_id"),
        Index("ix_club_sale_audit_events_transfer_id", "transfer_id"),
    )

    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    listing_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("club_sale_listings.id", ondelete="SET NULL"),
        nullable=True,
    )
    inquiry_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("club_sale_inquiries.id", ondelete="SET NULL"),
        nullable=True,
    )
    offer_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("club_sale_offers.id", ondelete="SET NULL"),
        nullable=True,
    )
    transfer_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("club_sale_transfers.id", ondelete="SET NULL"),
        nullable=True,
    )
    actor_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    status_from: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status_to: Mapped[str | None] = mapped_column(String(32), nullable=True)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


@event.listens_for(ClubSaleTransfer, "before_insert")
@event.listens_for(ClubSaleTransfer, "before_update")
def _normalize_transfer_amounts(_mapper, _connection, target: ClubSaleTransfer) -> None:
    target.executed_sale_price = _normalize_amount(target.executed_sale_price) or Decimal("0.0000")
    target.platform_fee_amount = _normalize_amount(target.platform_fee_amount) or Decimal("0.0000")
    target.seller_net_amount = _normalize_amount(target.seller_net_amount) or Decimal("0.0000")


@event.listens_for(ClubSaleTransfer, "before_update")
def _prevent_settled_transfer_mutation(_mapper, _connection, target: ClubSaleTransfer) -> None:
    state = inspect(target)
    status_history = state.attrs.status.history
    prior_status = status_history.deleted[0] if status_history.deleted else target.status
    if prior_status != ClubSaleTransferStatus.SETTLED and target.status == ClubSaleTransferStatus.SETTLED:
        return
    if target.status != ClubSaleTransferStatus.SETTLED:
        return
    for field_name in IMMUTABLE_SETTLED_TRANSFER_FIELDS:
        if state.attrs[field_name].history.has_changes():
            raise ValueError("Settled club sale transfer settlement fields are immutable.")


@event.listens_for(ClubSaleAuditEvent, "before_update")
def _prevent_audit_update(_mapper, _connection, _target: ClubSaleAuditEvent) -> None:
    raise ValueError("Club sale audit events are append-only and cannot be updated.")


@event.listens_for(ClubSaleAuditEvent, "before_delete")
def _prevent_audit_delete(_mapper, _connection, _target: ClubSaleAuditEvent) -> None:
    raise ValueError("Club sale audit events are append-only and cannot be deleted.")


__all__ = [
    "ClubSaleAuditEvent",
    "ClubSaleInquiry",
    "ClubSaleInquiryStatus",
    "ClubSaleListing",
    "ClubSaleListingStatus",
    "ClubSaleOffer",
    "ClubSaleOfferStatus",
    "ClubSaleTransfer",
    "ClubSaleTransferStatus",
    "ClubValuationSnapshot",
]
