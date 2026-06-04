from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.access_control.dependencies import require_bound_organization_access
from app.common.enums.academy_player_status import AcademyPlayerStatus
from app.models.access_control import OrganizationRole
from app.schemas.academy_core import AcademyPlayerView, AcademyProgramView
from app.schemas.club_finance_core import ClubBudgetSnapshotView, ClubCashflowSummaryView
from app.schemas.club_ops_requests import (
    CreateAcademyPlayerRequest,
    CreateAcademyProgramRequest,
    CreateScoutAssignmentRequest,
    CreateSponsorshipContractRequest,
    UpdateAcademyPlayerRequest,
    UpdateSponsorshipContractRequest,
    UpdateYouthProspectRequest,
)
from app.schemas.club_ops_responses import (
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
from app.schemas.scouting_core import ScoutAssignmentView, YouthPipelineSnapshotView, YouthProspectView
from app.schemas.sponsorship_core import ClubSponsorshipAssetView, ClubSponsorshipContractView
from app.services.academy_service import AcademyService, get_academy_service
from app.services.club_budget_service import ClubBudgetService, get_club_budget_service
from app.services.club_cashflow_service import ClubCashflowService, get_club_cashflow_service
from app.services.club_finance_service import ClubFinanceService, get_club_finance_service
from app.services.club_sponsorship_service import ClubSponsorshipService, get_club_sponsorship_service
from app.services.scouting_service import ScoutingService, get_scouting_service
from app.services.youth_pipeline_service import YouthPipelineService, get_youth_pipeline_service

router = APIRouter(prefix="/api/clubs/{club_id}", tags=["club-ops"])


@router.get(
    "/finances",
    response_model=ClubFinanceOverviewResponse,
    dependencies=[
        Depends(require_bound_organization_access(OrganizationRole.CLUB, forbidden_detail="club_access_required"))
    ],
)
def get_club_finances(
    club_id: str,
    finance_service: ClubFinanceService = Depends(get_club_finance_service),
) -> ClubFinanceOverviewResponse:
    return finance_service.get_finance_overview(club_id)


@router.get(
    "/finances/ledger",
    response_model=ClubFinanceLedgerResponse,
    dependencies=[
        Depends(require_bound_organization_access(OrganizationRole.CLUB, forbidden_detail="club_access_required"))
    ],
)
def get_club_finance_ledger(
    club_id: str,
    finance_service: ClubFinanceService = Depends(get_club_finance_service),
) -> ClubFinanceLedgerResponse:
    return finance_service.get_ledger(club_id)


@router.get(
    "/finances/budget",
    response_model=ClubBudgetSnapshotView,
    dependencies=[
        Depends(require_bound_organization_access(OrganizationRole.CLUB, forbidden_detail="club_access_required"))
    ],
)
def get_club_budget(
    club_id: str,
    budget_service: ClubBudgetService = Depends(get_club_budget_service),
) -> ClubBudgetSnapshotView:
    return budget_service.get_budget(club_id)


@router.get(
    "/finances/cashflow",
    response_model=ClubCashflowSummaryView,
    dependencies=[
        Depends(require_bound_organization_access(OrganizationRole.CLUB, forbidden_detail="club_access_required"))
    ],
)
def get_club_cashflow(
    club_id: str,
    cashflow_service: ClubCashflowService = Depends(get_club_cashflow_service),
) -> ClubCashflowSummaryView:
    return cashflow_service.get_cashflow(club_id)


@router.get(
    "/sponsorships",
    response_model=ClubSponsorshipOverviewResponse,
    dependencies=[
        Depends(require_bound_organization_access(OrganizationRole.CLUB, forbidden_detail="club_access_required"))
    ],
)
def get_club_sponsorships(
    club_id: str,
    sponsorship_service: ClubSponsorshipService = Depends(get_club_sponsorship_service),
) -> ClubSponsorshipOverviewResponse:
    return sponsorship_service.get_overview(club_id)


@router.get(
    "/sponsorships/catalog",
    response_model=ClubSponsorshipCatalogResponse,
    dependencies=[
        Depends(require_bound_organization_access(OrganizationRole.CLUB, forbidden_detail="club_access_required"))
    ],
)
def get_sponsorship_catalog(
    club_id: str,
    sponsorship_service: ClubSponsorshipService = Depends(get_club_sponsorship_service),
) -> ClubSponsorshipCatalogResponse:
    del club_id
    return sponsorship_service.list_catalog()


@router.post(
    "/sponsorships/contracts",
    response_model=ClubSponsorshipContractView,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(require_bound_organization_access(OrganizationRole.CLUB, forbidden_detail="club_access_required"))
    ],
)
def create_sponsorship_contract(
    club_id: str,
    payload: CreateSponsorshipContractRequest,
    sponsorship_service: ClubSponsorshipService = Depends(get_club_sponsorship_service),
) -> ClubSponsorshipContractView:
    return _handle_domain_errors(lambda: sponsorship_service.create_contract(club_id, payload))


