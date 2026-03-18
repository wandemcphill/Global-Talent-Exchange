from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, JSON, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin


class CreatorCard(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "creator_cards"
    __table_args__ = (
        UniqueConstraint("player_id", name="uq_creator_cards_player_id"),
        Index("ix_creator_cards_owner_creator_profile_id", "owner_creator_profile_id"),
    )

    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
    )
    owner_creator_profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("creator_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active", server_default="active")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class CreatorCardListing(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "creator_card_listings"
    __table_args__ = (
        Index("ix_creator_card_listings_creator_card_id", "creator_card_id"),
        Index("ix_creator_card_listings_seller_creator_profile_id", "seller_creator_profile_id"),
        Index("ix_creator_card_listings_status", "status"),
    )

    creator_card_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("creator_cards.id", ondelete="CASCADE"),
        nullable=False,
    )
    seller_creator_profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("creator_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    price_credits: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="open", server_default="open")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class CreatorCardSale(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "creator_card_sales"
    __table_args__ = (
        UniqueConstraint("settlement_reference", name="uq_creator_card_sales_settlement_reference"),
        Index("ix_creator_card_sales_creator_card_id", "creator_card_id"),
        Index("ix_creator_card_sales_buyer_creator_profile_id", "buyer_creator_profile_id"),
    )

    creator_card_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("creator_cards.id", ondelete="CASCADE"),
        nullable=False,
    )
    listing_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("creator_card_listings.id", ondelete="SET NULL"),
        nullable=True,
    )
    seller_creator_profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("creator_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    buyer_creator_profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("creator_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    price_credits: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    settlement_reference: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="settled", server_default="settled")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class CreatorCardSwap(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "creator_card_swaps"
    __table_args__ = (
        Index("ix_creator_card_swaps_proposer_creator_profile_id", "proposer_creator_profile_id"),
        Index("ix_creator_card_swaps_counterparty_creator_profile_id", "counterparty_creator_profile_id"),
        Index("ix_creator_card_swaps_status", "status"),
    )

    proposer_creator_profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("creator_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    counterparty_creator_profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("creator_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    proposer_card_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("creator_cards.id", ondelete="CASCADE"),
        nullable=False,
    )
    counterparty_card_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("creator_cards.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="executed", server_default="executed")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class CreatorCardLoan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "creator_card_loans"
    __table_args__ = (
        Index("ix_creator_card_loans_creator_card_id", "creator_card_id"),
        Index("ix_creator_card_loans_lender_creator_profile_id", "lender_creator_profile_id"),
        Index("ix_creator_card_loans_borrower_creator_profile_id", "borrower_creator_profile_id"),
        Index("ix_creator_card_loans_status", "status"),
    )

    creator_card_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("creator_cards.id", ondelete="CASCADE"),
        nullable=False,
    )
    lender_creator_profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("creator_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    borrower_creator_profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("creator_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    loan_fee_credits: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active", server_default="active")
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    returned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = [
    "CreatorCard",
    "CreatorCardListing",
    "CreatorCardLoan",
    "CreatorCardSale",
    "CreatorCardSwap",
]
