from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class LaunchState(StrEnum):
    HIDDEN = "hidden"
    INTERNAL = "internal"
    BETA = "beta"
    PUBLIC = "public"
    PAUSED = "paused"
    MAINTENANCE = "maintenance"
    DISABLED = "disabled"


class LaunchControlFeatureFlagView(BaseModel):
    id: str
    feature_key: str
    title: str
    description: str | None = None
    enabled: bool
    audience: str
    launch_state: LaunchState
    allowed_roles: list[str] = Field(default_factory=list)
    allowed_regions: list[str] = Field(default_factory=list)
    beta_only: bool = False
    kill_switch_enabled: bool = False
    maintenance_message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    route: str | None = None
    updated_at: datetime


class LaunchControlFlagUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    enabled: bool | None = None
    audience: str | None = Field(default=None, min_length=1, max_length=32)
    launch_state: LaunchState | None = None
    allowed_roles: list[str] | None = None
    allowed_regions: list[str] | None = None
    beta_only: bool | None = None
    kill_switch_enabled: bool | None = None
    maintenance_message: str | None = Field(default=None, max_length=2000)
    metadata: dict[str, Any] | None = None
    reason: str | None = Field(default=None, max_length=2000)


class LaunchControlReasonRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=2000)


class LaunchControlKillSwitchRequest(BaseModel):
    enabled: bool = True
    reason: str | None = Field(default=None, max_length=2000)


class BetaAccessGrantRequest(BaseModel):
    feature_key: str = Field(min_length=2, max_length=64)
    user_id: str = Field(min_length=1, max_length=36)
    active: bool = True
    notes: str | None = Field(default=None, max_length=2000)
    expires_at: datetime | None = None


class BetaAccessGrantView(BaseModel):
    id: str
    feature_key: str
    user_id: str
    active: bool
    notes: str | None = None
    expires_at: datetime | None = None
    granted_by_user_id: str | None = None
    created_at: datetime
    updated_at: datetime


class FeatureFlagAuditEventView(BaseModel):
    id: str
    feature_key: str
    action: str
    previous: dict[str, Any] = Field(default_factory=dict)
    next: dict[str, Any] = Field(default_factory=dict)
    reason: str | None = None
    actor_user_id: str | None = None
    created_at: datetime


class ClientFeatureFlagView(BaseModel):
    feature_key: str
    title: str
    enabled: bool
    launch_state: LaunchState
    route: str | None = None
    maintenance_message: str | None = None


class AdminCommandRouteView(BaseModel):
    module_key: str
    title: str
    description: str
    route: str
    feature_key: str | None = None
    launch_state: LaunchState | None = None
    enabled: bool = False


class ModuleHealthView(BaseModel):
    module_key: str
    status: str
    detail: str
    feature_key: str | None = None
    launch_state: LaunchState | None = None
    kill_switch_enabled: bool = False


class LaunchControlDashboardView(BaseModel):
    flags: list[LaunchControlFeatureFlagView]
    beta_grants: list[BetaAccessGrantView]
    recent_audit_events: list[FeatureFlagAuditEventView]
    command_routes: list[AdminCommandRouteView]
    module_health: list[ModuleHealthView]
