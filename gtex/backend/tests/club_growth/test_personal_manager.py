from __future__ import annotations

from collections.abc import Iterator
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.access_control.service import AccessControlService
from app.auth.dependencies import get_current_user, get_session
from app.club_growth.personal_manager_policy import PersonalManagerBand
from app.club_growth.router import router as club_growth_router
from app.club_growth.schemas import PersonalManagerCreateRequest
from app.club_growth.service import ClubGrowthService
from app.models.base import Base
from app.models.club_growth import (
    ClubStaffAssignment,
    ClubStaffContract,
    ClubStaffProfile,
    PersonalManager,
)
from app.models.club_profile import ClubProfile
from app.models.player_agency_state import PlayerAgencyState
from app.models.player_personality import PlayerPersonality
from app.models.regen import RegenProfile
from app.models.user import KycStatus, User, UserRole
from app.models.wallet import LedgerSourceTag, LedgerTransaction, LedgerUnit
from app.services.player_agency_context_service import PlayerAgencyContextService
from app.ingestion.models import Player


@pytest.fixture()
def session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with session_local() as db_session:
        user_owner = User(
            id="user-owner",
            email="owner@example.com",
            username="owner",
            display_name="Owner User",
            password_hash="x",
            role=UserRole.USER,
            kyc_status=KycStatus.FULLY_VERIFIED,
        )
        user_other = User(
            id="user-other",
            email="other@example.com",
            username="other",
            display_name="Other User",
            password_hash="x",
            role=UserRole.USER,
            kyc_status=KycStatus.FULLY_VERIFIED,
        )
        db_session.add_all([user_owner, user_other])
        db_session.flush()

        from app.wallets.service import WalletService

        wallet = WalletService()
        wallet.credit_trade_proceeds(
            db_session,
            user=user_owner,
            amount=Decimal("10000"),
            reference="seed-owner",
            description="seed owner balance",
            external_reference="seed-owner-ext",
            unit=LedgerUnit.CREDIT,
        )
        wallet.credit_trade_proceeds(
            db_session,
            user=user_other,
            amount=Decimal("10000"),
            reference="seed-other",
            description="seed other balance",
            external_reference="seed-other-ext",
            unit=LedgerUnit.CREDIT,
        )
        db_session.commit()
        yield db_session
    engine.dispose()


@pytest.fixture()
def client(session: Session) -> Iterator[TestClient]:
    app = FastAPI()
    app.include_router(club_growth_router, prefix="/api")
    app.state.current_user_id = "user-owner"

    def override_session() -> Iterator[Session]:
        yield session

    def override_current_user() -> User:
        user = session.get(User, app.state.current_user_id)
        assert user is not None
        return user

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_user] = override_current_user
    with TestClient(app) as test_client:
        yield test_client


def _club(session: Session, *, owner_id: str = "user-owner") -> ClubProfile:
    club = ClubProfile(
        id=f"club-{owner_id}",
        owner_user_id=owner_id,
        club_name="Tactical FC",
        short_name="TFC",
        slug=f"tactical-fc-{owner_id}",
        primary_color="#112233",
        secondary_color="#FFFFFF",
        accent_color="#FFD700",
        home_venue_name="Tactical Arena",
        country_code="NG",
    )
    session.add(club)
    session.flush()
    AccessControlService(session).ensure_club_organization(club, owner_user_id=owner_id)
    session.commit()
    return club


