from __future__ import annotations

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.common.enums.academy_player_status import AcademyPlayerStatus
from app.common.enums.academy_program_type import AcademyProgramType
from app.common.enums.club_finance_account_type import ClubFinanceAccountType
from app.common.enums.player_pathway_stage import PlayerPathwayStage
from app.common.enums.sponsorship_status import SponsorshipStatus
from app.models.academy_graduation_event import AcademyGraduationEvent
from app.models.academy_player import AcademyPlayer
from app.models.academy_player_progress import AcademyPlayerProgress
from app.models.academy_program import AcademyProgram
from app.models.academy_training_cycle import AcademyTrainingCycle
from app.models.base import Base
from app.models.club_finance_account import ClubFinanceAccount
from app.models.club_finance_ledger_entry import ClubFinanceLedgerEntry
from app.models.club_ops_state_snapshot import ClubOpsStateSnapshot
from app.models.club_sponsorship_asset import ClubSponsorshipAsset
from app.models.club_sponsorship_contract import ClubSponsorshipContract
from app.models.club_sponsorship_payout import ClubSponsorshipPayout
from app.models.scout_assignment import ScoutAssignment
from app.models.youth_pipeline_snapshot import YouthPipelineSnapshot
from app.models.youth_prospect import YouthProspect
from app.models.youth_prospect_report import YouthProspectReport
from app.schemas.club_ops_requests import (
    CreateAcademyProgramRequest,
    CreateScoutAssignmentRequest,
    CreateSponsorshipContractRequest,
    UpdateAcademyPlayerRequest,
    UpdateSponsorshipContractRequest,
    UpdateYouthProspectRequest,
)
from app.services.academy_service import AcademyService
from app.services.club_finance_service import ClubFinanceService, ClubOpsStore, get_club_ops_store
from app.services.club_sponsorship_service import ClubSponsorshipService
from app.services.scouting_service import ScoutingService
from app.services.sponsorship_payout_service import SponsorshipPayoutService
from app.services.youth_pipeline_service import YouthPipelineService
from app.services.youth_prospect_service import YouthProspectService


def _session_factory():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False), engine


def test_default_club_ops_store_binds_session_factory() -> None:
    store = get_club_ops_store()
    assert store.session_factory is not None


def test_club_ops_finance_state_survives_store_recreation_and_projects_to_orm() -> None:
    session_factory, engine = _session_factory()
    try:
        first_store = ClubOpsStore(session_factory=session_factory)
        finance = ClubFinanceService(store=first_store)
        finance.ensure_club_setup("club-persistence-test")
        finance.record_manual_adjustment(
            "club-persistence-test",
            amount_minor=1250,
            description="Durability regression test adjustment",
            reference_id="durability-test",
        )

        with pytest.raises(ValueError, match="insufficient_operating_balance"):
            finance.record_manual_adjustment(
                "club-persistence-test",
                amount_minor=-9_000_000,
                description="Should roll back without mutating balance",
                reference_id="failed-debit",
            )

        # A distinct store simulates a fresh service instance / worker process.
        second_store = ClubOpsStore(session_factory=session_factory)
        second_finance = ClubFinanceService(store=second_store)
        overview = second_finance.get_finance_overview("club-persistence-test")
        operating = next(
            account for account in overview.accounts if account.account_type == ClubFinanceAccountType.OPERATING_BALANCE
        )
        assert operating.balance_minor == 1_501_250
        ledger = second_finance.get_ledger("club-persistence-test")
        assert any(entry.reference_id == "durability-test" for entry in ledger.entries)
        assert all(entry.reference_id != "failed-debit" for entry in ledger.entries)

        with session_factory() as session:
            snapshot = session.get(ClubOpsStateSnapshot, "global")
            assert snapshot is not None
            account = session.scalar(
                select(ClubFinanceAccount).where(
                    ClubFinanceAccount.club_id == "club-persistence-test",
                    ClubFinanceAccount.account_type == ClubFinanceAccountType.OPERATING_BALANCE,
                )
            )
            assert account is not None
            assert account.balance_minor == 1_501_250
            entry = session.scalar(
                select(ClubFinanceLedgerEntry).where(
                    ClubFinanceLedgerEntry.club_id == "club-persistence-test",
                    ClubFinanceLedgerEntry.reference_id == "durability-test",
                )
            )
            assert entry is not None
            assert entry.amount_minor == 1250

        # Updates committed by the second store must also be visible when the
        # first store enters its lock on subsequent operations.
        second_finance.record_manual_adjustment(
            "club-persistence-test",
            amount_minor=750,
            description="Second worker adjustment",
            reference_id="second-worker",
        )
        with first_store.lock:
            assert (
                first_store.accounts_by_club["club-persistence-test"][
                    ClubFinanceAccountType.OPERATING_BALANCE
                ].balance_minor
                == 1_502_000
            )
    finally:
        engine.dispose()


