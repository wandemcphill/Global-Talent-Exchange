from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from app.common.schemas.base import CommonSchema
from app.schemas.academy_core import (
    AcademyGraduationEventView,
    AcademyPlayerView,
    AcademyProgramView,
    AcademyTrainingCycleView,
)
from app.schemas.club_finance_core import (
    ClubBudgetSnapshotView,
    ClubCashflowSummaryView,
    ClubFinanceAccountView,
    ClubFinanceLedgerEntryView,
)
from app.schemas.scouting_core import (
    ScoutAssignmentView,
    ScoutingRegionView,
    YouthPipelineSnapshotView,
    YouthProspectView,
)
from app.schemas.sponsorship_core import (
    ClubSponsorshipAssetView,
    ClubSponsorshipContractView,
    ClubSponsorshipPackageView,
)

ClubOpsContractState = Literal[
    "ready",
    "draft",
    "published",
    "archived",
    "empty",
    "blocked",
    "degraded",
    "syncing",
    "error",
]
ClubOpsLaneStatus = Literal["ready", "empty", "blocked", "degraded", "missing", "syncing", "error"]


class ClubOpsMissingDataResponse(CommonSchema):
    source: str
    reason: str


class ClubOpsContractLaneResponse(CommonSchema):
    lane: str
    state: ClubOpsLaneStatus
    status: ClubOpsLaneStatus
    source: str | None = None
    items: tuple[dict[str, object], ...] = Field(default_factory=tuple)
    missing_data: tuple[ClubOpsMissingDataResponse, ...] = Field(default_factory=tuple)
    blockers: tuple[str, ...] = Field(default_factory=tuple)
    warnings: tuple[str, ...] = Field(default_factory=tuple)


class FormationCoordinatesResponse(CommonSchema):
    x: float | None = None
    y: float | None = None


class FormationSlotResponse(CommonSchema):
    id: str
    slot_id: str | None = None
    position: str | None = None
    role: str | None = None
    role_code: str | None = None
    role_label: str | None = None
    player: dict[str, object] | None = None
    player_id: str | None = None
    assigned_player_id: str | None = None
    player_name: str | None = None
    position_group: str | None = None
    coordinates: FormationCoordinatesResponse | None = None
    x: float | None = None
    y: float | None = None
    filled: bool = False
    locked_reason: str | None = None


class FormationHealthResponse(CommonSchema):
    score: int | None = Field(default=None, ge=0, le=100)
    blockers: tuple[str, ...] = Field(default_factory=tuple)
    warnings: tuple[str, ...] = Field(default_factory=tuple)
    missing_data: tuple[ClubOpsMissingDataResponse, ...] = Field(default_factory=tuple)


class FormationAuditEventResponse(CommonSchema):
    id: str
    action: str
    actor: str | None = None
    occurred_at: datetime | None = None
    note: str | None = None
    version: int | None = None


class FormationContractResponse(CommonSchema):
    club_id: str
    id: str | None = None
    formation_id: str | None = None
    version: int | None = None
    name: str | None = None
    shape: str | None = None
    scheme: str | None = None
    formation: str | None = None
    status: ClubOpsContractState
    state: ClubOpsContractState
    slots: tuple[FormationSlotResponse, ...] = Field(default_factory=tuple)
    chemistry_score: float | None = None
    warnings: tuple[str, ...] = Field(default_factory=tuple)
    health: FormationHealthResponse
    audit_trail: tuple[FormationAuditEventResponse, ...] = Field(default_factory=tuple)
    audit_ref: str | None = None
    sync_token: str | None = None
    can_save_draft: bool = False
    can_publish: bool = False
    missing_data: tuple[ClubOpsMissingDataResponse, ...] = Field(default_factory=tuple)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    updated_by: str | None = None
    published_at: datetime | None = None
    published_by: str | None = None
    code: str | None = None
    reason: str | None = None


class FormationHistoryResponse(CommonSchema):
    club_id: str
    state: ClubOpsContractState
    status: ClubOpsContractState
    formations: tuple[dict[str, object], ...] = Field(default_factory=tuple)
    items: tuple[dict[str, object], ...] = Field(default_factory=tuple)
    missing_data: tuple[ClubOpsMissingDataResponse, ...] = Field(default_factory=tuple)
    sync_token: str | None = None
    code: str | None = None
    reason: str | None = None


