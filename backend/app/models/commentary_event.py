from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin


class CommentaryEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "commentary_events"
    __table_args__ = (
        Index("ix_commentary_events_match_id_minute", "match_id", "minute"),
        Index("ix_commentary_events_match_id_event_type", "match_id", "event_type"),
        Index("ix_commentary_events_created_at", "created_at"),
    )

    match_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    minute: Mapped[int] = mapped_column(nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    context: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    generated_line: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


__all__ = ["CommentaryEvent"]
