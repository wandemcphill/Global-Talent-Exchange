from __future__ import annotations

from collections.abc import Iterator
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import create_engine

from app.access_control.service import AccessControlService
from app.auth.dependencies import get_current_admin, get_current_user, get_session
from app.club_lifecycle.router import router as club_lifecycle_router
from app.ingestion.models import Player
from app.models.access_control import AccessAuditLog, Organization, OrganizationMembership
from app.models.base import Base
from app.models.club_jersey_design import ClubJerseyDesign
from app.models.club_lifecycle import (
    ClubLifecycleAuditEvent,
    ClubLifecycleState,
    ClubOperatingStatus,
    ClubReadinessStatus,
    ClubRegistrationSlot,
    ClubSquadRegistration,
    ClubEligibilityFlag,
)
from app.models.club_profile import ClubProfile
from app.models.player_token_market import PlayerShareMarket
from app.models.user import KycStatus, User, UserRole
from app.models.wallet import (
    LedgerAccount,
    LedgerAccountKind,
    LedgerBalanceProjection,
    LedgerTransaction,
    LedgerUnit,
)


@pytest.fixture()
def session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            ClubProfile.__table__,
            Organization.__table__,
            OrganizationMembership.__table__,
            AccessAuditLog.__table__,
            ClubJerseyDesign.__table__,
            Player.__table__,
            PlayerShareMarket.__table__,
            LedgerAccount.__table__,
            LedgerTransaction.__table__,
            LedgerBalanceProjection.__table__,
            ClubLifecycleState.__table__,
            ClubReadinessStatus.__table__,
            ClubSquadRegistration.__table__,
            ClubRegistrationSlot.__table__,
            ClubEligibilityFlag.__table__,
            ClubOperatingStatus.__table__,
            ClubLifecycleAuditEvent.__table__,
        ],
    )
    session_local = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with session_local() as db_session:
        db_session.add_all(
            [
                User(
                    id="user-owner",
                    email="owner@example.com",
                    username="owner",
                    display_name="Owner",
                    password_hash="x",
                    role=UserRole.USER,
                    kyc_status=KycStatus.FULLY_VERIFIED,
                ),
                User(
                    id="user-admin",
                    email="admin@example.com",
                    username="admin",
                    display_name="Admin",
                    password_hash="x",
                    role=UserRole.ADMIN,
                    kyc_status=KycStatus.FULLY_VERIFIED,
                ),
                User(
                    id="user-other",
                    email="other@example.com",
                    username="other",
                    display_name="Other",
                    password_hash="x",
                    role=UserRole.USER,
                    kyc_status=KycStatus.FULLY_VERIFIED,
                ),
            ]
        )
        db_session.commit()
        yield db_session
    engine.dispose()


@pytest.fixture()
def client(session: Session) -> Iterator[TestClient]:
    app = FastAPI()
    app.include_router(club_lifecycle_router, prefix="/api")
    app.state.current_user_id = "user-owner"
    app.state.current_admin_id = "user-admin"

    def override_session() -> Iterator[Session]:
        yield session

    def override_current_user() -> User:
        user = session.get(User, app.state.current_user_id)
        assert user is not None
        return user

    def override_current_admin() -> User:
        user = session.get(User, app.state.current_admin_id)
        assert user is not None
        return user

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_current_admin] = override_current_admin
    with TestClient(app) as test_client:
        yield test_client


def _club(session: Session, *, owner_id: str = "user-owner") -> ClubProfile:
    club = ClubProfile(
        id="club-owner",
        owner_user_id=owner_id,
        club_name="Launch FC",
        short_name="LFC",
        slug="launch-fc",
        primary_color="#112233",
        secondary_color="#FFFFFF",
        accent_color="#FFD700",
        home_venue_name="Launch Park",
    )
    session.add(club)
    session.flush()
    AccessControlService(session).ensure_club_organization(club, owner_user_id=owner_id)
    session.commit()
    return club


