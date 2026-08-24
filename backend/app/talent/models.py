"""Persistence for the Talent Exchange discovery layer.

These tables sit *beside* the existing football entities rather than replacing
them. `ingestion_players` remains the canonical player identity, `value_engine`
remains the economic authority, and `scouting_intelligence` remains the in-game
club scouting simulation. What was missing — and what lives here — is the
discovery-facing projection of a talent, its ranking lineage, its derived
signals, its verification ladder, and the scout-side workflow (shortlists) and
admin-side workflow (moderation audit) built on top.

`talent_profiles` intentionally denormalises the handful of columns that search
filters on. Discovery queries must be answerable from one indexed table scan;
joining out to matches and stats per candidate is what turns a talent search
into an outage.

No column in this module holds KYC evidence, government identifiers, contact
details or payment data. Verification records reference an opaque
`evidence_reference` (e.g. an internal review ticket id), never the document.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.talent.constants import (
    AvailabilityStatus,
    ModerationState,
    NEUTRAL_COMPONENT_SCORE,
    ShortlistEntryStatus,
    VerificationDecision,
    VerificationTier,
    VisibilityState,
)


class TalentProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "talent_profiles"
    __table_args__ = (
        UniqueConstraint("player_id", name="uq_talent_profiles_player_id"),
        Index("ix_talent_profiles_owner_user_id", "owner_user_id"),
        Index("ix_talent_profiles_visibility_score", "visibility_state", "composite_score"),
        Index("ix_talent_profiles_visibility_position", "visibility_state", "position_code"),
        Index("ix_talent_profiles_visibility_country", "visibility_state", "nationality_code"),
        Index("ix_talent_profiles_visibility_availability", "visibility_state", "availability_status"),
        Index("ix_talent_profiles_visibility_verification", "visibility_state", "verification_tier"),
        Index("ix_talent_profiles_visibility_age", "visibility_state", "age_years"),
        Index("ix_talent_profiles_moderation_state", "moderation_state"),
        Index("ix_talent_profiles_display_name", "display_name"),
        Index("ix_talent_profiles_featured", "is_featured", "featured_rank"),
    )

    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
    )
    # A talent may or may not be a platform account holder. When they are, that
    # account is the only non-admin identity allowed the OWNER projection.
    owner_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # --- identity (public-safe) -----------------------------------------
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    headline: Mapped[str | None] = mapped_column(String(200), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- football identity ----------------------------------------------
    position_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    secondary_positions_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    tactical_roles_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    preferred_foot: Mapped[str | None] = mapped_column(String(8), nullable=True)

    # Pipe-delimited membership indexes ("|CB|LB|"). JSON containment is not
    # portable between SQLite and Postgres, and filtering multi-valued fields in
    # Python after the fetch would break pagination totals. A bounded LIKE over
    # a short string keeps multi-valued filters inside the single indexed query.
    position_index: Mapped[str] = mapped_column(String(128), nullable=False, default="", server_default="")
    tactical_role_index: Mapped[str] = mapped_column(String(512), nullable=False, default="", server_default="")
    signal_index: Mapped[str] = mapped_column(String(512), nullable=False, default="", server_default="")

    # `date_of_birth` is owner/admin only; `age_years` is the public-facing and
    # searchable form so age filtering never requires exposing a birth date.
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    age_years: Mapped[int | None] = mapped_column(Integer, nullable=True)

    nationality_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    nationality_name: Mapped[str | None] = mapped_column(String(96), nullable=True)
    location_country_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    location_region: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # City is scout-and-above only: it is precise enough to be locating.
    location_city: Mapped[str | None] = mapped_column(String(120), nullable=True)

    height_cm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weight_kg: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # --- football attributes --------------------------------------------
    technical_attributes_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    tactical_attributes_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    physical_attributes_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    # --- availability / experience --------------------------------------
    availability_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=AvailabilityStatus.UNKNOWN.value,
        server_default=AvailabilityStatus.UNKNOWN.value,
    )
    availability_note: Mapped[str | None] = mapped_column(String(240), nullable=True)
    available_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    experience_years: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    current_club_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    current_competition_name: Mapped[str | None] = mapped_column(String(160), nullable=True)

    # --- verification ----------------------------------------------------
    verification_tier: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=VerificationTier.UNVERIFIED.value,
        server_default=VerificationTier.UNVERIFIED.value,
    )
    verification_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verification_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # --- visibility / moderation ----------------------------------------
    visibility_state: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=VisibilityState.DRAFT.value,
        server_default=VisibilityState.DRAFT.value,
    )
    moderation_state: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ModerationState.CLEAR.value,
        server_default=ModerationState.CLEAR.value,
    )
    is_featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    featured_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # --- denormalised ranking (written by the ranking pipeline) ----------
    composite_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=NEUTRAL_COMPONENT_SCORE, server_default="50.0"
    )
    form_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=NEUTRAL_COMPONENT_SCORE, server_default="50.0"
    )
    consistency_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=NEUTRAL_COMPONENT_SCORE, server_default="50.0"
    )
    competition_level_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=NEUTRAL_COMPONENT_SCORE, server_default="50.0"
    )
    ranking_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    ranking_sample_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    ranking_computed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ranking_config_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ranking_inputs_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    active_signal_codes_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)

    # --- portfolio -------------------------------------------------------
    # Entries: {"kind": "video"|"image"|"document", "url": str, "title": str,
    #           "approved": bool}. Only approved entries are ever projected.
    portfolio_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)

    # --- admin-only ------------------------------------------------------
    internal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    suspension_reason: Mapped[str | None] = mapped_column(String(240), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    ranking_snapshots: Mapped[list["TalentRankingSnapshot"]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
    )
    signal_records: Mapped[list["TalentSignalRecord"]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
    )
    verification_records: Mapped[list["TalentVerificationRecord"]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
    )

    @property
    def is_discoverable(self) -> bool:
        return self.visibility_state == VisibilityState.PUBLISHED.value


class TalentRankingSnapshot(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One immutable-per-day record of what the ranking pipeline produced.

    Keyed on (player, as_of, config version) so a same-day recompute updates in
    place rather than accumulating duplicates, while a config-version bump
    keeps the previous lineage intact for comparison.
    """

    __tablename__ = "talent_ranking_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "player_id",
            "as_of",
            "config_version",
            name="uq_talent_ranking_snapshots_player_asof_config",
        ),
        Index("ix_talent_ranking_snapshots_profile_id", "profile_id"),
        Index("ix_talent_ranking_snapshots_inputs_digest", "inputs_digest"),
        Index("ix_talent_ranking_snapshots_as_of", "as_of"),
    )

    profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("talent_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
    )
    as_of: Mapped[date] = mapped_column(Date, nullable=False)
    config_version: Mapped[str] = mapped_column(String(32), nullable=False)
    composite_score: Mapped[float] = mapped_column(Float, nullable=False)
    base_score: Mapped[float] = mapped_column(Float, nullable=False)
    adjustments_total: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    components_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    adjustments_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    signals_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    inputs_digest: Mapped[str] = mapped_column(String(64), nullable=False)

    profile: Mapped[TalentProfile] = relationship(back_populates="ranking_snapshots")


class TalentSignalRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "talent_signal_records"
    __table_args__ = (
        UniqueConstraint("player_id", "signal_code", "as_of", name="uq_talent_signal_records_player_code_asof"),
        Index("ix_talent_signal_records_profile_id", "profile_id"),
        Index("ix_talent_signal_records_code", "signal_code"),
        Index("ix_talent_signal_records_as_of", "as_of"),
    )

    profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("talent_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
    )
    as_of: Mapped[date] = mapped_column(Date, nullable=False)
    signal_code: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(160), nullable=False)
    polarity: Mapped[str] = mapped_column(String(16), nullable=False, default="positive", server_default="positive")
    strength: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    explanation: Mapped[str] = mapped_column(Text, nullable=False, default="")
    evidence_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    config_version: Mapped[str] = mapped_column(String(32), nullable=False)

    profile: Mapped[TalentProfile] = relationship(back_populates="signal_records")


class TalentVerificationRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Audit trail of verification decisions.

    The presence of a profile grants nothing. A tier is only claimable while a
    `GRANTED` record for it exists and has not been revoked or expired.
    """

    __tablename__ = "talent_verification_records"
    __table_args__ = (
        Index("ix_talent_verification_records_profile_id", "profile_id"),
        Index("ix_talent_verification_records_player_tier", "player_id", "tier"),
        Index("ix_talent_verification_records_decision", "decision"),
    )

    profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("talent_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
    )
    tier: Mapped[str] = mapped_column(String(32), nullable=False)
    decision: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=VerificationDecision.GRANTED.value,
        server_default=VerificationDecision.GRANTED.value,
    )
    # What *kind* of evidence was reviewed (e.g. "club_letter", "federation_registry").
    evidence_kind: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # An opaque internal pointer (review ticket id). Never a document, never PII.
    evidence_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    decided_by_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    profile: Mapped[TalentProfile] = relationship(back_populates="verification_records")


class TalentShortlist(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "talent_shortlists"
    __table_args__ = (
        UniqueConstraint("owner_user_id", "name", name="uq_talent_shortlists_owner_name"),
        Index("ix_talent_shortlists_owner_user_id", "owner_user_id"),
        Index("ix_talent_shortlists_club_id", "club_id"),
    )

    owner_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    club_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(String(400), nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    entries: Mapped[list["TalentShortlistEntry"]] = relationship(
        back_populates="shortlist",
        cascade="all, delete-orphan",
    )


class TalentShortlistEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "talent_shortlist_entries"
    __table_args__ = (
        UniqueConstraint("shortlist_id", "player_id", name="uq_talent_shortlist_entries_list_player"),
        Index("ix_talent_shortlist_entries_player_id", "player_id"),
        Index("ix_talent_shortlist_entries_status", "status"),
    )

    shortlist_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("talent_shortlists.id", ondelete="CASCADE"),
        nullable=False,
    )
    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
    )
    added_by_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ShortlistEntryStatus.WATCHING.value,
        server_default=ShortlistEntryStatus.WATCHING.value,
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    # Scout's private note. Visible only to the shortlist owner and admins.
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Score at the moment of adding, so a scout can see drift since.
    score_at_add: Mapped[float | None] = mapped_column(Float, nullable=True)

    shortlist: Mapped[TalentShortlist] = relationship(back_populates="entries")


class TalentModerationAction(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Append-only audit of every admin action against a talent profile."""

    __tablename__ = "talent_moderation_actions"
    __table_args__ = (
        Index("ix_talent_moderation_actions_profile_id", "profile_id"),
        Index("ix_talent_moderation_actions_player_id", "player_id"),
        Index("ix_talent_moderation_actions_action", "action"),
        Index("ix_talent_moderation_actions_actor", "actor_user_id"),
    )

    profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("talent_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    player_id: Mapped[str] = mapped_column(String(36), nullable=False)
    actor_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    action: Mapped[str] = mapped_column(String(48), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(400), nullable=True)
    before_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    after_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = [
    "TalentModerationAction",
    "TalentProfile",
    "TalentRankingSnapshot",
    "TalentShortlist",
    "TalentShortlistEntry",
    "TalentSignalRecord",
    "TalentVerificationRecord",
]