def test_create_personal_manager_success(client: TestClient, session: Session) -> None:
    response = client.post(
        "/api/clubs/personal-manager",
        json={
            "display_name": "Boss Pep",
            "quality_band": 4,  # BAND_91_95
            "fan_coin_price": 2500,  # client value is ignored; server policy supplies 1000
            "tactical_identity": {
                "formation": "4-3-3",
                "mentality": "attacking",
                "playing_style": "tiki-taka",
            },
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["user_id"] == "user-owner"
    assert payload["display_name"] == "Boss Pep"
    assert payload["quality_band"] == "BAND_91_95"
    assert payload["gsi_min"] == 91
    assert payload["gsi_max"] == 95
    assert payload["gsi_rating"] == 93
    assert payload["fan_coin_price"] == 1000
    assert payload["permanent"] is True
    assert payload["transferable"] is False
    assert payload["salary_bearing"] is False
    assert payload["tactical_identity"]["formation"] == "4-3-3"

    manager_in_db = session.scalar(select(PersonalManager).where(PersonalManager.user_id == "user-owner"))
    assert manager_in_db is not None
    assert manager_in_db.permanent is True
    assert manager_in_db.transferable is False
    assert manager_in_db.salary_bearing is False

    transaction = session.scalar(
        select(LedgerTransaction).where(
            LedgerTransaction.reference == "personal-manager:create:user-owner"
        )
    )
    assert transaction is not None
    assert transaction.source_tag == LedgerSourceTag.PERSONAL_MANAGER_CREATION_SPEND


def test_duplicate_creation_rejected(client: TestClient, session: Session) -> None:
    first = client.post(
        "/api/clubs/personal-manager",
        json={
            "display_name": "Boss One",
            "quality_band": 1,
            "fan_coin_price": 500,
            "tactical_identity": {"formation": "4-4-2"},
        },
    )
    assert first.status_code == 200, first.text

    second = client.post(
        "/api/clubs/personal-manager",
        json={
            "display_name": "Boss Two",
            "quality_band": 2,
            "fan_coin_price": 1000,
            "tactical_identity": {"formation": "3-5-2"},
        },
    )
    assert second.status_code == 409, second.text
    assert "personal_manager_already_exists" in second.json()["detail"]


def test_quality_band_validation_and_bounds(client: TestClient) -> None:
    invalid_price = client.post(
        "/api/clubs/personal-manager",
        json={
            "display_name": "Invalid Price Boss",
            "quality_band": 2,
            "fan_coin_price": 0,
            "tactical_identity": {},
        },
    )
    assert invalid_price.status_code == 422

    invalid_band = client.post(
        "/api/clubs/personal-manager",
        json={
            "display_name": "Invalid Band Boss",
            "quality_band": 99,
            "fan_coin_price": 500,
            "tactical_identity": {},
        },
    )
    assert invalid_band.status_code == 422


def test_immutable_quality_and_invariants(session: Session) -> None:
    user = session.get(User, "user-owner")
    assert user is not None
    service = ClubGrowthService(session)
    view = service.create_personal_manager(
        actor=user,
        payload=PersonalManagerCreateRequest(
            display_name="Immutable Boss",
            quality_band=3,  # BAND_81_90
            fan_coin_price=1500,
            tactical_identity={"style": "counter-attack"},
        ),
    )
    session.commit()

    manager = session.get(PersonalManager, view.id)
    assert manager is not None
    assert manager.quality_band == "BAND_81_90"
    assert manager.gsi_min == 81
    assert manager.gsi_max == 90
    assert manager.permanent is True
    assert manager.transferable is False
    assert manager.salary_bearing is False


def test_unique_constraint_at_database_level(session: Session) -> None:
    pm1 = PersonalManager(
        user_id="user-owner",
        display_name="DB Boss 1",
        quality_band="BAND_60_70",
        gsi_min=60,
        gsi_max=70,
        gsi_rating=65,
        fan_coin_price=500,
        permanent=True,
        transferable=False,
        salary_bearing=False,
    )
    pm2 = PersonalManager(
        user_id="user-owner",
        display_name="DB Boss 2",
        quality_band="BAND_71_80",
        gsi_min=71,
        gsi_max=80,
        gsi_rating=75,
        fan_coin_price=1000,
        permanent=True,
        transferable=False,
        salary_bearing=False,
    )
    session.add(pm1)
    session.commit()

    session.add(pm2)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_self_lookup_me(client: TestClient) -> None:
    not_found = client.get("/api/clubs/personal-manager/me")
    assert not_found.status_code == 404

    client.post(
        "/api/clubs/personal-manager",
        json={
            "display_name": "My Boss",
            "quality_band": 2,
            "fan_coin_price": 800,
            "tactical_identity": {"formation": "4-2-3-1"},
        },
    )

    found = client.get("/api/clubs/personal-manager/me")
    assert found.status_code == 200
    assert found.json()["display_name"] == "My Boss"


def test_appoint_personal_manager_succeeds(client: TestClient, session: Session) -> None:
    club = _club(session, owner_id="user-owner")

    client.post(
        "/api/clubs/personal-manager",
        json={
            "display_name": "Appointed Boss",
            "quality_band": 3,
            "fan_coin_price": 1200,
            "tactical_identity": {"possession": True},
        },
    )

    appoint = client.post(f"/api/clubs/{club.id}/growth/personal-manager/appoint")
    assert appoint.status_code == 200, appoint.text
    contract_data = appoint.json()
    assert contract_data["status"] == "active"
    assert contract_data["salary_minor"] == 0
    assert contract_data["role_scope"] == "first_team_manager"

    staff_profile = session.scalar(
        select(ClubStaffProfile).where(ClubStaffProfile.market_key == "personal-manager:user-owner")
    )
    assert staff_profile is not None
    assert staff_profile.salary_minor == 0
    assert staff_profile.staff_type == "personal_manager"

    contract = session.scalar(
        select(ClubStaffContract).where(
            ClubStaffContract.club_id == club.id,
            ClubStaffContract.staff_profile_id == staff_profile.id,
        )
    )
    assert contract is not None
    assert contract.salary_minor == 0
    assert contract.status == "active"

    assignment = session.scalar(
        select(ClubStaffAssignment).where(
            ClubStaffAssignment.club_id == club.id,
            ClubStaffAssignment.role_key == "first_team_manager",
        )
    )
    assert assignment is not None
    assert assignment.staff_contract_id == contract.id


def test_non_owner_blocked_from_appointing(client: TestClient, session: Session) -> None:
    club = _club(session, owner_id="user-owner")
    client.app.state.current_user_id = "user-other"

    appoint = client.post(f"/api/clubs/{club.id}/growth/personal-manager/appoint")
    assert appoint.status_code == 403
    assert appoint.json()["detail"] == "club_owner_required"


def test_player_agency_context_manager_and_unknown_virtual_age(session: Session) -> None:
    owner = session.get(User, "user-owner")
    assert owner is not None
    club = _club(session, owner_id="user-owner")

    ClubGrowthService(session).create_personal_manager(
        actor=owner,
        payload=PersonalManagerCreateRequest(
            display_name="Context Boss",
            quality_band=4,
            fan_coin_price=2000,
            tactical_identity={"gsi": 92},
        ),
    )
    session.commit()

    player = Player(
        id="player-agency-1",
        source_provider="gtex_test",
        provider_external_id="ext-agency-1",
        full_name="Regen Prospect",
        position="CM",
        normalized_position="CM",
        is_tradable=True,
        is_real_player=False,
    )
    regen = RegenProfile(
        id="regen-agency-1",
        player_id="player-agency-1",
        regen_id="R-001",
        linked_unique_card_id="card-agency-1",
        birth_country_code="NG",
        primary_position="CM",
        scout_confidence=0.8,
        generation_source="test",
        current_gsi=70,
        generated_for_club_id=club.id,
        metadata_json={
            "career_state": {
                "virtual_age_months": None,
                "retirement_policy_status": "age_unknown",
                "career_stage": "age_unknown",
            }
        },
    )
    personality = PlayerPersonality(
        player_id="player-agency-1",
        regen_profile_id="regen-agency-1",
        ambition=50,
        loyalty=50,
        professionalism=50,
    )
    state = PlayerAgencyState(
        player_id="player-agency-1",
        current_club_id=club.id,
    )
    session.add_all([player, regen, personality, state])
    session.commit()

    context_service = PlayerAgencyContextService(session)

    club_ctx = context_service.build_club_context(
        player=player,
        regen=regen,
        club_id=club.id,
        reference_on=session.get(User, "user-owner").created_at.date(),
    )
    assert club_ctx.has_personal_manager is True
    assert club_ctx.manager_name == "Context Boss"

    career_stage = context_service.infer_career_stage(
        player=player,
        regen=regen,
        personality=personality,
        reference_on=session.get(User, "user-owner").created_at.date(),
    )
    assert career_stage == "age_unknown"