@router.patch(
    "/sponsorships/contracts/{contract_id}",
    response_model=ClubSponsorshipContractView,
    dependencies=[
        Depends(require_bound_organization_access(OrganizationRole.CLUB, forbidden_detail="club_access_required"))
    ],
)
def update_sponsorship_contract(
    club_id: str,
    contract_id: str,
    payload: UpdateSponsorshipContractRequest,
    sponsorship_service: ClubSponsorshipService = Depends(get_club_sponsorship_service),
) -> ClubSponsorshipContractView:
    return _handle_domain_errors(lambda: sponsorship_service.update_contract(club_id, contract_id, payload))


@router.get(
    "/sponsorships/assets",
    response_model=tuple[ClubSponsorshipAssetView, ...],
    dependencies=[
        Depends(require_bound_organization_access(OrganizationRole.CLUB, forbidden_detail="club_access_required"))
    ],
)
def list_sponsorship_assets(
    club_id: str,
    sponsorship_service: ClubSponsorshipService = Depends(get_club_sponsorship_service),
) -> tuple[ClubSponsorshipAssetView, ...]:
    return sponsorship_service.list_assets(club_id)


@router.get(
    "/academy",
    response_model=AcademyOverviewResponse,
    dependencies=[
        Depends(require_bound_organization_access(OrganizationRole.CLUB, forbidden_detail="club_access_required"))
    ],
)
def get_academy_overview(
    club_id: str,
    academy_service: AcademyService = Depends(get_academy_service),
) -> AcademyOverviewResponse:
    return academy_service.get_overview(club_id)


@router.post(
    "/academy/programs",
    response_model=AcademyProgramView,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(require_bound_organization_access(OrganizationRole.CLUB, forbidden_detail="club_access_required"))
    ],
)
def create_academy_program(
    club_id: str,
    payload: CreateAcademyProgramRequest,
    academy_service: AcademyService = Depends(get_academy_service),
) -> AcademyProgramView:
    return _handle_domain_errors(lambda: academy_service.create_program(club_id, payload))


@router.get(
    "/academy/players",
    response_model=AcademyPlayersResponse,
    dependencies=[
        Depends(require_bound_organization_access(OrganizationRole.CLUB, forbidden_detail="club_access_required"))
    ],
)
def list_academy_players(
    club_id: str,
    academy_service: AcademyService = Depends(get_academy_service),
) -> AcademyPlayersResponse:
    return academy_service.list_players(club_id)


@router.post(
    "/academy/players",
    response_model=AcademyPlayerView,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(require_bound_organization_access(OrganizationRole.CLUB, forbidden_detail="club_access_required"))
    ],
)
def create_academy_player(
    club_id: str,
    payload: CreateAcademyPlayerRequest,
    academy_service: AcademyService = Depends(get_academy_service),
) -> AcademyPlayerView:
    return _handle_domain_errors(lambda: academy_service.create_player(club_id, payload))


@router.patch(
    "/academy/players/{player_id}",
    response_model=AcademyPlayerView,
    dependencies=[
        Depends(require_bound_organization_access(OrganizationRole.CLUB, forbidden_detail="club_access_required"))
    ],
)
def update_academy_player(
    club_id: str,
    player_id: str,
    payload: UpdateAcademyPlayerRequest,
    academy_service: AcademyService = Depends(get_academy_service),
) -> AcademyPlayerView:
    return _handle_domain_errors(lambda: academy_service.update_player(club_id, player_id, payload))


