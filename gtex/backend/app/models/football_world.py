from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class FootballCultureProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "football_culture_profiles"
    __table_args__ = (UniqueConstraint("culture_key", name="uq_football_culture_profiles_culture_key"),)

    culture_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    scope_type: Mapped[str] = mapped_column(String(32), nullable=False, default="archetype", server_default="archetype")
    country_code: Mapped[str | None] = mapped_column(String(8), nullable=True, index=True)
    region_name: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    city_name: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    play_style_summary: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    supporter_traits_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    rivalry_themes_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    talent_archetypes_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    climate_notes: Mapped[str] = mapped_column(String(255), nullable=False, default="", server_default="")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class ClubWorldProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "club_world_profiles"
    __table_args__ = (UniqueConstraint("club_id", name="uq_club_world_profiles_club_id"),)

    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    culture_profile_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("football_culture_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    narrative_phase: Mapped[str] = mapped_column(
        String(48),
        nullable=False,
        default="establishing_identity",
        server_default="establishing_identity",
    )
    supporter_mood: Mapped[str] = mapped_column(String(48), nullable=False, default="hopeful", server_default="hopeful")
    derby_heat_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    global_appeal_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    identity_keywords_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    transfer_identity_tags_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    fan_culture_tags_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    world_flags_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class WorldNarrativeArc(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "world_narrative_arcs"
    __table_args__ = (UniqueConstraint("slug", name="uq_world_narrative_arcs_slug"),)

    slug: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    scope_type: Mapped[str] = mapped_column(String(32), nullable=False, default="global", server_default="global")
    club_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    competition_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("user_competitions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    arc_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active", server_default="active", index=True)
    visibility: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default="public",
        server_default="public",
        index=True,
    )
    headline: Mapped[str] = mapped_column(String(180), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    importance_score: Mapped[int] = mapped_column(Integer, nullable=False, default=50, server_default="50")
    simulation_horizon: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="seasonal",
        server_default="seasonal",
    )
    start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tags_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    impact_vectors_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = ["FootballCultureProfile", "ClubWorldProfile", "WorldNarrativeArc"]
