from __future__ import annotations

from typing import Any

from sqlalchemy import Boolean, Float, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PunditProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "pundit_profiles"
    __table_args__ = (UniqueConstraint("name", name="uq_pundit_profiles_name"),)

    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    style: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    bias: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    confidence_level: Mapped[float] = mapped_column(Float, nullable=False, default=0.65, server_default="0.65")
    debate_style: Mapped[str] = mapped_column(String(64), nullable=False, default="measured", server_default="measured")
    signature_line: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = ["PunditProfile"]
