from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.auth.dependencies import get_current_admin
from app.common.enums.academy_player_status import AcademyPlayerStatus
from app.common.enums.player_pathway_stage import PlayerPathwayStage
from app.common.enums.sponsorship_status import SponsorshipStatus
from app.schemas.club_ops_requests import (
    CreateAcademyPlayerRequest,
    CreateAcademyProgramRequest,
    CreateScoutAssignmentRequest,
    CreateSponsorshipContractRequest,
    UpdateAcademyPlayerRequest,
    UpdateSponsorshipContractRequest,
    UpdateYouthProspectRequest,
)
from app.routes.admin_club_ops import router as admin_club_ops_router
from app.routes.club_ops import router as club_ops_router
from app.services.academy_graduation_service import AcademyGraduationService, get_academy_graduation_service
from app.services.academy_progression_service import AcademyProgressionService, get_academy_progression_service
from app.services.academy_service import AcademyService, get_academy_service
from app.services.academy_training_service import AcademyTrainingService, get_academy_training_service
from app.services.club_budget_service import ClubBudgetService, get_club_budget_service
from app.services.club_cashflow_service import ClubCashflowService, get_club_cashflow_service
from app.services.club_finance_service import ClubFinanceService, ClubOpsStore, get_club_finance_service
from app.services.club_ops_admin_service import ClubOpsAdminService, get_club_ops_admin_service
from app.services.club_ops_analytics_service import ClubOpsAnalyticsService, get_club_ops_analytics_service
from app.services.club_sponsorship_service import ClubSponsorshipService, get_club_sponsorship_service
from app.services.regen_service import RegenService
from app.services.scout_assignment_service import ScoutAssignmentService, get_scout_assignment_service
from app.services.scouting_service import ScoutingService, get_scouting_service
from app.services.sponsorship_catalog_service import SponsorshipCatalogService, get_sponsorship_catalog_service
from app.services.sponsorship_payout_service import SponsorshipPayoutService, get_sponsorship_payout_service
from app.services.youth_pipeline_service import YouthPipelineService, get_youth_pipeline_service
from app.services.youth_prospect_service import YouthProspectService, get_youth_prospect_service


def build_club_ops_services() -> dict[str, object]:
    store = ClubOpsStore()
    finance = ClubFinanceService(store=store)
    budget = ClubBudgetService(finance_service=finance)
    cashflow = ClubCashflowService(finance_service=finance)
    catalog = SponsorshipCatalogService()
    payouts = SponsorshipPayoutService(finance_service=finance)
    sponsorship = ClubSponsorshipService(
        store=store,
        finance_service=finance,
        catalog_service=catalog,
        payout_service=payouts,
    )
    progression = AcademyProgressionService()
    training = AcademyTrainingService()
    graduation = AcademyGraduationService()
    academy = AcademyService(
        store=store,
        finance_service=finance,
        progression_service=progression,
        training_service=training,
        graduation_service=graduation,
    )
    assignment = ScoutAssignmentService()
    prospect = YouthProspectService(store=store)
    pipeline = YouthPipelineService(store=store)
    scouting = ScoutingService(
        store=store,
        finance_service=finance,
        assignment_service=assignment,
        prospect_service=prospect,
        pipeline_service=pipeline,
        academy_service=academy,
    )
    regen = RegenService(store=store)
    analytics = ClubOpsAnalyticsService(store=store, finance_service=finance)
    admin = ClubOpsAdminService(store=store, finance_service=finance, analytics_service=analytics)
    return {
        "store": store,
        "finance": finance,
        "budget": budget,
        "cashflow": cashflow,
        "catalog": catalog,
        "payouts": payouts,
        "sponsorship": sponsorship,
        "progression": progression,
        "training": training,
        "graduation": graduation,
        "academy": academy,
        "assignment": assignment,
        "prospect": prospect,
        "pipeline": pipeline,
        "scouting": scouting,
        "regen": regen,
        "analytics": analytics,
        "admin": admin,
        "admin_user": SimpleNamespace(id="admin-1", role="admin", is_admin=True),
    }


@pytest.fixture()
def club_ops_services() -> dict[str, object]:
    return build_club_ops_services()


