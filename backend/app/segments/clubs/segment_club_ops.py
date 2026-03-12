from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.schemas.academy_core import AcademyPlayerView, AcademyProgramView
from backend.app.schemas.club_finance_core import ClubBudgetSnapshotView, ClubCashflowSummaryView
from backend.app.schemas.club_ops_requests import (
    CreateAcademyPlayerRequest,
    CreateAcademyProgramRequest,
    CreateScoutAssignmentRequest,
    CreateSponsorshipContractRequest,
    UpdateAcademyPlayerRequest,
    UpdateSponsorshipContractRequest,
    UpdateYouthProspectRequest,
)
from backend.app.schemas.club_ops_responses import (
    AcademyOverviewResponse,
    AcademyPlayersResponse,
    AcademyTrainingCyclesResponse,
    ClubFinanceLedgerResponse,
    ClubFinanceOverviewResponse,
    ClubSponsorshipCatalogResponse,
    ClubSponsorshipOverviewResponse,
    ScoutingOverviewResponse,
    ScoutingProspectDetailResponse,
    ScoutingProspectsResponse,
)
from backend.app.schemas.scouting_core import ScoutAssignmentView, YouthProspectView
from backend.app.schemas.sponsorship_core import ClubSponsorshipAssetView, ClubSponsorshipContractView
from backend.app.services.academy_service import AcademyService, get_academy_service
from backend.app.services.club_budget_service import ClubBudgetService, get_club_budget_service
from backend.app.services.club_cashflow_service import ClubCashflowService, get_club_cashflow_service
from backend.app.services.club_finance_service import ClubFinanceService, get_club_finance_service
from backend.app.services.club_sponsorship_service import ClubSponsorshipService, get_club_sponsorship_service
from backend.app.services.scouting_service import ScoutingService, get_scouting_service

router = APIRouter(prefix="/api/clubs/{club_id}", tags=["club-ops"])


@router.get("/finances", response_model=ClubFinanceOverviewResponse)
def get_club_finances(
    club_id: str,
    finance_service: ClubFinanceService = Depends(get_club_finance_service),
) -> ClubFinanceOverviewResponse:
    return finance_service.get_finance_overview(club_id)


@router.get("/finances/ledger", response_model=ClubFinanceLedgerResponse)
def get_club_finance_ledger(
    club_id: str,
    finance_service: ClubFinanceService = Depends(get_club_finance_service),
) -> ClubFinanceLedgerResponse:
    return finance_service.get_ledger(club_id)


@router.get("/finances/budget", response_model=ClubBudgetSnapshotView)
def get_club_budget(
    club_id: str,
    budget_service: ClubBudgetService = Depends(get_club_budget_service),
) -> ClubBudgetSnapshotView:
    return budget_service.get_budget(club_id)


@router.get("/finances/cashflow", response_model=ClubCashflowSummaryView)
def get_club_cashflow(
    club_id: str,
    cashflow_service: ClubCashflowService = Depends(get_club_cashflow_service),
) -> ClubCashflowSummaryView:
    return cashflow_service.get_cashflow(club_id)


@router.get("/sponsorships", response_model=ClubSponsorshipOverviewResponse)
def get_club_sponsorships(
    club_id: str,
    sponsorship_service: ClubSponsorshipService = Depends(get_club_sponsorship_service),
) -> ClubSponsorshipOverviewResponse:
    return sponsorship_service.get_overview(club_id)


@router.get("/sponsorships/catalog", response_model=ClubSponsorshipCatalogResponse)
def get_sponsorship_catalog(
    club_id: str,
    sponsorship_service: ClubSponsorshipService = Depends(get_club_sponsorship_service),
) -> ClubSponsorshipCatalogResponse:
    del club_id
    return sponsorship_service.list_catalog()


@router.post("/sponsorships/contracts", response_model=ClubSponsorshipContractView, status_code=status.HTTP_201_CREATED)
def create_sponsorship_contract(
    club_id: str,
    payload: CreateSponsorshipContractRequest,
    sponsorship_service: ClubSponsorshipService = Depends(get_club_sponsorship_service),
) -> ClubSponsorshipContractView:
    return _handle_domain_errors(lambda: sponsorship_service.create_contract(club_id, payload))


@router.patch("/sponsorships/contracts/{contract_id}", response_model=ClubSponsorshipContractView)
def update_sponsorship_contract(
    club_id: str,
    contract_id: str,
    payload: UpdateSponsorshipContractRequest,
    sponsorship_service: ClubSponsorshipService = Depends(get_club_sponsorship_service),
) -> ClubSponsorshipContractView:
    return _handle_domain_errors(lambda: sponsorship_service.update_contract(club_id, contract_id, payload))