class FormationContractEnvelopeResponse(CommonSchema):
    club_id: str
    state: ClubOpsContractState
    status: ClubOpsContractState
    formation: FormationContractResponse
    missing_data: tuple[ClubOpsMissingDataResponse, ...] = Field(default_factory=tuple)
    code: str | None = None
    reason: str | None = None


class SquadReadinessResponse(CommonSchema):
    club_id: str
    state: ClubOpsContractState
    status: ClubOpsContractState
    eligible_count: int
    injured_count: int | None = None
    suspended_count: int | None = None
    available_for_next_fixture: int | None = None
    readiness_score: float | None = None
    warnings: tuple[str, ...] = Field(default_factory=tuple)
    blockers: tuple[str, ...] = Field(default_factory=tuple)
    missing_data: tuple[ClubOpsMissingDataResponse, ...] = Field(default_factory=tuple)
    lanes: dict[str, ClubOpsContractLaneResponse] = Field(default_factory=dict)
    players: tuple[dict[str, object], ...] = Field(default_factory=tuple)


class ClubFinanceOverviewResponse(CommonSchema):
    club_id: str
    currency: str
    balance_summary: dict[str, object] = Field(default_factory=dict)
    accounts: tuple[ClubFinanceAccountView, ...] = Field(default_factory=tuple)
    budget: ClubBudgetSnapshotView
    cashflow: ClubCashflowSummaryView


class ClubFinanceLedgerResponse(CommonSchema):
    club_id: str
    entries: tuple[ClubFinanceLedgerEntryView, ...] = Field(default_factory=tuple)


class ClubSponsorshipOverviewResponse(CommonSchema):
    club_id: str
    contracts: tuple[ClubSponsorshipContractView, ...] = Field(default_factory=tuple)
    visible_assets: tuple[ClubSponsorshipAssetView, ...] = Field(default_factory=tuple)
    active_contract_count: int
    total_settled_revenue_minor: int


class ClubSponsorshipCatalogResponse(CommonSchema):
    packages: tuple[ClubSponsorshipPackageView, ...] = Field(default_factory=tuple)


class AcademyOverviewResponse(CommonSchema):
    club_id: str
    programs: tuple[AcademyProgramView, ...] = Field(default_factory=tuple)
    players: tuple[AcademyPlayerView, ...] = Field(default_factory=tuple)
    training_cycles: tuple[AcademyTrainingCycleView, ...] = Field(default_factory=tuple)
    graduation_events: tuple[AcademyGraduationEventView, ...] = Field(default_factory=tuple)
    active_enrollment_count: int
    promoted_count: int


class AcademyPlayersResponse(CommonSchema):
    club_id: str
    players: tuple[AcademyPlayerView, ...] = Field(default_factory=tuple)


class AcademyTrainingCyclesResponse(CommonSchema):
    club_id: str
    training_cycles: tuple[AcademyTrainingCycleView, ...] = Field(default_factory=tuple)


class ScoutingOverviewResponse(CommonSchema):
    club_id: str
    regions: tuple[ScoutingRegionView, ...] = Field(default_factory=tuple)
    assignments: tuple[ScoutAssignmentView, ...] = Field(default_factory=tuple)
    prospects: tuple[YouthProspectView, ...] = Field(default_factory=tuple)
    pipeline_snapshot: YouthPipelineSnapshotView


class ScoutingProspectsResponse(CommonSchema):
    club_id: str
    prospects: tuple[YouthProspectView, ...] = Field(default_factory=tuple)


class ScoutingProspectDetailResponse(CommonSchema):
    prospect: YouthProspectView
    pipeline_snapshot: YouthPipelineSnapshotView


__all__ = [
    "AcademyOverviewResponse",
    "AcademyPlayersResponse",
    "AcademyTrainingCyclesResponse",
    "ClubOpsContractLaneResponse",
    "ClubOpsLaneStatus",
    "ClubOpsMissingDataResponse",
    "ClubFinanceLedgerResponse",
    "ClubFinanceOverviewResponse",
    "ClubSponsorshipCatalogResponse",
    "ClubSponsorshipOverviewResponse",
    "ClubOpsContractState",
    "FormationAuditEventResponse",
    "FormationContractEnvelopeResponse",
    "FormationContractResponse",
    "FormationCoordinatesResponse",
    "FormationHealthResponse",
    "FormationHistoryResponse",
    "FormationSlotResponse",
    "ScoutingOverviewResponse",
    "ScoutingProspectDetailResponse",
    "ScoutingProspectsResponse",
    "SquadReadinessResponse",
]
