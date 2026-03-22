from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class StreamerTournamentType(str, Enum):
    CREATOR_INVITATION = "creator_invitation"
    FAN_QUALIFIER = "fan_qualifier"
    CREATOR_VS_FAN = "creator_vs_fan"


class StreamerTournamentStatus(str, Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    PUBLISHED = "published"
    LIVE = "live"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class StreamerTournamentApprovalStatus(str, Enum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class StreamerTournamentInviteStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    REVOKED = "revoked"


class StreamerTournamentQualificationType(str, Enum):
    INVITE = "invite"
    PLAYOFFS = "playoffs"
    SEASON_PASS = "season_pass"
    SHAREHOLDER = "shareholder"
    TOP_GIFTER = "top_gifter"


class StreamerTournamentEntryStatus(str, Enum):
    CONFIRMED = "confirmed"
    ELIMINATED = "eliminated"
    COMPLETED = "completed"
    DECLINED = "declined"
    WITHDRAWN = "withdrawn"
    DISQUALIFIED = "disqualified"


class StreamerTournamentRewardType(str, Enum):
    GTEX_COIN = "gtex_coin"
    FAN_COIN = "fan_coin"
    EXCLUSIVE_COSMETIC = "exclusive_cosmetic"


class StreamerTournamentRiskStatus(str, Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class StreamerTournamentRewardGrantStatus(str, Enum):
    PENDING = "pending"
    SETTLED = "settled"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StreamerTournamentPolicy(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "streamer_tournament_policies"
    __table_args__ = (
        UniqueConstraint("policy_key", name="uq_streamer_tournament_policies_policy_key"),
    )

    policy_key: Mapped[str] = mapped_column(String(64), nullable=False, default="default", server_default="default")
    reward_coin_approval_limit: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("500.0000"), server_default="500.0000")
    reward_credit_approval_limit: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("5000.0000"), server_default="5000.0000")
    max_cosmetic_rewards_without_review: Mapped[int] = mapped_column(Integer, nullable=False, default=10, server_default="10")
    max_reward_slots: Mapped[int] = mapped_column(Integer, nullable=False, default=12, server_default="12")
    max_invites_per_tournament: Mapped[int] = mapped_column(Integer, nullable=False, default=64, server_default="64")
    top_gifter_rank_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=25, server_default="25")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    config_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    updated_by_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )


class StreamerTournament(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "streamer_tournaments"
    __table_args__ = (
        UniqueConstraint("creator_profile_id", "slug", name="uq_streamer_tournaments_creator_slug"),
    )

    host_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    creator_profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("creator_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    creator_club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    season_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("creator_league_seasons.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    linked_competition_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("user_competitions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    playoff_source_competition_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("user_competitions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    slug: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tournament_type: Mapped[StreamerTournamentType] = mapped_column(
        SqlEnum(StreamerTournamentType, name="streamertournamenttype"),
        nullable=False,
    )
    status: Mapped[StreamerTournamentStatus] = mapped_column(
        SqlEnum(StreamerTournamentStatus, name="streamertournamentstatus"),
        nullable=False,
        default=StreamerTournamentStatus.DRAFT,
        server_default=StreamerTournamentStatus.DRAFT.value,
    )
    approval_status: Mapped[StreamerTournamentApprovalStatus] = mapped_column(
        SqlEnum(StreamerTournamentApprovalStatus, name="streamertournamentapprovalstatus"),
        nullable=False,
        default=StreamerTournamentApprovalStatus.NOT_REQUIRED,
        server_default=StreamerTournamentApprovalStatus.NOT_REQUIRED.value,
    )
    max_participants: Mapped[int] = mapped_column(Integer, nullable=False, default=8, server_default="8")
    requires_admin_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    high_reward_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    rejected_by_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    submission_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    approval_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    entry_rules_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class StreamerTournamentInvite(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "streamer_tournament_invites"
    __table_args__ = (
        UniqueConstraint("tournament_id", "invited_user_id", name="uq_streamer_tournament_invites_tournament_user"),
    )

    tournament_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("streamer_tournaments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    invited_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    invited_by_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[StreamerTournamentInviteStatus] = mapped_column(
        SqlEnum(StreamerTournamentInviteStatus, name="streamertournamentinvitestatus"),
        nullable=False,
        default=StreamerTournamentInviteStatus.PENDING,
        server_default=StreamerTournamentInviteStatus.PENDING.value,
    )
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class StreamerTournamentEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "streamer_tournament_entries"
    __table_args__ = (
        UniqueConstraint("tournament_id", "user_id", name="uq_streamer_tournament_entries_tournament_user"),
    )

    tournament_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("streamer_tournaments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    invite_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("streamer_tournament_invites.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    entry_role: Mapped[str] = mapped_column(String(32), nullable=False, default="participant", server_default="participant")
    qualification_source: Mapped[StreamerTournamentQualificationType] = mapped_column(
        SqlEnum(StreamerTournamentQualificationType, name="streamertournamentqualificationtype"),
        nullable=False,
    )
    qualification_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[StreamerTournamentEntryStatus] = mapped_column(
        SqlEnum(StreamerTournamentEntryStatus, name="streamertournamententrystatus"),
        nullable=False,
        default=StreamerTournamentEntryStatus.CONFIRMED,
        server_default=StreamerTournamentEntryStatus.CONFIRMED.value,
    )
    seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    placement: Mapped[int | None] = mapped_column(Integer, nullable=True)
    joined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class StreamerTournamentReward(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "streamer_tournament_rewards"

    tournament_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("streamer_tournaments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    reward_type: Mapped[StreamerTournamentRewardType] = mapped_column(
        SqlEnum(StreamerTournamentRewardType, name="streamertournamentrewardtype"),
        nullable=False,
    )
    placement_start: Mapped[int] = mapped_column(Integer, nullable=False)
    placement_end: Mapped[int] = mapped_column(Integer, nullable=False)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    cosmetic_sku: Mapped[str | None] = mapped_column(String(120), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class StreamerTournamentRiskSignal(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "streamer_tournament_risk_signals"
    __table_args__ = (
        UniqueConstraint("tournament_id", "signal_key", name="uq_streamer_tournament_risk_signals_tournament_signal"),
    )

    tournament_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("streamer_tournaments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    signal_key: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="low", server_default="low")
    status: Mapped[StreamerTournamentRiskStatus] = mapped_column(
        SqlEnum(StreamerTournamentRiskStatus, name="streamertournamentriskstatus"),
        nullable=False,
        default=StreamerTournamentRiskStatus.OPEN,
        server_default=StreamerTournamentRiskStatus.OPEN.value,
    )
    summary: Mapped[str] = mapped_column(String(255), nullable=False)
    detail: Mapped[str | None] = mapped_column(String(500), nullable=True)
    detected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class StreamerTournamentRewardGrant(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "streamer_tournament_reward_grants"

    tournament_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("streamer_tournaments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reward_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("streamer_tournament_rewards.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entry_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("streamer_tournament_entries.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    recipient_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    placement: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reward_type: Mapped[StreamerTournamentRewardType] = mapped_column(
        SqlEnum(StreamerTournamentRewardType, name="streamertournamentrewardtype"),
        nullable=False,
    )
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    cosmetic_sku: Mapped[str | None] = mapped_column(String(120), nullable=True)
    settlement_status: Mapped[StreamerTournamentRewardGrantStatus] = mapped_column(
        SqlEnum(StreamerTournamentRewardGrantStatus, name="streamertournamentrewardgrantstatus"),
        nullable=False,
        default=StreamerTournamentRewardGrantStatus.PENDING,
        server_default=StreamerTournamentRewardGrantStatus.PENDING.value,
    )
    reward_settlement_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("reward_settlements.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    ledger_transaction_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    settled_by_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = [
    "StreamerTournament",
    "StreamerTournamentApprovalStatus",
    "StreamerTournamentEntry",
    "StreamerTournamentEntryStatus",
    "StreamerTournamentInvite",
    "StreamerTournamentInviteStatus",
    "StreamerTournamentPolicy",
    "StreamerTournamentQualificationType",
    "StreamerTournamentReward",
    "StreamerTournamentRewardGrant",
    "StreamerTournamentRewardGrantStatus",
    "StreamerTournamentRewardType",
    "StreamerTournamentRiskSignal",
    "StreamerTournamentRiskStatus",
    "StreamerTournamentStatus",
    "StreamerTournamentType",
]