def _seed_identity(session: Session, club: ClubProfile) -> None:
    session.add(
        ClubJerseyDesign(
            club_id=club.id,
            name="Home",
            slot_type="home",
            base_template_id="classic",
            primary_color="#112233",
            secondary_color="#FFFFFF",
            trim_color="#FFD700",
        )
    )
    session.commit()


def _seed_wallet(session: Session, *, owner_id: str = "user-owner") -> None:
    account = LedgerAccount(
        id="wallet-owner-coin",
        owner_user_id=owner_id,
        code=f"{owner_id}:coin:user",
        label="Owner Coin Wallet",
        unit=LedgerUnit.COIN,
        kind=LedgerAccountKind.USER,
    )
    session.add(account)
    session.flush()
    session.add(
        LedgerBalanceProjection(
            account_id=account.id,
            owner_user_id=owner_id,
            unit=LedgerUnit.COIN,
            balance=Decimal("250.0000"),
        )
    )
    session.commit()


def _seed_players(session: Session, club: ClubProfile, positions: list[str]) -> list[str]:
    player_ids: list[str] = []
    for index, position in enumerate(positions, start=1):
        player = Player(
            source_provider="fixture",
            provider_external_id=f"launch-fc-{index}",
            full_name=f"Launch Player {index}",
            canonical_display_name=f"Launch Player {index}",
            position=position,
            normalized_position=position,
            current_club_profile_id=club.id,
        )
        session.add(player)
        session.flush()
        player_ids.append(player.id)
    session.commit()
    return player_ids


def test_readiness_registration_and_lifecycle_flow(client: TestClient, session: Session) -> None:
    club = _club(session)

    early = client.get(f"/api/clubs/{club.id}/readiness")
    assert early.status_code == 200, early.text
    assert early.json()["recommended_state"] == "identity_pending"
    assert "wallet_funded" in early.json()["blockers"]

    _seed_identity(session, club)
    _seed_wallet(session)
    positions = ["GK", "CB", "RB", "LB", "CB", "CM", "CDM", "CAM", "ST", "LW", "RW"]
    _seed_players(session, club, positions)

    registration = client.post(f"/api/clubs/{club.id}/squad-registration", json={"season_label": "launch"})
    assert registration.status_code == 200, registration.text
    assert registration.json()["status"] == "draft"
    assert len(registration.json()["players"]) == 11

    submitted = client.post(f"/api/clubs/{club.id}/squad-registration/submit")
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["status"] == "submitted"

    locked = client.post(f"/api/clubs/{club.id}/squad-registration/lock")
    assert locked.status_code == 200, locked.text
    assert locked.json()["status"] == "locked"

    advanced = client.post(
        f"/api/clubs/{club.id}/advance-lifecycle",
        json={"target_state": "competition_ready", "reason": "Launch checklist complete"},
    )
    assert advanced.status_code == 200, advanced.text
    assert advanced.json()["state"] == "competition_ready"
    assert advanced.json()["readiness"]["competition_eligible"] is True

    audit_actions = list(session.scalars(select(ClubLifecycleAuditEvent.action)).all())
    assert "squad_registration_upserted" in audit_actions
    assert "squad_registration_submitted" in audit_actions
    assert "squad_registration_locked" in audit_actions
    assert "lifecycle_advanced" in audit_actions


def test_squad_registration_rejects_incomplete_squad(client: TestClient, session: Session) -> None:
    club = _club(session)
    _seed_identity(session, club)
    _seed_wallet(session)
    _seed_players(session, club, ["GK", "CB", "RB", "CM", "ST"])

    registration = client.post(f"/api/clubs/{club.id}/squad-registration", json={"season_label": "launch"})
    assert registration.status_code == 200, registration.text

    submitted = client.post(f"/api/clubs/{club.id}/squad-registration/submit")
    assert submitted.status_code == 400, submitted.text
    assert submitted.json()["detail"] == "minimum_squad_size_not_met"


def test_non_owner_is_blocked_from_club_lifecycle(client: TestClient, session: Session) -> None:
    club = _club(session)
    client.app.state.current_user_id = "user-other"

    response = client.get(f"/api/clubs/{club.id}/readiness")

    assert response.status_code == 403, response.text
    assert response.json()["detail"] == "club_owner_required"
