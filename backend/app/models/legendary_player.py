from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.ingestion.models import Player


class LegendaryPlayerProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "legendary_player_profiles"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_legendary_player_profiles_slug"),
        Index("ix_legendary_player_profiles_slug", "slug"),
        Index("ix_legendary_player_profiles_country_code", "country_code"),
        Index("ix_legendary_player_profiles_primary_position", "primary_position"),
        Index("ix_legendary_player_profiles_legendary_classification", "legendary_classification"),
        Index("ix_legendary_player_profiles_era", "era"),
        Index("ix_legendary_player_profiles_status", "is_active", "is_searchable"),
        Index("ix_legendary_player_profiles_editorial_status", "editorial_status"),
        Index("ix_legendary_player_profiles_rights_status", "rights_status"),
        Index("ix_legendary_player_profiles_catalogue_status", "catalogue_status"),
    )

    slug: Mapped[str] = mapped_column(String(128), nullable=False)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    country_code: Mapped[str] = mapped_column(String(8), nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    primary_position: Mapped[str] = mapped_column(String(40), nullable=False)
    secondary_positions_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    preferred_foot: Mapped[str] = mapped_column(String(16), nullable=False, default="right")
    historical_height_cm: Mapped[int] = mapped_column(Integer, nullable=False)
    gtex_height_cm: Mapped[int] = mapped_column(Integer, nullable=False)
    signature_traits_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    signature_role: Mapped[str | None] = mapped_column(String(80), nullable=True)
    technical_profile_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    physical_profile_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    mental_profile_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    era: Mapped[str] = mapped_column(String(64), nullable=False)
    legendary_classification: Mapped[str] = mapped_column(
        String(40), nullable=False, default="icon", server_default="icon"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    is_searchable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    is_tradable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    is_rentable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    is_national_team_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    portrait_metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    source_evidence_json: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)
    football_evidence_json: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)
    editorial_status: Mapped[str] = mapped_column(String(32), nullable=False, default="sourced", server_default="sourced")
    rights_status: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown", server_default="unknown")
    catalogue_status: Mapped[str] = mapped_column(String(32), nullable=False, default="staged", server_default="staged")
    source_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)

    instantiated_players: Mapped[list["Player"]] = relationship(
        "Player",
        back_populates="legendary_profile",
        foreign_keys="[Player.legendary_profile_id]",
    )


__all__ = ["LegendaryPlayerProfile"]