@router.get(
    "/academy/training-cycles",
    response_model=AcademyTrainingCyclesResponse,
    dependencies=[
        Depends(require_bound_organization_access(OrganizationRole.CLUB, forbidden_detail="club_access_required"))
    ],
)
def list_academy_training_cycles(
    club_id: str,
    academy_service: AcademyService = Depends(get_academy_service),
) -> AcademyTrainingCyclesResponse:
    return academy_service.list_training_cycles(club_id)


@router.get(
    "/scouting",
    response_model=ScoutingOverviewResponse,
    dependencies=[
        Depends(
            require_bound_organization_access(
                OrganizationRole.CLUB, OrganizationRole.SCOUT, forbidden_detail="club_access_required"
            )
        )
    ],
)
def get_scouting_overview(
    club_id: str,
    scouting_service: ScoutingService = Depends(get_scouting_service),
) -> ScoutingOverviewResponse:
    return scouting_service.get_overview(club_id)


@router.get(
    "/youth-pipeline",
    response_model=YouthPipelineSnapshotView,
    dependencies=[
        Depends(
            require_bound_organization_access(
                OrganizationRole.CLUB, OrganizationRole.SCOUT, forbidden_detail="club_access_required"
            )
        )
    ],
)
def get_youth_pipeline(
    club_id: str,
    youth_pipeline_service: YouthPipelineService = Depends(get_youth_pipeline_service),
) -> YouthPipelineSnapshotView:
    return youth_pipeline_service.get_snapshot(club_id)


@router.post(
    "/scouting/assignments",
    response_model=ScoutAssignmentView,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(
            require_bound_organization_access(
                OrganizationRole.CLUB, OrganizationRole.SCOUT, forbidden_detail="club_access_required"
            )
        )
    ],
)
def create_scout_assignment(
    club_id: str,
    payload: CreateScoutAssignmentRequest,
    scouting_service: ScoutingService = Depends(get_scouting_service),
) -> ScoutAssignmentView:
    return _handle_domain_errors(lambda: scouting_service.create_assignment(club_id, payload))


@router.get(
    "/scouting/prospects",
    response_model=ScoutingProspectsResponse,
    dependencies=[
        Depends(
            require_bound_organization_access(
                OrganizationRole.CLUB, OrganizationRole.SCOUT, forbidden_detail="club_access_required"
            )
        )
    ],
)
def list_scouting_prospects(
    club_id: str,
    scouting_service: ScoutingService = Depends(get_scouting_service),
) -> ScoutingProspectsResponse:
    return scouting_service.list_prospects(club_id)


@router.get(
    "/scouting/prospects/{prospect_id}",
    response_model=ScoutingProspectDetailResponse,
    dependencies=[
        Depends(
            require_bound_organization_access(
                OrganizationRole.CLUB, OrganizationRole.SCOUT, forbidden_detail="club_access_required"
            )
        )
    ],
)
def get_scouting_prospect(
    club_id: str,
    prospect_id: str,
    scouting_service: ScoutingService = Depends(get_scouting_service),
) -> ScoutingProspectDetailResponse:
    return _handle_domain_errors(lambda: scouting_service.get_prospect(club_id, prospect_id))


@router.patch(
    "/scouting/prospects/{prospect_id}",
    response_model=YouthProspectView,
    dependencies=[
        Depends(
            require_bound_organization_access(
                OrganizationRole.CLUB, OrganizationRole.SCOUT, forbidden_detail="club_access_required"
            )
        )
    ],
)
def update_scouting_prospect(
    club_id: str,
    prospect_id: str,
    payload: UpdateYouthProspectRequest,
    scouting_service: ScoutingService = Depends(get_scouting_service),
) -> YouthProspectView:
    return _handle_domain_errors(lambda: scouting_service.update_prospect(club_id, prospect_id, payload))


