from datetime import date, datetime
from decimal import Decimal
from unittest.mock import patch
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.ingestion.models import Player
from app.models.base import Base
from app.models.club_profile import ClubProfile
from app.models.regen import RegenGenerationEvent, RegenProfile
from app.models.user import KycStatus, User, UserRole
from app.regen_universe.models import RegenSeason
from app.services.player_lifecycle_service import PlayerLifecycleService
from app.schemas.player_lifecycle import ContractCreateRequest


@pytest.fixture()
def session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def lifecycle_service(session: Session) -> PlayerLifecycleService:
    return PlayerLifecycleService(session)


def seed_test_regen(session: Session, *, player_id: str = "player-p6") -> RegenProfile:
    user = User(
        id="user-owner-p6",
        email="owner-p6@example.com",
        username="owner_p6",
        display_name="Owner P6",
        password_hash="x",  # pragma: allowlist secret
        role=UserRole.USER,
        kyc_status=KycStatus.FULLY_VERIFIED,
    )
    club = ClubProfile(
        id="club-p6",
        owner_user_id=user.id,
        club_name="P6 FC",
        short_name="P6",
        slug="p6-fc",
        primary_color="#000000",
        secondary_color="#ffffff",
        accent_color="#ff0000",
        country_code="NG",
        region_name="Lagos",
        city_name="Lagos",
    )
    player = Player(
        id=player_id,
        source_provider="test",
        provider_external_id=player_id,
        current_club_profile_id=club.id,
        full_name="Policy Test Regen",
        normalized_position="forward",
        is_tradable=True,
    )
    regen = RegenProfile(
        id=f"regen-db-{player_id}",
        regen_id=f"regen-{player_id}",
        player_id=player_id,
        linked_unique_card_id=f"card-{player_id}",
        generated_for_club_id=club.id,
        birth_country_code="NG",
        primary_position="ST",
        generated_at=datetime(2020, 1, 1, 12, 0),
        current_gsi=65,
        scout_confidence="High",
        generation_source="new_club",
        status="active",
        metadata_json={
            "career_state": {
                "contract_currency": "FanCoin",
                "transfer_listed": False,
                "free_agent": False,
                "retired": False,
            }
        },
    )
    season1 = RegenSeason(
        id="season-1",
        season_number=1,
        start_date=date(2020, 1, 1),
        end_date=date(2020, 12, 31),
        is_active=False,
        metadata_json={"virtual_age_month_index": 204},
    )
    season2 = RegenSeason(
        id="season-2",
        season_number=2,
        start_date=date(2021, 1, 1),
        end_date=date(2021, 12, 31),
        is_active=True,
        metadata_json={"virtual_age_month_index": 216},
    )
    gen_event = RegenGenerationEvent(
        id="gen-event-1",
        regen_profile_id=regen.id,
        club_id=club.id,
        generation_source="new_club",
        season_label="Season 1",
        metadata_json={"season_number": 1},
    )
    session.add_all([user, club, player, regen, season1, season2, gen_event])
    session.commit()
    return regen


def test_policy_assessment_controls_retirement_when_eligible(
    session: Session,
    lifecycle_service: PlayerLifecycleService,
) -> None:
    regen = seed_test_regen(session, player_id="p-eligible")
    contract = lifecycle_service.create_contract(
        "p-eligible",
        ContractCreateRequest(
            club_id="club-p6",
            wage_amount=Decimal("50000.00"),
            signed_on=date(2021, 1, 1),
            starts_on=date(2021, 1, 1),
            ends_on=date(2022, 1, 1),
        ),
    )

    from app.regen_career.clock import RegenCareerAssessment, RetirementPressureBand
    from app.regen_career.policy_service import RegenCareerPolicyContext

    mock_assessment = RegenCareerAssessment(
        virtual_age_months=476,
        career_stage="late_career",
        retirement_pressure=0.95,
        pressure_band=RetirementPressureBand.DECISION,
        expected_longevity_months=476,
        should_enter_retirement_watch=True,
        eligible_for_retirement_decision=True,
        drivers=("virtual_age",),
    )
    mock_policy_ctx = RegenCareerPolicyContext(
        player_id="p-eligible",
        regen_id=regen.regen_id,
        generation_season_number=1,
        current_season_number=2,
        position="forward",
        personality={},
        current_contract_id=contract.id,
        active_injury_count=0,
        assessment=mock_assessment,
    )

    with patch("app.regen_career.policy_service.RegenCareerPolicyService.assess", return_value=mock_policy_ctx):
        summary = lifecycle_service.get_regen_summary("p-eligible", on_date=date(2021, 6, 1))

    assert summary is not None
    assert summary.retired is True
    assert summary.lifecycle_phase == "retired"
    player = session.get(Player, "p-eligible")
    assert player is not None
    assert player.is_tradable is False
    assert player.current_club_profile_id is None
    session.refresh(contract)
    assert contract.status == "terminated"


