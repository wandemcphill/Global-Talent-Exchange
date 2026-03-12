from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.scout_assignment import ScoutAssignment
    from backend.app.models.youth_prospect import YouthProspect


class YouthProspectReport(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "youth_prospect_reports"

    prospect_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("youth_prospects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assignment_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("scout_assignments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    confidence_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    summary_text: Mapped[str] = mapped_column(String(255), nullable=False)
    strengths_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    development_flags_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)

    prospect: Mapped["YouthProspect"] = relationship(back_populates="reports")
    assignment: Mapped["ScoutAssignment | None"] = relationship(back_populates="reports")


__all__ = ["YouthProspectReport"]
