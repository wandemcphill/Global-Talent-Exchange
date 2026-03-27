from __future__ import annotations

from typing import Any

from sqlalchemy import Float, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class HighlightEvent(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "highlight_events"

    match_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    minute: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    importance_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = ["HighlightEvent"]
