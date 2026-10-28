from __future__ import annotations

from typing import Any

from sqlalchemy import ForeignKey, ForeignKeyConstraint, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class OwnerCompetitionLifecycleMapping(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Explicit one-to-one link from the legacy owner-console competition to GTEX canonical competition."""

    __tablename__ = "owner_competition_lifecycle_mappings"
    __table_args__ = (
        UniqueConstraint(
            "legacy_competition_id",
            name="uq_owner_comp_lifecycle_legacy_competition",
        ),
        UniqueConstraint(
            "canonical_competition_id",
            name="uq_owner_comp_lifecycle_canonical_competition",
        ),
        UniqueConstraint(
            "id",
            "legacy_competition_id",
            name="uq_owner_comp_lifecycle_id_legacy_competition",
        ),
    )

    # Intentionally no FK to owner_competitions: mapping removal or schema
    # maintenance must not cascade into historical owner-console records.
    legacy_competition_id: Mapped[str] = mapped_column(String(36), nullable=False)
    canonical_competition_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("user_competitions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    mapping_status: Mapped[str] = mapped_column(String(24), nullable=False, default="active", server_default="active")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class OwnerMatchLifecycleMapping(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Explicit one-to-one link from a legacy OwnerMatch to its canonical fixture."""

    __tablename__ = "owner_match_lifecycle_mappings"
    __table_args__ = (
        UniqueConstraint(
            "legacy_match_id",
            name="uq_owner_match_lifecycle_legacy_match",
        ),
        UniqueConstraint(
            "canonical_match_id",
            name="uq_owner_match_lifecycle_canonical_match",
        ),
        ForeignKeyConstraint(
            ["competition_mapping_id", "legacy_competition_id"],
            [
                "owner_competition_lifecycle_mappings.id",
                "owner_competition_lifecycle_mappings.legacy_competition_id",
            ],
            name="fk_owner_match_lifecycle_competition_map_legacy_competition",
            ondelete="RESTRICT",
        ),
    )

    # Intentionally no FK to owner_matches so that deleting a mapping cannot
    # delete or rewrite legacy match history.
    legacy_match_id: Mapped[str] = mapped_column(String(36), nullable=False)
    competition_mapping_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    legacy_competition_id: Mapped[str] = mapped_column(String(36), nullable=False)
    canonical_match_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("competition_matches.id", ondelete="RESTRICT"),
        nullable=False,
    )
    mapping_status: Mapped[str] = mapped_column(String(24), nullable=False, default="active", server_default="active")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = ["OwnerCompetitionLifecycleMapping", "OwnerMatchLifecycleMapping"]
