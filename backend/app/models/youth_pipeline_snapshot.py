from __future__ import annotations

from sqlalchemy import Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class YouthPipelineSnapshot(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "youth_pipeline_snapshots"

    club_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    funnel_json: Mapped[dict[str, int]] = mapped_column(JSON, nullable=False, default=dict)
    academy_conversion_rate_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    promotion_rate_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")


__all__ = ["YouthPipelineSnapshot"]
