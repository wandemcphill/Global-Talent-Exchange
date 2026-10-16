from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums.scout_assignment_status import ScoutAssignmentStatus
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.scouting_region import ScoutingRegion
    from app.models.youth_prospect import YouthProspect
    from app.models.youth_prospect_report import YouthProspectReport


class ScoutAssignment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "scout_assignments"

    club_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    region_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("scouting_regions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    region_code: Mapped[str] = mapped_column(String(64), nullable=False)
    region_name: Mapped[str] = mapped_column(String(120), nullable=False)
    focus_area: Mapped[str] = mapped_column(String(120), nullable=False)
    budget_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    scout_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    status: Mapped[ScoutAssignmentStatus] = mapped_column(
        Enum(
            ScoutAssignmentStatus,
            name="scout_assignment_status",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    report_confidence_floor_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    region: Mapped["ScoutingRegion | None"] = relationship(back_populates="assignments")
    prospects: Mapped[list["YouthProspect"]] = relationship(back_populates="assignment")
    reports: Mapped[list["YouthProspectReport"]] = relationship(back_populates="assignment")


__all__ = ["ScoutAssignment"]
