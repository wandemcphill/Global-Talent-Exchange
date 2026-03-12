from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.common.enums.player_pathway_stage import PlayerPathwayStage
from backend.app.common.enums.youth_prospect_rating_band import YouthProspectRatingBand
from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.scout_assignment import ScoutAssignment
    from backend.app.models.youth_prospect_report import YouthProspectReport


class YouthProspect(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "youth_prospects"

    club_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    assignment_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("scout_assignments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    nationality_code: Mapped[str] = mapped_column(String(12), nullable=False)
    region_label: Mapped[str] = mapped_column(String(120), nullable=False)
    primary_position: Mapped[str] = mapped_column(String(40), nullable=False)
    secondary_position: Mapped[str | None] = mapped_column(String(40), nullable=True)
    rating_band: Mapped[YouthProspectRatingBand] = mapped_column(
        Enum(
            YouthProspectRatingBand,
            name="youth_prospect_rating_band",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    development_traits_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    pathway_stage: Mapped[PlayerPathwayStage] = mapped_column(
        Enum(
            PlayerPathwayStage,
            name="player_pathway_stage",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    scouting_source: Mapped[str] = mapped_column(String(80), nullable=False)
    follow_priority: Mapped[int] = mapped_column(Integer, nullable=False, default=5, server_default="5")
    academy_player_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)

    assignment: Mapped["ScoutAssignment | None"] = relationship(back_populates="prospects")
    reports: Mapped[list["YouthProspectReport"]] = relationship(back_populates="prospect")


__all__ = ["YouthProspect"]
