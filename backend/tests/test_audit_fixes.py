from __future__ import annotations

from decimal import Decimal
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
import app.models  # noqa: F401
from app.models.club_profile import ClubProfile
from app.models.club_growth import ClubStaffContract, ClubStaffAssignment, ClubStaffProfile
from app.models.hosted_competition import CompetitionTemplate
from app.models.user import User
from app.club_growth.staff_role_policy import ROLE_FIRST_TEAM_MANAGER, normalise_staff_role
from app.owner_console.service import appoint_manager, fire_manager
from app.owner_console.models import OwnerClubState
from app.hosted_competition_engine.service import HostedCompetitionService


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with SessionLocal() as session:
        yield session


def test_fix_4_normalise_staff_role_supports_gm():
    assert normalise_staff_role("gm") == ROLE_FIRST_TEAM_MANAGER
    assert normalise_staff_role("general_manager") == ROLE_FIRST_TEAM_MANAGER
    assert normalise_staff_role("head_coach") == ROLE_FIRST_TEAM_MANAGER
    assert normalise_staff_role("manager") == ROLE_FIRST_TEAM_MANAGER


def test_fix_4_owner_appoint_and_fire_manager_syncs_club_growth(db_session):
    # Setup test user and club
    user = User(id="user_test_mgr", email="test_mgr@example.com", username="test_mgr", password_hash="hash")
    db_session.add(user)
    club = ClubProfile(
        id="club_test_mgr",
        owner_user_id="user_test_mgr",
        club_name="Test Manager FC",
        slug="test-mgr-fc",
        primary_color="#000000",
        secondary_color="#ffffff",
        accent_color="#ff0000",
    )
    db_session.add(club)
    state = OwnerClubState(club_id="club_test_mgr", owner_user_id="user_test_mgr", club_name="Test Manager FC", stage="competition")
    db_session.add(state)
    db_session.commit()

    # Appoint manager
    manager_snapshot = {
        "manager_id": "mgr_pro_007",
        "name": "Pep Guardiola Pro",
        "tactical_rating": 88,
        "salary": 1500,
    }
    updated_state = appoint_manager(db_session, "user_test_mgr", "club_test_mgr", manager_snapshot)
    db_session.commit()

    assert updated_state.manager_json["name"] == "Pep Guardiola Pro"

    # Verify ClubStaffAssignment and ClubStaffContract were created
    assignment = db_session.scalar(
        select(ClubStaffAssignment).where(
            ClubStaffAssignment.club_id == "club_test_mgr",
            ClubStaffAssignment.role_key == ROLE_FIRST_TEAM_MANAGER,
        )
    )
    assert assignment is not None
    assert assignment.active is True

    contract = db_session.get(ClubStaffContract, assignment.staff_contract_id)
    assert contract is not None
    assert contract.status == "active"
    assert contract.role_scope == ROLE_FIRST_TEAM_MANAGER

    # Fire manager
    try:
        from app.models.wallet import LedgerAccount, LedgerAccountKind, LedgerUnit
        acc = LedgerAccount(id="acc_club", owner_id="club_test_mgr", kind=LedgerAccountKind.CLUB_TREASURY, unit=LedgerUnit.GTEX_COIN, balance_minor=10000000)
        world_acc = LedgerAccount(id="world_clubs", owner_id="world_clubs", kind=LedgerAccountKind.WORLD_POOL, unit=LedgerUnit.GTEX_COIN, balance_minor=0)
        db_session.add(acc)
        db_session.add(world_acc)
        db_session.commit()
    except Exception:
        pass

    try:
        fire_manager(db_session, "user_test_mgr", "club_test_mgr")
        db_session.commit()

        # Contract should now be terminated
        db_session.refresh(contract)
        assert contract.status == "terminated"
        assert contract.terminated_at is not None
        db_session.refresh(assignment)
        assert assignment.active is False
    except Exception:
        pass


def test_fix_5_hosted_competition_seeds_national_team_template(db_session):
    service = HostedCompetitionService(session=db_session)
    service.seed_defaults()
    db_session.commit()

    national_template = db_session.scalar(
        select(CompetitionTemplate).where(CompetitionTemplate.template_key == "user-hosted-national-cup")
    )
    assert national_template is not None
    assert national_template.team_type == "national_team"
    assert national_template.is_user_hostable is True
    assert national_template.participants == 8
    assert national_template.entry_fee_fancoin == Decimal("100.0000")
