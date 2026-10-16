from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class FederationMembershipStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    REJECTED = "rejected"
    SUSPENDED = "suspended"


class FederationCompetitionType(StrEnum):
    LEAGUE = "league"
    CUP = "cup"
    TOURNAMENT = "tournament"


class FederationProposalStatus(StrEnum):
    DRAFT = "draft"
    OPEN = "open"
    CLOSED = "closed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class FederationVoteType(StrEnum):
    YES = "yes"
    NO = "no"
    ABSTAIN = "abstain"


class FederationSanctionType(StrEnum):
    FINE = "fine"
    POINTS_DEDUCTION = "points_deduction"
    PLAYER_BAN = "player_ban"
    TRANSFER_BAN = "transfer_ban"


class FederationRuleAuditStatus(StrEnum):
    PASSED = "passed"
    VIOLATION = "violation"


class Federation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "federations"
    __table_args__ = (
        UniqueConstraint("name", name="uq_federations_name"),
        Index("ix_federations_owner_user_id", "owner_user_id"),
        Index("ix_federations_ranking_score", "ranking_score"),
    )

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    owner_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    structure_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    rules_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    competitions_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    members_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    reputation_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0, server_default="50.0")
    ranking_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    treasury_balance: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0",
    )
    audience_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    default_reality_mode: Mapped[str] = mapped_column(String(24), nullable=False, default="hybrid", server_default="hybrid")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class FederationLeague(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "federation_leagues"
    __table_args__ = (
        UniqueConstraint("federation_id", "name", name="uq_federation_leagues_federation_name"),
        Index("ix_federation_leagues_federation_id", "federation_id"),
        Index("ix_federation_leagues_linked_competition_id", "linked_competition_id"),
    )

    federation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("federations.id", ondelete="CASCADE"),
        nullable=False,
    )
    linked_competition_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("user_competitions.id", ondelete="SET NULL"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    competition_type: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default=FederationCompetitionType.LEAGUE.value,
        server_default=FederationCompetitionType.LEAGUE.value,
    )
    format: Mapped[str] = mapped_column(String(32), nullable=False)
    divisions_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    promotion_relegation_rules_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    entry_requirements_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    governance_rules_override_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    season_label: Mapped[str | None] = mapped_column(String(48), nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="draft", server_default="draft")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class FederationMembership(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "federation_memberships"
    __table_args__ = (
        UniqueConstraint("federation_id", "club_id", name="uq_federation_memberships_federation_club"),
        Index("ix_federation_memberships_federation_id", "federation_id"),
        Index("ix_federation_memberships_status", "status"),
    )

    federation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("federations.id", ondelete="CASCADE"),
        nullable=False,
    )
    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="member_club", server_default="member_club")
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default=FederationMembershipStatus.PENDING.value,
        server_default=FederationMembershipStatus.PENDING.value,
    )
    entry_requirements_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class FederationProposal(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "federation_proposals"
    __table_args__ = (
        Index("ix_federation_proposals_federation_id", "federation_id"),
        Index("ix_federation_proposals_status", "status"),
        Index("ix_federation_proposals_voting_ends_at", "voting_ends_at"),
    )

    federation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("federations.id", ondelete="CASCADE"),
        nullable=False,
    )
    league_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("federation_leagues.id", ondelete="SET NULL"),
        nullable=True,
    )
    proposer_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    proposal_type: Mapped[str] = mapped_column(String(48), nullable=False, default="rule_change", server_default="rule_change")
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default=FederationProposalStatus.OPEN.value,
        server_default=FederationProposalStatus.OPEN.value,
    )
    voting_starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    voting_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    yes_votes: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    no_votes: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    abstain_votes: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class FederationVote(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "federation_votes"
    __table_args__ = (
        UniqueConstraint("proposal_id", "user_id", name="uq_federation_votes_proposal_user"),
        Index("ix_federation_votes_federation_id", "federation_id"),
    )

    proposal_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("federation_proposals.id", ondelete="CASCADE"),
        nullable=False,
    )
    federation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("federations.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    vote_type: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default=FederationVoteType.YES.value,
        server_default=FederationVoteType.YES.value,
    )
    weight: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class FederationSanction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "federation_sanctions"
    __table_args__ = (
        Index("ix_federation_sanctions_federation_id", "federation_id"),
        Index("ix_federation_sanctions_club_id", "club_id"),
        Index("ix_federation_sanctions_player_id", "player_id"),
    )

    federation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("federations.id", ondelete="CASCADE"),
        nullable=False,
    )
    league_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("federation_leagues.id", ondelete="SET NULL"),
        nullable=True,
    )
    club_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    player_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="SET NULL"),
        nullable=True,
    )
    applied_by_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    sanction_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=FederationSanctionType.FINE.value,
        server_default=FederationSanctionType.FINE.value,
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    fine_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0",
    )
    points_deduction: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    suspension_matches: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active", server_default="active")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class FederationTreasuryEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "federation_treasury_entries"
    __table_args__ = (
        UniqueConstraint("federation_id", "source_type", "source_reference", name="uq_federation_treasury_source"),
        Index("ix_federation_treasury_entries_federation_id", "federation_id"),
    )

    federation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("federations.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_reference: Mapped[str] = mapped_column(String(120), nullable=False)
    gross_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0",
    )
    federation_share: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0",
    )
    club_distribution_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class FederationNarrativeSnapshot(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "federation_narrative_snapshots"
    __table_args__ = (
        Index("ix_federation_narrative_snapshots_federation_id", "federation_id"),
        Index("ix_federation_narrative_snapshots_narrative_type", "narrative_type"),
    )

    federation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("federations.id", ondelete="CASCADE"),
        nullable=False,
    )
    narrative_type: Mapped[str] = mapped_column(String(48), nullable=False)
    headline: Mapped[str] = mapped_column(String(180), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class FederationRuleAudit(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "federation_rule_audits"
    __table_args__ = (
        Index("ix_federation_rule_audits_federation_id", "federation_id"),
        Index("ix_federation_rule_audits_status", "status"),
        Index("ix_federation_rule_audits_checked_at", "checked_at"),
    )

    federation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("federations.id", ondelete="CASCADE"),
        nullable=False,
    )
    league_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("federation_leagues.id", ondelete="SET NULL"),
        nullable=True,
    )
    action_type: Mapped[str] = mapped_column(String(48), nullable=False)
    club_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    player_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default=FederationRuleAuditStatus.PASSED.value,
        server_default=FederationRuleAuditStatus.PASSED.value,
    )
    violation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    violations_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = [
    "Federation",
    "FederationCompetitionType",
    "FederationLeague",
    "FederationMembership",
    "FederationMembershipStatus",
    "FederationNarrativeSnapshot",
    "FederationProposal",
    "FederationProposalStatus",
    "FederationRuleAudit",
    "FederationRuleAuditStatus",
    "FederationSanction",
    "FederationSanctionType",
    "FederationTreasuryEntry",
    "FederationVote",
    "FederationVoteType",
]
