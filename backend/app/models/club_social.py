from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, CreatedAtMixin


class ClubChallenge(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "club_challenges"
    __table_args__ = (UniqueConstraint("slug", name="uq_club_challenges_slug"),)

    issuing_club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_club_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    issuing_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    competition_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("user_competitions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    linked_match_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("competition_matches.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    accepted_club_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    winner_club_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    stakes_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    visibility: Mapped[str] = mapped_column(String(24), nullable=False, default="public", server_default="public", index=True)
    country_code: Mapped[str | None] = mapped_column(String(8), nullable=True, index=True)
    region_name: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    city_name: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="open", server_default="open", index=True)
    accept_by: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    live_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class ClubChallengeResponse(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "club_challenge_responses"
    __table_args__ = (
        UniqueConstraint("challenge_id", "responding_club_id", name="uq_club_challenge_responses_challenge_club"),
    )

    challenge_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_challenges.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    responding_club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    responder_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    response_type: Mapped[str] = mapped_column(String(24), nullable=False, default="accept", server_default="accept")
    response_status: Mapped[str] = mapped_column(String(24), nullable=False, default="recorded", server_default="recorded")
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class ClubChallengeLink(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "club_challenge_links"
    __table_args__ = (
        UniqueConstraint("link_code", name="uq_club_challenge_links_link_code"),
        UniqueConstraint("vanity_path", name="uq_club_challenge_links_vanity_path"),
    )

    challenge_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_challenges.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    channel: Mapped[str] = mapped_column(String(32), nullable=False, default="share", server_default="share")
    link_code: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    vanity_path: Mapped[str] = mapped_column(String(220), nullable=False)
    web_path: Mapped[str] = mapped_column(String(255), nullable=False)
    deep_link_path: Mapped[str] = mapped_column(String(255), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    click_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class ClubIdentityMetrics(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "club_identity_metrics"
    __table_args__ = (UniqueConstraint("club_id", name="uq_club_identity_metrics_club_id"),)

    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    fan_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    reputation_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    media_popularity_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    media_value_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    club_valuation_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    rivalry_intensity_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    support_momentum_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    sponsorship_potential_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    discoverability_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    challenge_history_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class MatchReactionEvent(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "match_reaction_events"
    __table_args__ = (
        UniqueConstraint("source_event_id", "reaction_type", name="uq_match_reaction_events_source_type"),
    )

    match_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("competition_matches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    competition_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("user_competitions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_event_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("competition_match_events.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    challenge_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("club_challenges.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    rivalry_profile_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("rivalry_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    club_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reaction_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    reaction_label: Mapped[str] = mapped_column(String(80), nullable=False)
    intensity_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    minute: Mapped[int | None] = mapped_column(Integer, nullable=True)
    happened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class RivalryProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "rivalry_profiles"
    __table_args__ = (
        UniqueConstraint("club_a_id", "club_b_id", name="uq_rivalry_profiles_pair"),
    )

    club_a_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    club_b_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    label: Mapped[str] = mapped_column(String(80), nullable=False, default="Emerging rivalry", server_default="Emerging rivalry")
    intensity_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    regional_derby: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    giant_killer_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    matches_played: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    club_a_wins: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    club_b_wins: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    draws: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    club_a_goals: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    club_b_goals: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    finals_played: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    upset_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    challenge_matches: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    high_view_matches: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    high_gift_matches: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    streak_holder_club_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    streak_length: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_match_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notable_moments_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    narrative_tags_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class RivalryMatchHistory(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "rivalry_match_history"
    __table_args__ = (
        UniqueConstraint("rivalry_id", "match_id", name="uq_rivalry_match_history_rivalry_match"),
    )

    rivalry_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("rivalry_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    match_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("competition_matches.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    competition_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("user_competitions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    challenge_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("club_challenges.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    home_club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    away_club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    winner_club_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    home_score: Mapped[int] = mapped_column(Integer, nullable=False)
    away_score: Mapped[int] = mapped_column(Integer, nullable=False)
    upset_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    final_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    challenge_match_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    high_view_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    high_gift_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    gift_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    match_weight: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    notable_moments_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    happened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class ChallengeShareEvent(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "challenge_share_events"

    challenge_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_challenges.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    link_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("club_challenge_links.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    actor_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    source_platform: Mapped[str | None] = mapped_column(String(48), nullable=True, index=True)
    country_code: Mapped[str | None] = mapped_column(String(8), nullable=True, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = [
    "ChallengeShareEvent",
    "ClubChallenge",
    "ClubChallengeLink",
    "ClubChallengeResponse",
    "ClubIdentityMetrics",
    "MatchReactionEvent",
    "RivalryMatchHistory",
    "RivalryProfile",
]