def test_policy_not_eligible_does_not_retire(
    session: Session,
    lifecycle_service: PlayerLifecycleService,
) -> None:
    seed_test_regen(session, player_id="p-not-eligible")
    lifecycle_service.create_contract(
        "p-not-eligible",
        ContractCreateRequest(
            club_id="club-p6",
            wage_amount=Decimal("50000.00"),
            signed_on=date(2021, 1, 1),
            starts_on=date(2021, 1, 1),
            ends_on=date(2022, 1, 1),
        ),
    )

    summary = lifecycle_service.get_regen_summary("p-not-eligible", on_date=date(2021, 6, 1))

    assert summary is not None
    assert summary.retired is False
    assert summary.lifecycle_phase != "retired"
    player = session.get(Player, "p-not-eligible")
    assert player is not None
    assert player.is_tradable is True


def test_virtual_age_unavailable_prevents_retirement(
    session: Session,
    lifecycle_service: PlayerLifecycleService,
) -> None:
    regen = seed_test_regen(session, player_id="p-no-mapping")
    lifecycle_service.create_contract(
        "p-no-mapping",
        ContractCreateRequest(
            club_id="club-p6",
            wage_amount=Decimal("50000.00"),
            signed_on=date(2021, 1, 1),
            starts_on=date(2021, 1, 1),
            ends_on=date(2022, 1, 1),
        ),
    )

    for season_obj in session.scalars(select(RegenSeason)).all():
        season_obj.metadata_json = {}
    session.commit()

    summary = lifecycle_service.get_regen_summary("p-no-mapping", on_date=date(2021, 6, 1))

    assert summary is not None
    assert summary.retired is False
    assert summary.lifecycle_age_months is None
    regen_updated = session.get(RegenProfile, regen.id)
    assert regen_updated is not None
    career_state = (regen_updated.metadata_json or {}).get("career_state", {})
    assert career_state.get("retirement_policy_status") == "age_unknown"


def test_retirement_remains_idempotent(
    session: Session,
    lifecycle_service: PlayerLifecycleService,
) -> None:
    regen = seed_test_regen(session, player_id="p-idempotent")
    contract = lifecycle_service.create_contract(
        "p-idempotent",
        ContractCreateRequest(
            club_id="club-p6",
            wage_amount=Decimal("50000.00"),
            signed_on=date(2021, 1, 1),
            starts_on=date(2021, 1, 1),
            ends_on=date(2022, 1, 1),
        ),
    )

    from app.regen_career.clock import RegenCareerAssessment, RetirementPressureBand
    from app.regen_career.policy_service import RegenCareerPolicyContext

    mock_assessment = RegenCareerAssessment(
        virtual_age_months=476,
        career_stage="late_career",
        retirement_pressure=0.95,
        pressure_band=RetirementPressureBand.DECISION,
        expected_longevity_months=476,
        should_enter_retirement_watch=True,
        eligible_for_retirement_decision=True,
        drivers=("virtual_age",),
    )
    mock_policy_ctx = RegenCareerPolicyContext(
        player_id="p-idempotent",
        regen_id=regen.regen_id,
        generation_season_number=1,
        current_season_number=2,
        position="forward",
        personality={},
        current_contract_id=contract.id,
        active_injury_count=0,
        assessment=mock_assessment,
    )

    with patch("app.regen_career.policy_service.RegenCareerPolicyService.assess", return_value=mock_policy_ctx):
        first_summary = lifecycle_service.get_regen_summary("p-idempotent", on_date=date(2021, 6, 1))
        events_after_first = lifecycle_service.list_events("p-idempotent", limit=50)
        retirement_events_first = [e for e in events_after_first if e.event_type == "regen_retired"]

        second_summary = lifecycle_service.get_regen_summary("p-idempotent", on_date=date(2021, 6, 2))
        events_after_second = lifecycle_service.list_events("p-idempotent", limit=50)
        retirement_events_second = [e for e in events_after_second if e.event_type == "regen_retired"]

    assert first_summary.retired is True
    assert second_summary.retired is True
    assert len(retirement_events_first) == 1
    assert len(retirement_events_second) == 1


def test_non_retirement_lifecycle_behaviour_remains_intact(
    session: Session,
    lifecycle_service: PlayerLifecycleService,
) -> None:
    seed_test_regen(session, player_id="p-intact")
    summary_before = lifecycle_service.get_regen_summary("p-intact", on_date=date(2021, 6, 1))
    assert summary_before is not None
    assert summary_before.free_agent is True

    lifecycle_service.create_contract(
        "p-intact",
        ContractCreateRequest(
            club_id="club-p6",
            wage_amount=Decimal("50000.00"),
            signed_on=date(2021, 6, 1),
            starts_on=date(2021, 6, 1),
            ends_on=date(2022, 6, 1),
        ),
    )

    summary_after = lifecycle_service.get_regen_summary("p-intact", on_date=date(2021, 6, 2))
    assert summary_after is not None
    assert summary_after.free_agent is False
    assert summary_after.retired is False