@pytest.fixture()
def club_ops_app(club_ops_services):
    app = FastAPI()
    app.include_router(club_ops_router)
    app.include_router(admin_club_ops_router)
    app.dependency_overrides[get_club_finance_service] = lambda: club_ops_services["finance"]
    app.dependency_overrides[get_club_budget_service] = lambda: club_ops_services["budget"]
    app.dependency_overrides[get_club_cashflow_service] = lambda: club_ops_services["cashflow"]
    app.dependency_overrides[get_sponsorship_catalog_service] = lambda: club_ops_services["catalog"]
    app.dependency_overrides[get_sponsorship_payout_service] = lambda: club_ops_services["payouts"]
    app.dependency_overrides[get_club_sponsorship_service] = lambda: club_ops_services["sponsorship"]
    app.dependency_overrides[get_academy_progression_service] = lambda: club_ops_services["progression"]
    app.dependency_overrides[get_academy_training_service] = lambda: club_ops_services["training"]
    app.dependency_overrides[get_academy_graduation_service] = lambda: club_ops_services["graduation"]
    app.dependency_overrides[get_academy_service] = lambda: club_ops_services["academy"]
    app.dependency_overrides[get_scout_assignment_service] = lambda: club_ops_services["assignment"]
    app.dependency_overrides[get_youth_prospect_service] = lambda: club_ops_services["prospect"]
    app.dependency_overrides[get_youth_pipeline_service] = lambda: club_ops_services["pipeline"]
    app.dependency_overrides[get_scouting_service] = lambda: club_ops_services["scouting"]
    app.dependency_overrides[get_club_ops_analytics_service] = lambda: club_ops_services["analytics"]
    app.dependency_overrides[get_club_ops_admin_service] = lambda: club_ops_services["admin"]
    app.dependency_overrides[get_current_admin] = lambda: club_ops_services["admin_user"]
    return app


@pytest.fixture()
def club_ops_client(club_ops_app):
    with TestClient(club_ops_app) as client:
        yield client


@pytest.fixture()
def seeded_ops_services(club_ops_services):
    finance = club_ops_services["finance"]
    sponsorship = club_ops_services["sponsorship"]
    academy = club_ops_services["academy"]
    scouting = club_ops_services["scouting"]

    finance.get_finance_overview("club-alpha")
    contract = sponsorship.create_contract(
        "club-alpha",
        payload=CreateSponsorshipContractRequest(
            package_code="community-jersey-front",
            sponsor_name="Harbor Energy",
            duration_months=6,
            activate_immediately=True,
        ),
    )
    academy_program = academy.create_program(
        "club-alpha",
        payload=CreateAcademyProgramRequest(
            name="Elite Pathway",
            program_type="elite_development",
            budget_minor=140_000,
            cycle_length_weeks=6,
            focus_attributes=("technical", "tactical"),
        ),
    )
    academy_player = academy.create_player(
        "club-alpha",
        payload=CreateAcademyPlayerRequest(
            program_id=academy_program.id,
            display_name="Kelechi Bright",
            age=17,
            primary_position="CM",
        ),
    )
    academy.update_player(
        "club-alpha",
        academy_player.id,
        payload=UpdateAcademyPlayerRequest(
            attendance_score=96,
            coach_assessment=95,
            completed_cycles_delta=3,
            attribute_deltas={"technical": 24, "tactical": 24, "physical": 22, "mentality": 22},
            status=AcademyPlayerStatus.PROMOTED,
        ),
    )
    assignment = scouting.create_assignment(
        "club-alpha",
        payload=CreateScoutAssignmentRequest(
            region_code="domestic-core",
            focus_area="Ball progression",
            budget_minor=45_000,
            scout_count=2,
        ),
    )
    prospect = scouting.list_prospects("club-alpha").prospects[0]
    scouting.update_prospect(
        "club-alpha",
        prospect.id,
        payload=UpdateYouthProspectRequest(
            pathway_stage=PlayerPathwayStage.ACADEMY_SIGNED,
            convert_to_academy=True,
            academy_program_id=academy_program.id,
        ),
    )
    scouting.update_prospect(
        "club-alpha",
        scouting.list_prospects("club-alpha").prospects[0].id,
        payload=UpdateYouthProspectRequest(
            pathway_stage=PlayerPathwayStage.PROMOTED,
        ),
    )
    sponsorship.update_contract(
        "club-alpha",
        contract.id,
        payload=UpdateSponsorshipContractRequest(
            moderation_status="approved",
            status=SponsorshipStatus.ACTIVE,
        ),
    )
    return club_ops_services