@router.get(
    "/dashboard",
    dependencies=[
        Depends(require_bound_organization_access(OrganizationRole.CLUB, forbidden_detail="club_access_required"))
    ],
)
def get_canonical_club_dashboard(
    club_id: str,
    finance_service: ClubFinanceService = Depends(get_club_finance_service),
    academy_service: AcademyService = Depends(get_academy_service),
    sponsorship_service: ClubSponsorshipService = Depends(get_club_sponsorship_service),
    scouting_service: ScoutingService = Depends(get_scouting_service),
) -> dict[str, object]:
    finance = finance_service.get_finance_overview(club_id)
    academy = academy_service.get_overview(club_id)
    sponsorships = sponsorship_service.get_overview(club_id)
    scouting = scouting_service.get_overview(club_id)
    recent_activity = [
        f"{len(academy.programs)} academy programs tracked",
        f"{len(sponsorships.contracts)} sponsorship contracts recorded",
        f"{len(scouting.prospects)} scouting prospects in pipeline",
    ]
    return {
        "club_id": club_id,
        "name": _club_label(finance_service, club_id),
        "total_squad_value": None,
        "alerts": _club_dashboard_alerts(
            academy_players=len(academy.players),
            active_sponsorships=sponsorships.active_contract_count,
            scouting_prospects=len(scouting.prospects),
        ),
        "recent_activity": recent_activity,
        "finance_updated_at": finance.balance_summary.get("updated_at"),
    }


@router.get(
    "/squad/readiness",
    dependencies=[
        Depends(require_bound_organization_access(OrganizationRole.CLUB, forbidden_detail="club_access_required"))
    ],
)
def get_canonical_squad_readiness(
    club_id: str,
    academy_service: AcademyService = Depends(get_academy_service),
) -> dict[str, object]:
    players = build_squad_players_from_academy(club_id, academy_service)
    eligible_count = sum(1 for player in players if bool(player.get("selection_ready")))
    injured_count = sum(1 for player in players if player.get("availability") == "injured")
    suspended_count = sum(1 for player in players if player.get("availability") == "suspended")
    return {
        "eligible_count": eligible_count,
        "injured_count": injured_count,
        "suspended_count": suspended_count,
        "available_for_next_fixture": eligible_count,
        "readiness_score": round(min(100, (eligible_count / 11) * 100), 2) if players else None,
        "warnings": [] if eligible_count >= 11 else ("Formation publish requires 11 backend-eligible players.",),
    }


@router.get(
    "/staff",
    dependencies=[
        Depends(require_bound_organization_access(OrganizationRole.CLUB, forbidden_detail="club_access_required"))
    ],
)
def get_canonical_club_staff(club_id: str) -> None:
    del club_id
    return {"members": (), "state": "empty", "reason": "No staff contracts are recorded for this club yet."}


@router.get(
    "/rankings",
    dependencies=[
        Depends(require_bound_organization_access(OrganizationRole.CLUB, forbidden_detail="club_access_required"))
    ],
)
def get_canonical_club_rankings(club_id: str) -> None:
    del club_id
    return {"rankings": (), "state": "empty", "reason": "No published ranking rows are recorded for this club yet."}


@router.get(
    "/squad",
    dependencies=[
        Depends(require_bound_organization_access(OrganizationRole.CLUB, forbidden_detail="club_access_required"))
    ],
)
def get_canonical_squad_roster(
    club_id: str,
    academy_service: AcademyService = Depends(get_academy_service),
) -> dict[str, object]:
    return {"club_id": club_id, "players": build_squad_players_from_academy(club_id, academy_service)}


@router.get(
    "/squad/selection-ready",
    dependencies=[
        Depends(require_bound_organization_access(OrganizationRole.CLUB, forbidden_detail="club_access_required"))
    ],
)
def get_canonical_selection_ready_players(
    club_id: str,
    academy_service: AcademyService = Depends(get_academy_service),
) -> dict[str, object]:
    players = [
        {
            "id": player["id"],
            "name": player["name"],
            "position": player["position"],
            "eligible": True,
        }
        for player in build_squad_players_from_academy(club_id, academy_service)
        if bool(player.get("selection_ready"))
    ]
    return {"club_id": club_id, "players": players}


@router.get(
    "/squad/availability",
    dependencies=[
        Depends(require_bound_organization_access(OrganizationRole.CLUB, forbidden_detail="club_access_required"))
    ],
)
def get_canonical_squad_availability(
    club_id: str,
    academy_service: AcademyService = Depends(get_academy_service),
) -> dict[str, object]:
    players = build_squad_players_from_academy(club_id, academy_service)
    return {
        "players": [
            {"player_id": player["id"], "name": player["name"], "position": player["position"]} for player in players
        ],
        "fixtures": (),
        "cells": (),
        "rows": [
            {
                "player_id": player["id"],
                "name": player["name"],
                "position": player["position"],
                "statuses": (player["availability"],),
            }
            for player in players
        ],
    }


