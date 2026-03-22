from __future__ import annotations

from typing import Any

from sqlalchemy import ForeignKey, Index, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CreatorSquad(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "creator_squads"
    __table_args__ = (
        UniqueConstraint("club_id", name="uq_creator_squads_club_id"),
        UniqueConstraint("creator_profile_id", name="uq_creator_squads_creator_profile_id"),
        Index("ix_creator_squads_club_id", "club_id"),
        Index("ix_creator_squads_creator_profile_id", "creator_profile_id"),
    )

    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    creator_profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("creator_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    first_team_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=25, server_default="25")
    academy_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=30, server_default="30")
    total_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=55, server_default="55")
    first_team_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    academy_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class CreatorRegen(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "creator_regens"
    __table_args__ = (
        UniqueConstraint("creator_profile_id", name="uq_creator_regens_creator_profile_id"),
        Index("ix_creator_regens_club_id", "club_id"),
        Index("ix_creator_regens_creator_profile_id", "creator_profile_id"),
    )

    creator_profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("creator_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    primary_position: Mapped[str] = mapped_column(String(40), nullable=False)
    secondary_positions_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    current_gsi: Mapped[int] = mapped_column(Integer, nullable=False)
    potential_maximum: Mapped[int] = mapped_column(Integer, nullable=False)
    squad_bucket: Mapped[str] = mapped_column(String(24), nullable=False, default="first_team", server_default="first_team")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class CreatorClubProvisioning(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "creator_club_provisioning"
    __table_args__ = (
        UniqueConstraint("application_id", name="uq_creator_club_provisioning_application_id"),
        UniqueConstraint("creator_profile_id", name="uq_creator_club_provisioning_creator_profile_id"),
        UniqueConstraint("club_id", name="uq_creator_club_provisioning_club_id"),
        UniqueConstraint("stadium_id", name="uq_creator_club_provisioning_stadium_id"),
        UniqueConstraint("creator_squad_id", name="uq_creator_club_provisioning_creator_squad_id"),
        UniqueConstraint("creator_regen_id", name="uq_creator_club_provisioning_creator_regen_id"),
        Index("ix_creator_club_provisioning_club_id", "club_id"),
        Index("ix_creator_club_provisioning_creator_profile_id", "creator_profile_id"),
    )

    application_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("creator_applications.id", ondelete="CASCADE"),
        nullable=False,
    )
    creator_profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("creator_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    stadium_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_stadiums.id", ondelete="CASCADE"),
        nullable=False,
    )
    creator_squad_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("creator_squads.id", ondelete="CASCADE"),
        nullable=False,
    )
    creator_regen_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("creator_regens.id", ondelete="CASCADE"),
        nullable=False,
    )
    provision_status: Mapped[str] = mapped_column(String(24), nullable=False, default="active", server_default="active")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = ["CreatorClubProvisioning", "CreatorRegen", "CreatorSquad"]
