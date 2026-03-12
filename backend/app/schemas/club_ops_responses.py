from __future__ import annotations

from pydantic import Field

from backend.app.common.schemas.base import CommonSchema
from backend.app.schemas.academy_core import (
    AcademyGraduationEventView,
    AcademyPlayerView,
    AcademyProgramView,
    AcademyTrainingCycleView,
)
from backend.app.schemas.club_finance_core import (
    ClubBudgetSnapshotView,
    ClubCashflowSummaryView,
    ClubFinanceAccountView,
    ClubFinanceLedgerEntryView,
)
from backend.app.schemas.scouting_core import (
    ScoutAssignmentView,
    ScoutingRegionView,
    YouthPipelineSnapshotView,
    YouthProspectView,
)
from backend.app.schemas.sponsorship_core import (
    ClubSponsorshipAssetView,
    ClubSponsorshipContractView,
    ClubSponsorshipPackageView,
)


class ClubFinanceOverviewResponse(CommonSchema):
    club_id: str
    currency: str
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
    "ClubFinanceLedgerResponse",
    "ClubFinanceOverviewResponse",
    "ClubSponsorshipCatalogResponse",
    "ClubSponsorshipOverviewResponse",
    "ScoutingOverviewResponse",
    "ScoutingProspectDetailResponse",
    "ScoutingProspectsResponse",
]
