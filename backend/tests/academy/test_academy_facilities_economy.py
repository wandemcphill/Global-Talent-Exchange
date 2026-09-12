from __future__ import annotations

from datetime import date
from decimal import Decimal
import pytest
from sqlalchemy import select
from app.club_growth.schemas import AcademyGenerateProspectsRequest

from app.common.enums.academy_player_status import AcademyPlayerStatus
from app.ingestion.models import Player
from app.models.club_growth import AcademyProfile, AcademyProspect
from app.models.club_infra import ClubFacility
from app.models.club_profile import ClubProfile
from app.models.regen import RegenProfile
from app.models.user import User
from app.models.wallet import LedgerUnit
from app.regen_career.clock import RegenCareerClock, RegenRetirementInputs
from app.regen_career.retirement_academy_bridge import RegenRetirementAcademyBridge
from app.schemas.academy_core import AcademyPlayerView
from app.schemas.club_ops_requests import CreateAcademyPlayerRequest, UpdateAcademyPlayerRequest
from app.services.academy_facility_economy_service import (
    AcademyFacilityEconomyService,
    FacilityEconomyError,
    calculate_completion_seasons,
    calculate_upgrade_cost,
)
from app.services.academy_progression_service import AcademyProgressionService
from app.services.academy_service import AcademyService
from app.club_growth.service import ClubGrowthError, ClubGrowthService
from app.wallets.service import WalletService
from tests.regen_universe_support import build_regen_universe_session


def _seed_test_club_and_owner(session, prefix: str = "test-6e") -> tuple[ClubProfile, User]:
    from app.models.base import Base
    Base.metadata.create_all(session.get_bind())

    owner = User(
        id=f"{prefix}-user-id",
        email=f"{prefix}@example.com",
        username=f"{prefix}_user",
        password_hash="hash",  # pragma: allowlist secret
        full_name="Facility Owner",
    )
    session.add(owner)
    club = ClubProfile(
        id=f"{prefix}-club-id",
        owner_user_id=owner.id,
        club_name=f"{prefix.upper()} FC",
        short_name=prefix[:3].upper(),
        slug=f"{prefix}-club",
        primary_color="#127A6B",
        secondary_color="#FFFFFF",
        accent_color="#C49B2C",
        visibility="public",
    )
    session.add(club)

    wallet_service = WalletService()
    wallet_service.credit_trade_proceeds(
        session,
        user=owner,
        amount=Decimal("100000.0000"),
        reference=f"seed:{prefix}",
        description="Initial Fan Coin funding for testing",
        external_reference=f"ext-seed:{prefix}",
        unit=LedgerUnit.CREDIT,
    )
    session.commit()
    return club, owner


def test_facility_level_state_creation_and_persistence() -> None:
    session = build_regen_universe_session()
    try:
        club, _owner = _seed_test_club_and_owner(session, prefix="persist-fac")
        service = AcademyFacilityEconomyService(session)

        facility = service.ensure_facility(club.id)
        assert facility is not None
        assert facility.training_level == 1
        assert facility.academy_level == 1
        assert facility.medical_level == 1
        assert facility.branding_level == 1
        assert facility.youth_recruitment_level == 1
        assert facility.in_progress_upgrades_json == {}

        academy = service.ensure_academy_profile(club.id)
        assert academy is not None
        assert academy.level == 1
        assert academy.capacity_limit == 18
    finally:
        session.close()


def test_facility_progression_across_seasons() -> None:
    session = build_regen_universe_session()
    try:
        club, owner = _seed_test_club_and_owner(session, prefix="prog-season")
        service = AcademyFacilityEconomyService(session)

        cost = calculate_upgrade_cost("training", 2)
        assert cost == Decimal("1515.7000")
        duration = calculate_completion_seasons("training", 2)
        assert duration == 1

        result = service.start_facility_upgrade(
            actor=owner,
            club_id=club.id,
            facility_key="training",
            current_season_number=1,
        )
        assert result["in_progress"] is True
        assert result["target_season"] == 2

        facility = service.ensure_facility(club.id)
        assert facility.training_level == 1
        assert "training" in facility.in_progress_upgrades_json

        completed_season_1 = service.advance_season_facility_upgrades(
            club_id=club.id, current_season_number=1
        )
        assert completed_season_1 == []
        assert facility.training_level == 1

        completed_season_2 = service.advance_season_facility_upgrades(
            club_id=club.id, current_season_number=2
        )
        assert completed_season_2 == ["training"]
        assert facility.training_level == 2
        assert "training" not in facility.in_progress_upgrades_json
    finally:
        session.close()


def test_academy_quality_and_capacity_calculations() -> None:
    session = build_regen_universe_session()
    try:
        club, _owner = _seed_test_club_and_owner(session, prefix="qual-cap")
        service = AcademyFacilityEconomyService(session)

        capacity_1, quality_1 = service.get_academy_capacity_and_quality(club.id)
        assert capacity_1 == 18
        assert quality_1 == 45

        facility = service.ensure_facility(club.id)
        facility.academy_level = 3
        facility.training_level = 3
        facility.youth_recruitment_level = 2
        facility.medical_level = 2
        session.flush()

        capacity_2, quality_2 = service.get_academy_capacity_and_quality(club.id)
        assert capacity_2 == 31
        assert quality_2 == 100
    finally:
        session.close()


