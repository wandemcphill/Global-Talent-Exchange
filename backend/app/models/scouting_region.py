from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.common.enums.scouting_region_type import ScoutingRegionType
from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.scout_assignment import ScoutAssignment


class ScoutingRegion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "scouting_regions"
    __table_args__ = (
        UniqueConstraint("code", name="uq_scouting_regions_code"),
    )

    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    region_type: Mapped[ScoutingRegionType] = mapped_column(
        Enum(
            ScoutingRegionType,
            name="scouting_region_type",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    territory_codes_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")

    assignments: Mapped[list["ScoutAssignment"]] = relationship(back_populates="region")


__all__ = ["ScoutingRegion"]
