from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class CardLoanListing(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "card_loan_listings"
    __table_args__ = (
        Index("ix_card_loan_listings_player_card_id", "player_card_id"),
        Index("ix_card_loan_listings_owner_user_id", "owner_user_id"),
        Index("ix_card_loan_listings_status", "status"),
        Index("ix_card_loan_listings_status_negotiable", "status", "is_negotiable"),
        Index("ix_card_loan_listings_status_fee_duration", "status", "loan_fee_credits", "duration_days"),
    )

    player_card_id: Mapped[str] = mapped_column(String(36), ForeignKey("player_cards.id", ondelete="CASCADE"), nullable=False)
    owner_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    total_slots: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    available_slots: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False, default=7, server_default="7")
    loan_fee_credits: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0")
    currency: Mapped[str] = mapped_column(String(12), nullable=False, default="coin", server_default="coin")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="open", server_default="open")
    is_negotiable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    usage_restrictions_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    borrower_rights_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    lender_restrictions_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    terms_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class CardLoanNegotiation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "card_loan_negotiations"
    __table_args__ = (
        Index("ix_card_loan_negotiations_listing_id", "listing_id"),
        Index("ix_card_loan_negotiations_borrower_user_id", "borrower_user_id"),
        Index("ix_card_loan_negotiations_proposer_user_id", "proposer_user_id"),
        Index("ix_card_loan_negotiations_status", "status"),
        Index("ix_card_loan_negotiations_supersedes", "supersedes_negotiation_id"),
    )

    listing_id: Mapped[str] = mapped_column(String(36), ForeignKey("card_loan_listings.id", ondelete="CASCADE"), nullable=False)
    player_card_id: Mapped[str] = mapped_column(String(36), ForeignKey("player_cards.id", ondelete="CASCADE"), nullable=False)
    owner_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    borrower_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    proposer_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    counterparty_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    proposed_duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    proposed_loan_fee_credits: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending", server_default="pending")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    supersedes_negotiation_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("card_loan_negotiations.id", ondelete="SET NULL"),
        nullable=True,
    )
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    requested_terms_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class CardLoanContract(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "card_loan_contracts"
    __table_args__ = (
        Index("ix_card_loan_contracts_listing_id", "listing_id"),
        Index("ix_card_loan_contracts_negotiation_id", "accepted_negotiation_id"),
        Index("ix_card_loan_contracts_borrower_user_id", "borrower_user_id"),
        Index("ix_card_loan_contracts_status", "status"),
        Index("ix_card_loan_contracts_due_at", "due_at"),
        Index("ix_card_loan_contracts_settlement_reference", "settlement_reference"),
    )

    listing_id: Mapped[str] = mapped_column(String(36), ForeignKey("card_loan_listings.id", ondelete="CASCADE"), nullable=False)
    accepted_negotiation_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("card_loan_negotiations.id", ondelete="SET NULL"),
        nullable=True,
    )
    player_card_id: Mapped[str] = mapped_column(String(36), ForeignKey("player_cards.id", ondelete="CASCADE"), nullable=False)
    owner_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    borrower_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    loan_fee_credits: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0")
    requested_loan_fee_credits: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0")
    platform_fee_credits: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0")
    lender_net_credits: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0")
    platform_fee_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    fee_floor_applied: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    loan_duration_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    currency: Mapped[str] = mapped_column(String(12), nullable=False, default="coin", server_default="coin")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="accepted_pending_settlement", server_default="accepted_pending_settlement")
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    borrowed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    returned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    settlement_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    accepted_terms_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    borrower_rights_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    lender_rights_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    lender_restrictions_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    usage_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class CardSwapListing(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "card_swap_listings"
    __table_args__ = (
        Index("ix_card_swap_listings_player_card_id", "player_card_id"),
        Index("ix_card_swap_listings_owner_user_id", "owner_user_id"),
        Index("ix_card_swap_listings_status", "status"),
        Index("ix_card_swap_listings_requested_player_card_id", "requested_player_card_id"),
    )

    player_card_id: Mapped[str] = mapped_column(String(36), ForeignKey("player_cards.id", ondelete="CASCADE"), nullable=False)
    owner_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    requested_player_card_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("player_cards.id", ondelete="SET NULL"),
        nullable=True,
    )
    requested_player_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="open", server_default="open")
    is_negotiable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    desired_filters_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    terms_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class CardSwapExecution(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "card_swap_executions"
    __table_args__ = (
        UniqueConstraint("listing_id", name="uq_card_swap_executions_listing_id"),
        Index("ix_card_swap_executions_owner_user_id", "owner_user_id"),
        Index("ix_card_swap_executions_counterparty_user_id", "counterparty_user_id"),
        Index("ix_card_swap_executions_status", "status"),
    )

    listing_id: Mapped[str] = mapped_column(String(36), ForeignKey("card_swap_listings.id", ondelete="CASCADE"), nullable=False)
    owner_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    counterparty_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    owner_player_card_id: Mapped[str] = mapped_column(String(36), ForeignKey("player_cards.id", ondelete="CASCADE"), nullable=False)
    counterparty_player_card_id: Mapped[str] = mapped_column(String(36), ForeignKey("player_cards.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="executed", server_default="executed")
    settled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class CardMarketplaceAuditEvent(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "card_marketplace_audit_events"
    __table_args__ = (
        Index("ix_card_marketplace_audit_events_listing_type", "listing_type"),
        Index("ix_card_marketplace_audit_events_action", "action"),
        Index("ix_card_marketplace_audit_events_actor_user_id", "actor_user_id"),
        Index("ix_card_marketplace_audit_events_player_card_id", "player_card_id"),
        Index("ix_card_marketplace_audit_events_listing_id", "listing_id"),
    )

    listing_type: Mapped[str] = mapped_column(String(24), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    player_card_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("player_cards.id", ondelete="SET NULL"), nullable=True)
    listing_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    loan_contract_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    negotiation_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    swap_execution_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status_from: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status_to: Mapped[str | None] = mapped_column(String(32), nullable=True)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class StarterSquadRental(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "starter_squad_rentals"
    __table_args__ = (
        Index("ix_starter_squad_rentals_user_id", "user_id"),
        Index("ix_starter_squad_rentals_status", "status"),
    )

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    club_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("club_profiles.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active", server_default="active")
    rental_fee_credits: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0")
    currency: Mapped[str] = mapped_column(String(12), nullable=False, default="credit", server_default="credit")
    term_days: Mapped[int] = mapped_column(Integer, nullable=False, default=7, server_default="7")
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    first_team_count: Mapped[int] = mapped_column(Integer, nullable=False, default=18, server_default="18")
    academy_count: Mapped[int] = mapped_column(Integer, nullable=False, default=18, server_default="18")
    is_non_tradable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    roster_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    academy_roster_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

__all__ = [
    "CardLoanContract",
    "CardLoanListing",
    "CardLoanNegotiation",
    "CardMarketplaceAuditEvent",
    "CardSwapExecution",
    "CardSwapListing",
    "StarterSquadRental",
]
