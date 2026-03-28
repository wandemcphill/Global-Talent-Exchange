from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from threading import RLock
from typing import Any

from app.core.events import DomainEvent


@dataclass(frozen=True, slots=True)
class AlertRecord:
    alert_id: str
    event_name: str
    severity: str
    alert_type: str
    title: str
    body: str
    user_id: str | None
    created_at: datetime
    metadata: dict[str, Any]


@dataclass(frozen=True, slots=True)
class AlertSnapshot:
    total_alerts: int
    by_severity: dict[str, int]
    by_type: dict[str, int]
    recent_alerts: list[AlertRecord]


@dataclass(slots=True)
class AlertSystem:
    max_alerts: int = 200
    _recent_alerts: deque[AlertRecord] = field(default_factory=deque)
    _by_severity: dict[str, int] = field(default_factory=dict)
    _by_type: dict[str, int] = field(default_factory=dict)
    _total_alerts: int = 0
    _lock: RLock = field(default_factory=RLock)

    def handle_event(self, event: DomainEvent) -> None:
        if event.name != "risk.fraud.detected":
            return
        payload = dict(event.payload or {})
        severity = str(payload.get("severity") or "warning").strip().lower() or "warning"
        alert_type = str(payload.get("rule_key") or "fraud").strip().lower() or "fraud"
        title = str(payload.get("title") or "Fraud alert").strip() or "Fraud alert"
        body = str(payload.get("description") or "").strip() or "A fraud rule was triggered."
        user_id = str(payload.get("user_id") or "").strip() or None
        alert_id = str(payload.get("system_event_id") or payload.get("fraud_case_id") or event.event_id)
        record = AlertRecord(
            alert_id=alert_id,
            event_name=event.name,
            severity=severity,
            alert_type=alert_type,
            title=title,
            body=body,
            user_id=user_id,
            created_at=event.occurred_at,
            metadata=dict(payload.get("metadata") or {}),
        )
        with self._lock:
            self._total_alerts += 1
            self._by_severity[severity] = self._by_severity.get(severity, 0) + 1
            self._by_type[alert_type] = self._by_type.get(alert_type, 0) + 1
            self._recent_alerts.appendleft(record)
            while len(self._recent_alerts) > self.max_alerts:
                self._recent_alerts.pop()

    def snapshot(self) -> AlertSnapshot:
        with self._lock:
            return AlertSnapshot(
                total_alerts=self._total_alerts,
                by_severity=dict(self._by_severity),
                by_type=dict(self._by_type),
                recent_alerts=list(self._recent_alerts),
            )


__all__ = ["AlertRecord", "AlertSnapshot", "AlertSystem"]
