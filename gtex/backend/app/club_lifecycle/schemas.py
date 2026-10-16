from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ClubLifecycleStatus(StrEnum):
    DRAFT = "draft"
    CREATED = "created"
    IDENTITY_PENDING = "identity_pending"
    WALLET_REQUIRED = "wallet_required"
    SQUAD_BUILDING = "squad_building"
    SQUAD_READY = "squad_ready"
    COMPETITION_READY = "competition_ready"
    ACTIVE = "active"
    RESTRICTED = "restricted"
    SUSPENDED = "suspended"
    SOLD = "sold"
    ARCHIVED = "archived"


class SquadRegistrationStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    LOCKED = "locked"
    REOPENED = "reopened"


class ClubReadinessItemView(BaseModel):
    key: str
    label: str
    complete: bool
    detail: str


class ClubReadinessView(BaseModel):
    club_id: str
    readiness_score: int
    recommended_state: ClubLifecycleStatus
    competition_eligible: bool
    checklist: list[ClubReadinessItemView]
    blockers: list[str] = Field(default_factory=list)
    updated_at: datetime


class ClubLifecycleView(BaseModel):
    club_id: str
    state: ClubLifecycleStatus
    previous_state: ClubLifecycleStatus | None = None
    readiness_score: int
    blocked_reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime
    readiness: ClubReadinessView


class ClubLifecycleAdvanceRequest(BaseModel):
    target_state: ClubLifecycleStatus | None = None
    reason: str | None = Field(default=None, max_length=2000)


class ClubLifecycleAuditView(BaseModel):
    id: str
    club_id: str
    action: str
    previous: dict[str, Any] = Field(default_factory=dict)
    next: dict[str, Any] = Field(default_factory=dict)
    actor_user_id: str | None = None
    reason: str | None = None
    created_at: datetime


class SquadPlayerView(BaseModel):
    player_id: str
    name: str
    position: str | None = None
    position_group: str


class SquadRegistrationView(BaseModel):
    id: str
    club_id: str
    season_label: str
    status: SquadRegistrationStatus
    players: list[SquadPlayerView]
    position_summary: dict[str, int]
    submitted_at: datetime | None = None
    locked_at: datetime | None = None
    updated_at: datetime


class SquadRegistrationUpsertRequest(BaseModel):
    season_label: str = Field(default="launch", min_length=1, max_length=32)
    player_ids: list[str] = Field(default_factory=list, max_length=40)


class ClubOperatingDashboardView(BaseModel):
    club_id: str
    lifecycle: ClubLifecycleView
    squad_registration: SquadRegistrationView | None = None
    module_links: list[dict[str, str]] = Field(default_factory=list)
    counts: dict[str, int] = Field(default_factory=dict)
    alerts: list[str] = Field(default_factory=list)
    updated_at: datetime
