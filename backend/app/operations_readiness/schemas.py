from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class OperationsReadinessMetric(BaseModel):
    key: str
    label: str
    value: float
    display_value: str
    unit: str | None = None
    status: str = "ok"
    route: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class OperationsReadinessQueue(BaseModel):
    key: str
    title: str
    description: str
    status: str
    route: str | None = None
    owner: str
    metrics: list[OperationsReadinessMetric]
    alerts: list[str] = Field(default_factory=list)
    action_routes: list[str] = Field(default_factory=list)


class OperationsLaunchGate(BaseModel):
    feature_key: str
    title: str
    enabled: bool
    launch_state: str
    audience: str
    kill_switch_enabled: bool
    maintenance_message: str | None = None
    route: str | None = None


class OperationsReadinessSnapshot(BaseModel):
    generated_at: datetime
    status: str
    totals: dict[str, int | float]
    queues: list[OperationsReadinessQueue]
    launch_gates: list[OperationsLaunchGate]


class OperationsReadinessNotificationDispatch(BaseModel):
    status: str
    notifications_created: int
    queue_keys: list[str] = Field(default_factory=list)
