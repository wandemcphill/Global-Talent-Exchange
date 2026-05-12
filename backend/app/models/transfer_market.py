from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class TransferListing(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "transfer_listings"
    __table_args__ = ()

    window_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("transfer_windows.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    selling_club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    base_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default="0",
    )
    current_highest_bid: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default="0",
    )
    highest_bidder_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default="open",
        server_default="open",
        index=True,
    )
    listing_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="transfer",
        server_default="transfer",
        index=True,
    )
    asset_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="real_player",
        server_default="real_player",
        index=True,
    )
    visibility: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="public",
        server_default="public",
        index=True,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reserve_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    salary_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    contract_years_remaining: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    buy_clause_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    loan_terms_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    swap_terms_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    availability_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    bid_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    watchlist_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    anti_sniping_extension_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_bid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class TransferListingBid(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "transfer_listing_bids"

    listing_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("transfer_listings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bidder_club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default="0",
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=func.now(),
        index=True,
    )
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class TransferHubOffer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "transfer_hub_offers"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_transfer_hub_offers_idempotency_key"),
    )

    listing_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("transfer_listings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    offer_type: Mapped[str] = mapped_column(String(32), nullable=False, default="transfer", server_default="transfer")
    seller_club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bidder_club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cash_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0",
    )
    offered_player_ids_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    loan_terms_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    swap_terms_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    conditional_terms_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    sell_on_percentage: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open", server_default="open", index=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class TransferRequest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "transfer_requests"

    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    current_club_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    requested_by_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open", server_default="open", index=True)
    preferred_leagues_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    preferred_clubs_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    reasons_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class PlayerDecisionProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "player_decision_profiles"
    __table_args__ = (
        UniqueConstraint("player_id", name="uq_player_decision_profiles_player_id"),
    )

    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    preferred_leagues_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    preferred_play_style: Mapped[str | None] = mapped_column(String(64), nullable=True)
    wage_expectation_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0",
    )
    ambition_level: Mapped[int] = mapped_column(Integer, nullable=False, default=50, server_default="50")
    happiness: Mapped[float] = mapped_column(Float, nullable=False, default=50.0, server_default="50.0")
    loyalty: Mapped[float] = mapped_column(Float, nullable=False, default=50.0, server_default="50.0")
    ambition: Mapped[float] = mapped_column(Float, nullable=False, default=50.0, server_default="50.0")
    frustration: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class CoachProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "coach_profiles"
    __table_args__ = (
        UniqueConstraint("club_id", name="uq_coach_profiles_club_id"),
    )

    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    personality_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    tactical_philosophy: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="balanced",
        server_default="balanced",
    )
    authority_level: Mapped[float] = mapped_column(Float, nullable=False, default=50.0, server_default="50.0")
    transfer_preference: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="balanced",
        server_default="balanced",
    )
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class CoachDemand(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "coach_demands"

    coach_profile_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("coach_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    need: Mapped[str] = mapped_column(String(80), nullable=False)
    urgency: Mapped[str] = mapped_column(String(16), nullable=False, default="medium", server_default="medium")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class PlayerCoachRelationship(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "player_coach_relationships"
    __table_args__ = (
        UniqueConstraint("player_id", "club_id", name="uq_player_coach_relationships_player_club"),
    )

    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relationship_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0, server_default="50.0")
    integration_success_modifier: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    conflict_level: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class ClubTeamDynamics(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "club_team_dynamics"
    __table_args__ = (
        UniqueConstraint("club_id", name="uq_club_team_dynamics_club_id"),
    )

    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    leaders_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    cliques_json: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)
    morale_groups_json: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)
    chemistry_risk: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class MarketWatchlistEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "market_watchlist_entries"
    __table_args__ = (
        UniqueConstraint("club_id", "player_id", name="uq_market_watchlist_entries_club_player"),
    )

    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="scouting", server_default="scouting")
    discovery_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0, server_default="50.0")
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class TransferNegotiation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "transfer_negotiations"
    __table_args__ = (
        UniqueConstraint("listing_id", name="uq_transfer_negotiations_listing_id"),
    )

    listing_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("transfer_listings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    winning_bid_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("transfer_listing_bids.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    selling_club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bidder_club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="awaiting_contract_offer",
        server_default="awaiting_contract_offer",
        index=True,
    )
    wage_offer_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    contract_years: Mapped[int] = mapped_column(Integer, nullable=False, default=3, server_default="3")
    expected_role: Mapped[str | None] = mapped_column(String(40), nullable=True)
    agent_response: Mapped[str | None] = mapped_column(String(32), nullable=True)
    coach_stance: Mapped[str | None] = mapped_column(String(16), nullable=True)
    coach_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    player_decision_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    coach_opinion_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    clauses_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    concerns_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    decision_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lifecycle_transfer_bid_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("transfer_bids.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    player_contract_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("player_contracts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
