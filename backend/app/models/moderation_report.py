from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.user import User


class ModerationReportStatus(StrEnum):
    OPEN = "open"
    IN_REVIEW = "in_review"
    ACTIONED = "actioned"
    DISMISSED = "dismissed"


class ModerationPriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class ModerationResolutionAction(StrEnum):
    NONE = "none"
    WARNING = "warning"
    CONTENT_REMOVED = "content_removed"
    ACCOUNT_RESTRICTED = "account_restricted"
    COMPETITION_LOCKED = "competition_locked"
    WALLET_REVIEW = "wallet_review"


class ModerationReport(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "moderation_reports"

    reporter_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    subject_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    target_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    target_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    reason_code: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[ModerationReportStatus] = mapped_column(
        Enum(ModerationReportStatus, name="moderation_report_status", native_enum=False),
        nullable=False,
        default=ModerationReportStatus.OPEN,
        server_default="open",
    )
    priority: Mapped[ModerationPriority] = mapped_column(
        Enum(ModerationPriority, name="moderation_priority", native_enum=False),
        nullable=False,
        default=ModerationPriority.NORMAL,
        server_default="normal",
    )
    assigned_admin_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    resolution_action: Mapped[ModerationResolutionAction] = mapped_column(
        Enum(ModerationResolutionAction, name="moderation_resolution_action", native_enum=False),
        nullable=False,
        default=ModerationResolutionAction.NONE,
        server_default="none",
    )
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    report_count_for_target: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")

    reporter_user: Mapped["User"] = relationship(foreign_keys=[reporter_user_id])
    subject_user: Mapped["User | None"] = relationship(foreign_keys=[subject_user_id])
    assigned_admin_user: Mapped["User | None"] = relationship(foreign_keys=[assigned_admin_user_id])
    resolved_by_user: Mapped["User | None"] = relationship(foreign_keys=[resolved_by_user_id])
