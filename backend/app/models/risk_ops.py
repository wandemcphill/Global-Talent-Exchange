from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Enum, ForeignKey, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class RiskCaseStatus(StrEnum):
    OPEN = "open"
    IN_REVIEW = "in_review"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class RiskSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SystemEventSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class RiskSignalType(StrEnum):
    DEVICE_ID = "device_id"
    IP_ADDRESS = "ip_address"
    TRANSACTION_PATTERN = "transaction_pattern"
    MATCH_BEHAVIOR = "match_behavior"


class RiskActionType(StrEnum):
    FREEZE_WALLET = "freeze_wallet"
    BLOCK_WITHDRAWAL = "block_withdrawal"
    MANUAL_REVIEW = "manual_review"
    BLOCK_TRADING = "block_trading"


class RiskActionStatus(StrEnum):
    ACTIVE = "active"
    RELEASED = "released"
    EXPIRED = "expired"


class AmlCase(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "aml_cases"

    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    case_key: Mapped[str] = mapped_column(String(96), nullable=False, unique=True, index=True)
    trigger_source: Mapped[str] = mapped_column(String(48), nullable=False, default="manual", server_default="manual")
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[RiskSeverity] = mapped_column(Enum(RiskSeverity, name="risk_severity", native_enum=False), nullable=False, default=RiskSeverity.MEDIUM, server_default="medium")
    status: Mapped[RiskCaseStatus] = mapped_column(Enum(RiskCaseStatus, name="risk_case_status", native_enum=False), nullable=False, default=RiskCaseStatus.OPEN, server_default="open")
    amount_signal: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0.00"), server_default="0.00")
    country_code: Mapped[str | None] = mapped_column(String(8), nullable=True, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    assigned_admin_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    resolved_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User | None"] = relationship(foreign_keys=[user_id])
    assigned_admin_user: Mapped["User | None"] = relationship(foreign_keys=[assigned_admin_user_id])
    resolved_by_user: Mapped["User | None"] = relationship(foreign_keys=[resolved_by_user_id])


class FraudCase(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "fraud_cases"

    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    case_key: Mapped[str] = mapped_column(String(96), nullable=False, unique=True, index=True)
    fraud_type: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[RiskSeverity] = mapped_column(Enum(RiskSeverity, name="risk_severity", native_enum=False), nullable=False, default=RiskSeverity.MEDIUM, server_default="medium")
    status: Mapped[RiskCaseStatus] = mapped_column(Enum(RiskCaseStatus, name="risk_case_status", native_enum=False), nullable=False, default=RiskCaseStatus.OPEN, server_default="open")
    confidence_score: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"), server_default="0.00")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    assigned_admin_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    resolved_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User | None"] = relationship(foreign_keys=[user_id])
    assigned_admin_user: Mapped["User | None"] = relationship(foreign_keys=[assigned_admin_user_id])
    resolved_by_user: Mapped["User | None"] = relationship(foreign_keys=[resolved_by_user_id])


class RiskSignal(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "risk_signals"

    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    signal_type: Mapped[RiskSignalType] = mapped_column(
        Enum(RiskSignalType, name="risk_signal_type", native_enum=False),
        nullable=False,
    )
    signal_key: Mapped[str] = mapped_column(String(64), nullable=False, default="signal", server_default="signal")
    signal_value: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    device_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(48), nullable=False, default="manual", server_default="manual", index=True)
    confidence_score: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"), server_default="0.00")
    occurred_at: Mapped[Any | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    user: Mapped["User | None"] = relationship(foreign_keys=[user_id])


class RiskAction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "risk_actions"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    action_type: Mapped[RiskActionType] = mapped_column(
        Enum(RiskActionType, name="risk_action_type", native_enum=False),
        nullable=False,
        index=True,
    )
    status: Mapped[RiskActionStatus] = mapped_column(
        Enum(RiskActionStatus, name="risk_action_status", native_enum=False),
        nullable=False,
        default=RiskActionStatus.ACTIVE,
        server_default="active",
        index=True,
    )
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    source_rule_key: Mapped[str] = mapped_column(String(96), nullable=False, default="manual", server_default="manual", index=True)
    created_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    released_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    fraud_case_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("fraud_cases.id", ondelete="SET NULL"), nullable=True, index=True)
    release_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    released_at: Mapped[Any | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Any | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    user: Mapped["User"] = relationship(foreign_keys=[user_id])
    created_by_user: Mapped["User | None"] = relationship(foreign_keys=[created_by_user_id])
    released_by_user: Mapped["User | None"] = relationship(foreign_keys=[released_by_user_id])
    fraud_case: Mapped["FraudCase | None"] = relationship(foreign_keys=[fraud_case_id])


class SystemEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "system_events"
    __table_args__ = (UniqueConstraint("event_key", name="uq_system_events_event_key"),)

    event_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    severity: Mapped[SystemEventSeverity] = mapped_column(Enum(SystemEventSeverity, name="system_event_severity", native_enum=False), nullable=False, default=SystemEventSeverity.INFO, server_default="info")
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    subject_type: Mapped[str | None] = mapped_column(String(48), nullable=True, index=True)
    subject_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    created_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    created_by_user: Mapped["User | None"] = relationship(foreign_keys=[created_by_user_id])


class AuditLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "audit_logs"

    actor_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action_key: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    resource_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    outcome: Mapped[str] = mapped_column(String(24), nullable=False, default="success", server_default="success")
    detail: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    actor_user: Mapped["User | None"] = relationship(foreign_keys=[actor_user_id])