def test_development_effects_are_deterministic() -> None:
    progression_service = AcademyProgressionService()
    from datetime import datetime, timezone
    player = AcademyPlayerView(
        id="acpl-test-dev",
        club_id="club-1",
        display_name="Test Dev Prospect",
        age=16,
        primary_position="CM",
        secondary_position=None,
        status=AcademyPlayerStatus.ENROLLED,
        overall_rating=55,
        readiness_score=60,
        completed_cycles=1,
        development_attributes={"technical": 55, "tactical": 54, "physical": 56, "mentality": 55},
        last_progressed_at=datetime.now(timezone.utc),
        pathway_note=None,
    )

    request = UpdateAcademyPlayerRequest(attendance_score=80, coach_assessment=75, completed_cycles_delta=1)

    result_low_fac = progression_service.apply_progress(
        player=player.model_copy(deep=True),
        payload=request,
        training_cycle_id="cycle-1",
        facility_training_level=1,
        facility_medical_level=1,
    )

    result_high_fac = progression_service.apply_progress(
        player=player.model_copy(deep=True),
        payload=request,
        training_cycle_id="cycle-1",
        facility_training_level=6,
        facility_medical_level=6,
    )

    assert result_high_fac.delta_overall > result_low_fac.delta_overall


def test_academy_state_affects_generation_pipeline_and_enforces_capacity() -> None:
    session = build_regen_universe_session()
    try:
        club, owner = _seed_test_club_and_owner(session, prefix="gen-pipe")
        facility_service = AcademyFacilityEconomyService(session)
        growth_service = ClubGrowthService(session)

        facility = facility_service.ensure_facility(club.id)
        facility.academy_level = 1
        facility.youth_recruitment_level = 1
        session.flush()

        capacity, _quality = facility_service.get_academy_capacity_and_quality(club.id)
        assert capacity == 18

        for batch_index in range(3):
            growth_service.generate_prospects(
                actor=owner,
                club_id=club.id,
                payload=AcademyGenerateProspectsRequest(count=6, seed=f"batch-{batch_index}"),
            )

        with pytest.raises(ClubGrowthError, match="capacity limit reached"):
            growth_service.generate_prospects(
                actor=owner,
                club_id=club.id,
                payload=AcademyGenerateProspectsRequest(count=1, seed="overflow"),
            )
    finally:
        session.close()


def test_retirement_legacy_planning_consumes_academy_context() -> None:
    session = build_regen_universe_session()
    monkeypatch_env = pytest.MonkeyPatch()
    try:
        club, owner = _seed_test_club_and_owner(session, prefix="ret-leg")
        facility_service = AcademyFacilityEconomyService(session)
        facility = facility_service.ensure_facility(club.id)
        facility.academy_level = 4
        facility.training_level = 4
        session.flush()

        bridge = RegenRetirementAcademyBridge(session)
        monkeypatch_env.setenv("GTE_REGEN_LEGACY_INTAKE_ENABLED", "1")

        state = {
            "legacy_intake_plan": {
                "trigger_key": "legacy-trigger-test-001",
                "club_id": club.id,
                "retiring_regen_id": "RGN-RET-01",
                "retiring_player_id": "PLR-RET-01",
                "successor_count": 2,
                "successor_quality_floor_gsi": 65,
                "generation_status": "pending",
            }
        }

        result = bridge.consume(state=state)
        assert result is not None
        assert result.status == "completed"
        assert len(result.prospect_ids) == 2

        prospects = list(session.scalars(
            select(AcademyProspect).where(AcademyProspect.id.in_(result.prospect_ids))
        ).all())
        for prospect in prospects:
            assert prospect.current_ability >= 65
            assert prospect.metadata_json.get("facility_quality_score") is not None
            assert prospect.metadata_json.get("legacy_generation") is True
    finally:
        monkeypatch_env.undo()
        session.close()


def test_no_wall_clock_fallback_introduced() -> None:
    clock = RegenCareerClock()
    inputs = RegenRetirementInputs(
        virtual_age_months=None,
        position="midfielder",
        injury_burden=0.8,
        playing_time=0.2,
    )
    assessment = clock.assess(inputs)
    assert assessment.virtual_age_months is None
    assert assessment.eligible_for_retirement_decision is False
    assert assessment.expected_longevity_months is None


def test_system_a_ownership_and_share_market_invariants() -> None:
    session = build_regen_universe_session()
    try:
        club, _owner = _seed_test_club_and_owner(session, prefix="system-a-inv")
        real_player = Player(
            id="real-player-p6e",
            source_provider="sportmonks",
            provider_external_id="ext-real-p6e",
            full_name="Real Player Invariant",
            position="ST",
            is_tradable=True,
            is_real_player=True,
        )
        session.add(real_player)
        session.flush()

        facility_service = AcademyFacilityEconomyService(session)
        facility_service.ensure_facility(club.id)

        assert real_player.is_real_player is True
        assert real_player.is_tradable is True
    finally:
        session.close()