def test_sponsorship_academy_and_scouting_persist_across_store_instances() -> None:
    session_factory, engine = _session_factory()
    try:
        club_id = "club-full-ops-persistence"
        store_1 = ClubOpsStore(session_factory=session_factory)
        finance_1 = ClubFinanceService(store=store_1)
        sponsorship_1 = ClubSponsorshipService(
            store=store_1,
            finance_service=finance_1,
            payout_service=SponsorshipPayoutService(finance_service=finance_1),
        )
        academy_1 = AcademyService(store=store_1, finance_service=finance_1)
        scouting_1 = ScoutingService(
            store=store_1,
            finance_service=finance_1,
            prospect_service=YouthProspectService(store=store_1),
            pipeline_service=YouthPipelineService(store=store_1),
            academy_service=academy_1,
        )

        contract = sponsorship_1.create_contract(
            club_id,
            CreateSponsorshipContractRequest(
                package_code="community-jersey-front",
                sponsor_name="persist-sponsor",
                duration_months=3,
                payout_schedule="upfront",
                custom_copy="Persist Sponsor Copy",
                activate_immediately=True,
            ),
        )
        assert contract.status == SponsorshipStatus.PENDING_APPROVAL

        approved_contract = sponsorship_1.update_contract(
            club_id,
            contract.id,
            UpdateSponsorshipContractRequest(
                moderation_status="approved",
                settle_due_payouts=True,
            ),
        )
        assert approved_contract.status == SponsorshipStatus.COMPLETED
        assert approved_contract.settled_amount_minor == approved_contract.contract_amount_minor

        program = academy_1.create_program(
            club_id,
            CreateAcademyProgramRequest(
                name="Elite Pathway",
                program_type=AcademyProgramType.ELITE_DEVELOPMENT,
                budget_minor=90_000,
                cycle_length_weeks=6,
                focus_attributes=("technical", "tactical"),
            ),
        )
        assignment = scouting_1.create_assignment(
            club_id,
            CreateScoutAssignmentRequest(
                region_code="domestic-core",
                focus_area="Midfield progression",
                budget_minor=45_000,
                scout_count=2,
                duration_weeks=4,
            ),
        )
        assert len(assignment.generated_prospect_ids) >= 2
        prospect_id = assignment.generated_prospect_ids[0]

        converted_prospect = scouting_1.update_prospect(
            club_id,
            prospect_id,
            UpdateYouthProspectRequest(
                pathway_stage=PlayerPathwayStage.ACADEMY_SIGNED,
                follow_priority=9,
                convert_to_academy=True,
                academy_program_id=program.id,
            ),
        )
        assert converted_prospect.academy_player_id is not None

        promoted_player = academy_1.update_player(
            club_id,
            converted_prospect.academy_player_id,
            UpdateAcademyPlayerRequest(
                attendance_score=95,
                coach_assessment=92,
                completed_cycles_delta=3,
                attribute_deltas={"technical": 12, "tactical": 10},
                status=AcademyPlayerStatus.PROMOTED,
                pathway_note="Promoted to first-team squad.",
            ),
        )
        assert promoted_player.status == AcademyPlayerStatus.PROMOTED

        # Recreate all services bound to a brand-new ClubOpsStore backed by the same DB.
        store_2 = ClubOpsStore(session_factory=session_factory)
        finance_2 = ClubFinanceService(store=store_2)
        sponsorship_2 = ClubSponsorshipService(
            store=store_2,
            finance_service=finance_2,
            payout_service=SponsorshipPayoutService(finance_service=finance_2),
        )
        academy_2 = AcademyService(store=store_2, finance_service=finance_2)
        scouting_2 = ScoutingService(
            store=store_2,
            finance_service=finance_2,
            prospect_service=YouthProspectService(store=store_2),
            pipeline_service=YouthPipelineService(store=store_2),
            academy_service=academy_2,
        )

        sponsorship_overview = sponsorship_2.get_overview(club_id)
        assert len(sponsorship_overview.contracts) == 1
        assert sponsorship_overview.contracts[0].id == contract.id
        assert sponsorship_overview.contracts[0].status == SponsorshipStatus.COMPLETED
        assert sponsorship_overview.total_settled_revenue_minor == approved_contract.contract_amount_minor

        academy_overview = academy_2.get_overview(club_id)
        assert len(academy_overview.programs) == 1
        assert academy_overview.programs[0].id == program.id
        assert len(academy_overview.players) == 1
        assert academy_overview.players[0].id == promoted_player.id
        assert academy_overview.players[0].status == AcademyPlayerStatus.PROMOTED
        assert len(academy_overview.graduation_events) == 1

        scouting_overview = scouting_2.get_overview(club_id)
        assert len(scouting_overview.assignments) == 1
        assert scouting_overview.assignments[0].id == assignment.id
        reloaded_prospect = scouting_2.get_prospect(club_id, prospect_id).prospect
        assert reloaded_prospect.pathway_stage == PlayerPathwayStage.ACADEMY_SIGNED
        assert reloaded_prospect.academy_player_id == promoted_player.id

        with session_factory() as session:
            assert session.scalar(select(ClubSponsorshipContract).where(ClubSponsorshipContract.id == contract.id))
            assert session.scalar(select(ClubSponsorshipPayout).where(ClubSponsorshipPayout.contract_id == contract.id))
            assert session.scalar(select(ClubSponsorshipAsset).where(ClubSponsorshipAsset.club_id == club_id))
            assert session.scalar(select(AcademyProgram).where(AcademyProgram.id == program.id))
            assert session.scalar(select(AcademyPlayer).where(AcademyPlayer.id == promoted_player.id))
            assert session.scalar(select(AcademyTrainingCycle).where(AcademyTrainingCycle.club_id == club_id))
            assert session.scalar(
                select(AcademyPlayerProgress).where(AcademyPlayerProgress.academy_player_id == promoted_player.id)
            )
            assert session.scalar(
                select(AcademyGraduationEvent).where(AcademyGraduationEvent.academy_player_id == promoted_player.id)
            )
            assert session.scalar(select(ScoutAssignment).where(ScoutAssignment.id == assignment.id))
            assert session.scalar(select(YouthProspect).where(YouthProspect.id == prospect_id))
            assert session.scalar(select(YouthProspectReport).where(YouthProspectReport.prospect_id == prospect_id))
            assert session.scalar(select(YouthPipelineSnapshot).where(YouthPipelineSnapshot.club_id == club_id))
    finally:
        engine.dispose()