@router.get("/sponsorships/assets", response_model=tuple[ClubSponsorshipAssetView, ...])
def list_sponsorship_assets(
    club_id: str,
    sponsorship_service: ClubSponsorshipService = Depends(get_club_sponsorship_service),
) -> tuple[ClubSponsorshipAssetView, ...]:
    return sponsorship_service.list_assets(club_id)


@router.get("/academy", response_model=AcademyOverviewResponse)
def get_academy_overview(
    club_id: str,
    academy_service: AcademyService = Depends(get_academy_service),
) -> AcademyOverviewResponse:
    return academy_service.get_overview(club_id)


@router.post("/academy/programs", response_model=AcademyProgramView, status_code=status.HTTP_201_CREATED)
def create_academy_program(
    club_id: str,
    payload: CreateAcademyProgramRequest,
    academy_service: AcademyService = Depends(get_academy_service),
) -> AcademyProgramView:
    return _handle_domain_errors(lambda: academy_service.create_program(club_id, payload))


@router.get("/academy/players", response_model=AcademyPlayersResponse)
def list_academy_players(
    club_id: str,
    academy_service: AcademyService = Depends(get_academy_service),
) -> AcademyPlayersResponse:
    return academy_service.list_players(club_id)


@router.post("/academy/players", response_model=AcademyPlayerView, status_code=status.HTTP_201_CREATED)
def create_academy_player(
    club_id: str,
    payload: CreateAcademyPlayerRequest,
    academy_service: AcademyService = Depends(get_academy_service),
) -> AcademyPlayerView:
    return _handle_domain_errors(lambda: academy_service.create_player(club_id, payload))


@router.patch("/academy/players/{player_id}", response_model=AcademyPlayerView)
def update_academy_player(
    club_id: str,
    player_id: str,
    payload: UpdateAcademyPlayerRequest,
    academy_service: AcademyService = Depends(get_academy_service),
) -> AcademyPlayerView:
    return _handle_domain_errors(lambda: academy_service.update_player(club_id, player_id, payload))


@router.get("/academy/training-cycles", response_model=AcademyTrainingCyclesResponse)
def list_academy_training_cycles(
    club_id: str,
    academy_service: AcademyService = Depends(get_academy_service),
) -> AcademyTrainingCyclesResponse:
    return academy_service.list_training_cycles(club_id)


@router.get("/scouting", response_model=ScoutingOverviewResponse)
def get_scouting_overview(
    club_id: str,
    scouting_service: ScoutingService = Depends(get_scouting_service),
) -> ScoutingOverviewResponse:
    return scouting_service.get_overview(club_id)


@router.post("/scouting/assignments", response_model=ScoutAssignmentView, status_code=status.HTTP_201_CREATED)
def create_scout_assignment(
    club_id: str,
    payload: CreateScoutAssignmentRequest,
    scouting_service: ScoutingService = Depends(get_scouting_service),
) -> ScoutAssignmentView:
    return _handle_domain_errors(lambda: scouting_service.create_assignment(club_id, payload))


@router.get("/scouting/prospects", response_model=ScoutingProspectsResponse)
def list_scouting_prospects(
    club_id: str,
    scouting_service: ScoutingService = Depends(get_scouting_service),
) -> ScoutingProspectsResponse:
    return scouting_service.list_prospects(club_id)


@router.get("/scouting/prospects/{prospect_id}", response_model=ScoutingProspectDetailResponse)
def get_scouting_prospect(
    club_id: str,
    prospect_id: str,
    scouting_service: ScoutingService = Depends(get_scouting_service),
) -> ScoutingProspectDetailResponse:
    return _handle_domain_errors(lambda: scouting_service.get_prospect(club_id, prospect_id))


@router.patch("/scouting/prospects/{prospect_id}", response_model=YouthProspectView)
def update_scouting_prospect(
    club_id: str,
    prospect_id: str,
    payload: UpdateYouthProspectRequest,
    scouting_service: ScoutingService = Depends(get_scouting_service),
) -> YouthProspectView:
    return _handle_domain_errors(lambda: scouting_service.update_prospect(club_id, prospect_id, payload))


def _handle_domain_errors(func):
    try:
        return func()
    except ValueError as exc:
        detail = str(exc)
        status_code = status.HTTP_400_BAD_REQUEST
        if detail in {
            "academy_player_not_found",
            "academy_program_not_found",
            "contract_not_found",
            "package_not_found",
            "prospect_not_found",
            "scouting_region_not_found",
        }:
            status_code = status.HTTP_404_NOT_FOUND
        elif detail in {"insufficient_operating_balance", "sponsorship_slot_unavailable"}:
            status_code = status.HTTP_409_CONFLICT
        raise HTTPException(status_code=status_code, detail=detail) from exc


__all__ = ["router"]
