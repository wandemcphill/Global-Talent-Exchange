from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = ["AlertSystem", "AuditTrailService"]


def __getattr__(name: str) -> Any:
    if name == "AlertSystem":
        return import_module("app.observability.alert_system").AlertSystem
    if name == "AuditTrailService":
        return import_module("app.observability.audit_service").AuditTrailService
    raise AttributeError(name)
