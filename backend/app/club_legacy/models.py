"""Delegation policy, pending recommendations, and audit rows for Club Legacy."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin, utcnow


class ClubLegacyPolicy(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "club_legacy_policies"
    __table_args__ = (UniqueConstraint("club_id", "task_key", name="uq_club_legacy_policies_club_task"),)

    club_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    task_key: Mapped[str] = mapped_column(String(64), nullable=False)
    mode: Mapped[str] = mapped_column(String(32), nullable=False)
    max_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    scope_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now()
    )


class ClubLegacyRecommendation(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "club_legacy_recommendations"

    club_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    task_key: Mapped[str] = mapped_column(String(64), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="recommended")
    outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now()
    )


class ClubLegacyAuditEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "club_legacy_audit_events"

    club_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    actor_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    detail_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now()
    )


class ClubLegacyExecutive(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "club_legacy_executives"
    __table_args__ = (UniqueConstraint("club_id", "role", name="uq_club_legacy_executives_club_role"),)

    club_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    personality: Mapped[str] = mapped_column(String(40), nullable=False, default="cautious")
    attributes_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    wage: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False, default=Decimal("0"))
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="hired")


class ClubLegacyReport(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "club_legacy_reports"

    club_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False)
    consequence: Mapped[str] = mapped_column(Text, nullable=False)


class ClubLegacyCatalogueItem(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "club_legacy_catalogue_items"

    sku: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    supply_cap: Mapped[int | None] = mapped_column(Integer, nullable=True)
    minted_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fallback_label: Mapped[str] = mapped_column(String(160), nullable=False)


class ClubLegacyAsset(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "club_legacy_assets"
    __table_args__ = (
        UniqueConstraint("catalogue_id", "edition_number", name="uq_club_legacy_assets_catalogue_edition"),
    )

    catalogue_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    edition_number: Mapped[int] = mapped_column(Integer, nullable=False)
    owner_class: Mapped[str] = mapped_column(String(16), nullable=False)
    owner_ref: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    club_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="owned")
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True)


class ClubLegacyGift(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "club_legacy_gifts"

    asset_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    sender_user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    recipient_ref: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="offered")


class ClubLegacyListing(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "club_legacy_listings"

    asset_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    seller_user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    fee: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False, default=Decimal("0"))
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open")
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True)


class ClubLegacyPreseasonWindow(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "club_legacy_preseason_windows"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    starts_on: Mapped[str] = mapped_column(String(10), nullable=False)
    ends_on: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open")


class ClubLegacyPreseasonInvite(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "club_legacy_preseason_invites"

    window_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    from_club_id: Mapped[str] = mapped_column(String(36), nullable=False)
    to_club_id: Mapped[str] = mapped_column(String(36), nullable=False)
    match_on: Mapped[str] = mapped_column(String(10), nullable=False)
    appearance_fee: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")


class ClubLegacyPreseasonSettlement(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "club_legacy_preseason_settlements"

    invite_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    platform_amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    host_amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    participant_amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    reputation_delta: Mapped[int] = mapped_column(Integer, nullable=False)
    audience: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rule_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    gift_platform_amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False, default=Decimal("0"))
    gift_club_amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False, default=Decimal("0"))


class ClubLegacySponsorContract(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "club_legacy_sponsor_contracts"

    club_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    sponsor_name: Mapped[str] = mapped_column(String(120), nullable=False)
    placement: Mapped[str] = mapped_column(String(32), nullable=False)
    fee: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="offered")
    delivery_report: Mapped[str | None] = mapped_column(Text, nullable=True)
    impressions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    renewed_from_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class ClubLegacyKitVersion(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "club_legacy_kit_versions"

    club_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    template_name: Mapped[str] = mapped_column(String(80), nullable=False)
    zones_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    contract_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class ClubLegacyManagerOffer(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "club_legacy_manager_offers"

    club_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    candidate_name: Mapped[str] = mapped_column(String(120), nullable=False)
    wage: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    prestige: Mapped[int] = mapped_column(Integer, nullable=False)
    ambition: Mapped[int] = mapped_column(Integer, nullable=False)
    seed: Mapped[int] = mapped_column(Integer, nullable=False)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    money_score: Mapped[int] = mapped_column(Integer, nullable=False)
    project_score: Mapped[int] = mapped_column(Integer, nullable=False)


class ClubLegacyPromise(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "club_legacy_promises"

    club_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open")
    trust: Mapped[int] = mapped_column(Integer, nullable=False, default=50)


class ClubLegacyCase(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "club_legacy_cases"

    club_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    rule_code: Mapped[str] = mapped_column(String(64), nullable=False)
    allegation: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open")
    sanction: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    appeal_outcome: Mapped[str | None] = mapped_column(Text, nullable=True)


class ClubLegacyBid(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "club_legacy_bids"

    listing_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    bidder_user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="leading")


class ClubLegacyStake(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "club_legacy_stakes"
    __table_args__ = (UniqueConstraint("club_id", "holder_user_id", name="uq_club_legacy_stakes_club_holder"),)

    club_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    holder_user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    percentage: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    voting_rights: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)


class ClubLegacyProvenance(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "club_legacy_provenance"

    asset_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    from_owner_class: Mapped[str] = mapped_column(String(16), nullable=False)
    from_owner_ref: Mapped[str] = mapped_column(String(64), nullable=False)
    to_owner_class: Mapped[str] = mapped_column(String(16), nullable=False)
    to_owner_ref: Mapped[str] = mapped_column(String(64), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    actor_user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now()
    )


class ClubLegacyRelationshipEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "club_legacy_relationship_events"

    gift_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    asset_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    actor_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    recipient_ref: Mapped[str] = mapped_column(String(64), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    loyalty: Mapped[int] = mapped_column(Integer, nullable=False)
    morale: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now()
    )


class ClubLegacyMarketSettings(UUIDPrimaryKeyMixin, Base):
    """Admin settings for resale fees and club inventory caps. Absent row uses documented defaults."""

    __tablename__ = "club_legacy_market_settings"

    settings_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    transfer_fee_rate: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    jet_cap: Mapped[int] = mapped_column(Integer, nullable=False)
    coach_cap: Mapped[int] = mapped_column(Integer, nullable=False)


class ClubLegacyRevenueRule(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "club_legacy_revenue_rules"

    version: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    platform_share: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    host_share: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    participant_share: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    stage_shares_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")


class ClubLegacyPreseasonEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "club_legacy_preseason_events"

    invite_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    appearance_fee: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    match_on: Mapped[str] = mapped_column(String(10), nullable=False)
    actor_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    detail_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now()
    )


class ClubLegacyPreseasonOffer(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "club_legacy_preseason_offers"

    invite_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    appearance_fee: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    match_on: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now()
    )


class ClubLegacyTournament(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "club_legacy_tournaments"

    window_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    host_club_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    match_on: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open")


class ClubLegacyTournamentParticipant(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "club_legacy_tournament_participants"
    __table_args__ = (
        UniqueConstraint("tournament_id", "club_id", name="uq_club_legacy_tournament_participants_tournament_club"),
    )

    tournament_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    club_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)


class ClubLegacyTournamentSettlement(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "club_legacy_tournament_settlements"

    tournament_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    rule_version: Mapped[int] = mapped_column(Integer, nullable=False)
    platform_amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    host_amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    participant_amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    audience: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reputation_delta: Mapped[int] = mapped_column(Integer, nullable=False)


class ClubLegacyManagerCommitment(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "club_legacy_manager_commitments"
    __table_args__ = (
        UniqueConstraint("club_id", "match_on", name="uq_club_legacy_manager_commitments_club_date"),
    )

    club_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    match_on: Mapped[str] = mapped_column(String(10), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    source_id: Mapped[str] = mapped_column(String(36), nullable=False)


class ClubLegacySponsorZone(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "club_legacy_sponsor_zones"
    __table_args__ = (UniqueConstraint("contract_id", "zone", name="uq_club_legacy_sponsor_zones_contract_zone"),)

    contract_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    zone: Mapped[str] = mapped_column(String(32), nullable=False)


CLUB_LEGACY_TABLES = (ClubLegacyPolicy.__table__, ClubLegacyRecommendation.__table__, ClubLegacyAuditEvent.__table__)
CLUB_LEGACY_PHASE_TABLES = (
    ClubLegacyExecutive.__table__,
    ClubLegacyReport.__table__,
    ClubLegacyCatalogueItem.__table__,
    ClubLegacyAsset.__table__,
    ClubLegacyGift.__table__,
    ClubLegacyListing.__table__,
    ClubLegacyPreseasonWindow.__table__,
    ClubLegacyPreseasonInvite.__table__,
    ClubLegacyPreseasonSettlement.__table__,
    ClubLegacySponsorContract.__table__,
    ClubLegacyKitVersion.__table__,
    ClubLegacyManagerOffer.__table__,
    ClubLegacyPromise.__table__,
    ClubLegacyCase.__table__,
    ClubLegacyStake.__table__,
    ClubLegacyBid.__table__,
)
CLUB_LEGACY_FULL_TABLES = (
    ClubLegacyProvenance.__table__,
    ClubLegacyRelationshipEvent.__table__,
    ClubLegacyMarketSettings.__table__,
    ClubLegacyRevenueRule.__table__,
    ClubLegacyPreseasonEvent.__table__,
    ClubLegacyPreseasonOffer.__table__,
    ClubLegacyTournament.__table__,
    ClubLegacyTournamentParticipant.__table__,
    ClubLegacyTournamentSettlement.__table__,
    ClubLegacyManagerCommitment.__table__,
    ClubLegacySponsorZone.__table__,
)