@router.get(
    "/squad/injuries",
    dependencies=[
        Depends(require_bound_organization_access(OrganizationRole.CLUB, forbidden_detail="club_access_required"))
    ],
)
def get_canonical_squad_injuries(club_id: str) -> None:
    del club_id
    return {"injuries": (), "state": "empty", "reason": "No injury records are recorded for this club yet."}


@router.get(
    "/squad/chemistry",
    dependencies=[
        Depends(require_bound_organization_access(OrganizationRole.CLUB, forbidden_detail="club_access_required"))
    ],
)
def get_canonical_squad_chemistry(club_id: str) -> None:
    del club_id
    return {"overall_score": None, "warnings": ("Chemistry model is not mounted for this club yet.",)}


@router.get(
    "/squad/contracts",
    dependencies=[
        Depends(require_bound_organization_access(OrganizationRole.CLUB, forbidden_detail="club_access_required"))
    ],
)
def get_canonical_squad_contracts(club_id: str) -> None:
    del club_id
    return {"contracts": (), "state": "empty", "reason": "No player contract records are recorded for this club yet."}


@router.get(
    "/squad/scouting",
    dependencies=[
        Depends(require_bound_organization_access(OrganizationRole.CLUB, forbidden_detail="club_access_required"))
    ],
)
def get_canonical_squad_scouting(
    club_id: str,
    scouting_service: ScoutingService = Depends(get_scouting_service),
) -> dict[str, object]:
    scouting = scouting_service.get_overview(club_id)
    notes: list[dict[str, object]] = []
    for prospect in scouting.prospects:
        for report in prospect.reports:
            notes.append(
                {
                    "player_id": prospect.academy_player_id or prospect.id,
                    "author_id": report.assignment_id,
                    "content": report.summary_text,
                    "created_at": report.created_at,
                    "tags": (*report.strengths, *report.development_flags),
                }
            )
    return {"club_id": club_id, "scouting_notes": notes}


def _raise_canonical_backend_gap(*, club_id: str, code: str, message: str) -> None:
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={
            "state": "blocked",
            "club_id": club_id,
            "code": code,
            "reason": message,
        },
    )


def _club_label(finance_service: ClubFinanceService, club_id: str) -> str:
    finance_service.ensure_club_setup(club_id)
    with finance_service.store.lock:
        return finance_service.store.club_labels.get(club_id, club_id)


def _club_dashboard_alerts(*, academy_players: int, active_sponsorships: int, scouting_prospects: int) -> tuple[str, ...]:
    alerts: list[str] = []
    if academy_players == 0:
        alerts.append("No academy players are registered.")
    if active_sponsorships == 0:
        alerts.append("No active sponsorship contracts are recorded.")
    if scouting_prospects == 0:
        alerts.append("No scouting prospects are currently tracked.")
    return tuple(alerts)


def build_squad_players_from_academy(
    club_id: str,
    academy_service: AcademyService,
) -> tuple[dict[str, Any], ...]:
    academy = academy_service.get_overview(club_id)
    return tuple(_academy_player_to_squad_player(player) for player in academy.players)


def _academy_player_to_squad_player(player: AcademyPlayerView) -> dict[str, Any]:
    status = player.status
    if not isinstance(status, AcademyPlayerStatus):
        status = AcademyPlayerStatus(str(status))
    selection_ready = status == AcademyPlayerStatus.PROMOTED
    availability = "available" if selection_ready else "unknown"
    return {
        "id": player.id,
        "name": player.display_name,
        "position": player.primary_position,
        "age": player.age,
        "availability": availability,
        "selection_ready": selection_ready,
        "morale": {"score": 0, "label": "unknown"},
        "chemistry_fit": {"overall_score": 0, "position_fit": 0, "team_fit": 0, "warnings": ()},
        "contract_status": {"player_id": player.id},
        "stats": {"rating": player.overall_rating},
        "scouting_notes": (
            {
                "player_id": player.id,
                "content": player.pathway_note,
                "created_at": player.last_progressed_at,
                "tags": (str(status.value),),
            },
        )
        if player.pathway_note
        else (),
    }


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
