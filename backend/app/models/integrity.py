from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Integer, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.user import User


class IntegrityScore(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "integrity_scores"
    __table_args__ = (UniqueConstraint("user_id", name="uq_integrity_scores_user_id"),)

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    score: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=100, server_default="100.00")
    risk_level: Mapped[str] = mapped_column(String(16), nullable=False, default="low", server_default="low")
    incident_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    user: Mapped["User"] = relationship()


class IntegrityIncident(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "integrity_incidents"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    incident_type: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="medium", server_default="medium")
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    score_delta: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0, server_default="0.00")
    detected_by: Mapped[str] = mapped_column(String(32), nullable=False, default="rules_engine", server_default="rules_engine")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open", server_default="open")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    resolved_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship(foreign_keys=[user_id])
    resolved_by_user: Mapped["User | None"] = relationship(foreign_keys=[resolved_by_user_id])
