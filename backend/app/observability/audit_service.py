from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.models.risk_ops import SystemEventSeverity
from app.risk_ops_engine.service import RiskOpsService


@dataclass(slots=True)
class AuditTrailService:
    session: Session

    def log_admin_override(
        self,
        *,
        actor_user_id: str | None,
        action_key: str,
        detail: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        RiskOpsService(self.session).log_audit(
            actor_user_id=actor_user_id,
            action_key=action_key,
            resource_type="admin_override",
            resource_id=None,
            detail=detail,
            metadata_json=metadata or {},
        )

    def log_integrity_alert(
        self,
        *,
        actor_user_id: str | None,
        event_key: str,
        title: str,
        body: str,
        severity: SystemEventSeverity = SystemEventSeverity.WARNING,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        RiskOpsService(self.session).create_system_event(
            actor_user_id=actor_user_id,
            event_key=event_key,
            event_type="integrity_alert",
            severity=severity,
            title=title,
            body=body,
            subject_type="integrity",
            subject_id=None,
            metadata_json=metadata or {},
        )


__all__ = ["AuditTrailService"]
