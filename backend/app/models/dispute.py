from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.user import User


class DisputeStatus(StrEnum):
    OPEN = "open"
    AWAITING_USER = "awaiting_user"
    AWAITING_ADMIN = "awaiting_admin"
    RESOLVED = "resolved"
    CLOSED = "closed"


class Dispute(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "disputes"
    __table_args__ = (
        Index("ix_disputes_status", "status"),
        Index("ix_disputes_user_id", "user_id"),
        Index("ix_disputes_reference", "reference"),
        Index("ix_disputes_resource", "resource_type", "resource_id"),
        Index("ix_disputes_created_at", "created_at"),
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    admin_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(64), nullable=False)
    reference: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[DisputeStatus] = mapped_column(
        Enum(DisputeStatus, name="dispute_status", native_enum=False),
        nullable=False,
        default=DisputeStatus.OPEN,
    )
    subject: Mapped[str | None] = mapped_column(String(120), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    admin_user: Mapped["User | None"] = relationship("User", foreign_keys=[admin_user_id])


class DisputeMessage(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "dispute_messages"
    __table_args__ = (
        Index("ix_dispute_messages_dispute_id", "dispute_id"),
        Index("ix_dispute_messages_created_at", "created_at"),
    )

    dispute_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("disputes.id", ondelete="CASCADE"),
        nullable=False,
    )
    sender_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    sender_role: Mapped[str] = mapped_column(String(32), nullable=False, default="user")
    message: Mapped[str] = mapped_column(Text, nullable=False)
    attachment_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("attachments.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    dispute: Mapped["Dispute"] = relationship("Dispute", foreign_keys=[dispute_id])
    sender: Mapped["User | None"] = relationship("User", foreign_keys=[sender_user_id])
