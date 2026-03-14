from __future__ import annotations

from typing import Any

from sqlalchemy import Boolean, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CompetitionAutofillRule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "competition_autofill_rules"

    competition_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("user_competitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    min_fill: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    max_fill: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100, server_default="100")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = ["CompetitionAutofillRule"]
