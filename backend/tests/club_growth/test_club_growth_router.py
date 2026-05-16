from __future__ import annotations

from collections.abc import Iterator
from datetime import timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.access_control.service import AccessControlService
from app.auth.dependencies import get_current_user, get_session
from app.club_growth.router import router as club_growth_router
from app.common.enums.sponsorship_asset_type import SponsorshipAssetType
from app.common.enums.sponsorship_status import SponsorshipStatus
from app.ingestion.models import Player, PlayerImageMetadata
from app.models.access_control import AccessAuditLog, Organization, OrganizationMembership
from app.models.base import Base, utcnow
from app.models.club_growth import (
    AcademyGenerationRun,
    AcademyProfile,
    AcademyPromotionHistory,
    AcademyProspect,
    AcademyRegenContractOffer,
    AcademyTrainingPlan,
    ClubGrowthAuditEvent,
    ClubStaffAssignment,
    ClubStaffContract,
    ClubStaffPerformanceLog,
    ClubStaffProfile,
)
from app.models.club_profile import ClubProfile
from app.models.club_sponsorship_asset import ClubSponsorshipAsset
from app.models.club_sponsorship_contract import ClubSponsorshipContract
from app.models.club_sponsorship_package import ClubSponsorshipPackage
from app.models.club_sponsorship_payout import ClubSponsorshipPayout
from app.models.player_token_market import PlayerShareMarket
from app.models.sponsorship_engine import SponsorshipLead
from app.models.user import KycStatus, User, UserRole


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
            Player.__table__,
            PlayerImageMetadata.__table__,
            PlayerShareMarket.__table__,
            ClubStaffProfile.__table__,
            ClubStaffContract.__table__,
            ClubStaffAssignment.__table__,
            ClubStaffPerformanceLog.__table__,
            AcademyProfile.__table__,
            AcademyProspect.__table__,
            AcademyTrainingPlan.__table__,
            AcademyRegenContractOffer.__table__,
            AcademyPromotionHistory.__table__,
            AcademyGenerationRun.__table__,
            ClubGrowthAuditEvent.__table__,
            ClubSponsorshipPackage.__table__,
            ClubSponsorshipContract.__table__,
            ClubSponsorshipAsset.__table__,
            ClubSponsorshipPayout.__table__,
            SponsorshipLead.__table__,
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
        id="club-owner",
        owner_user_id=owner_id,
        club_name="Launch FC",
        short_name="LFC",
        slug="launch-growth-fc",
        primary_color="#112233",
        secondary_color="#FFFFFF",
        accent_color="#FFD700",
        home_venue_name="Launch Park",
        country_code="NG",
    )
    session.add(club)
    session.flush()
    AccessControlService(session).ensure_club_organization(club, owner_user_id=owner_id)
    session.commit()
    return club


def _seed_sponsorship(session: Session, club: ClubProfile) -> None:
    package = ClubSponsorshipPackage(
        code="front-shirt",
        name="Front Shirt",
        asset_type=SponsorshipAssetType.JERSEY_FRONT,
        base_amount_minor=100000,
        currency="CREDITS",
        default_duration_months=2,
        payout_schedule="monthly",
        description="Primary shirt package",
    )
    session.add(package)
    session.flush()
    session.add(
        ClubSponsorshipContract(
            club_id=club.id,
            package_id=package.id,
            asset_type=SponsorshipAssetType.JERSEY_FRONT,
            sponsor_name="Launch Sponsor",
            status=SponsorshipStatus.ACTIVE,
            contract_amount_minor=100000,
            currency="CREDITS",
            duration_months=2,
            payout_schedule="monthly",
            start_at=utcnow(),
            end_at=utcnow() + timedelta(days=60),
            settled_amount_minor=25000,
            outstanding_amount_minor=75000,
        )
    )
    session.add(
        SponsorshipLead(
            club_id=club.id,
            requester_user_id="user-owner",
            sponsor_name="Queue Sponsor",
            asset_type=SponsorshipAssetType.CLUB_BANNER.value,
            status="submitted",
            proposal_note="Review me",
        )
    )
    session.commit()


def test_growth_dashboard_composes_staff_academy_and_sponsorship(client: TestClient, session: Session) -> None:
    club = _club(session)
    _seed_sponsorship(session, club)

    response = client.get(f"/api/clubs/{club.id}/growth")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["club_id"] == club.id
    assert payload["academy_profile"]["level"] == 1
    assert len(payload["staff_market"]) >= 3
    assert payload["sponsorship"]["active_contracts"] == 1
    assert payload["sponsorship"]["open_leads"] == 1


def test_staff_contract_flow_creates_assignment_and_audit(client: TestClient, session: Session) -> None:
    club = _club(session)
    staff_id = client.get(f"/api/clubs/{club.id}/growth").json()["staff_market"][0]["id"]

    offered = client.post(
        f"/api/clubs/{club.id}/growth/staff/{staff_id}/offer",
        json={"duration_days": 120, "role_scope": "club", "exclusive": True},
    )
    assert offered.status_code == 200, offered.text
    assert offered.json()["status"] == "offered"

    accepted = client.post(f"/api/clubs/{club.id}/growth/staff-contracts/{offered.json()['id']}/accept")
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == "active"

    assignment_count = session.scalar(select(ClubStaffAssignment).where(ClubStaffAssignment.club_id == club.id))
    assert assignment_count is not None
    audit_actions = list(session.scalars(select(ClubGrowthAuditEvent.action)).all())
    assert "staff_contract_offered" in audit_actions
    assert "staff_contract_accepted" in audit_actions


def test_academy_prospect_contract_and_promotion_flow(client: TestClient, session: Session) -> None:
    club = _club(session)

    generated = client.post(
        f"/api/clubs/{club.id}/growth/academy/generate-prospects",
        json={"count": 2, "seed": "stable-test"},
    )
    assert generated.status_code == 200, generated.text
    assert len(generated.json()) == 2
    prospect_id = generated.json()[0]["id"]
    assert generated.json()[0]["metadata"]["portrait_policy"] == "newgen_bank_only"

    offered = client.post(
        f"/api/clubs/{club.id}/growth/academy/prospects/{prospect_id}/offer-contract",
        json={"wage_minor": 1000, "duration_months": 18},
    )
    assert offered.status_code == 200, offered.text
    assert offered.json()["status"] == "offered"

    accepted = client.post(
        f"/api/clubs/{club.id}/growth/academy/contracts/{offered.json()['id']}/respond",
        json={"accepted": True, "reason": "ready"},
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == "accepted"

    promoted = client.post(f"/api/clubs/{club.id}/growth/academy/prospects/{prospect_id}/promote")
    assert promoted.status_code == 200, promoted.text
    assert promoted.json()["status"] == "promoted_to_senior"
    assert promoted.json()["portrait_asset_ref"]
    assert promoted.json()["senior_player_id"]
    history = session.scalar(select(AcademyPromotionHistory).where(AcademyPromotionHistory.prospect_id == prospect_id))
    assert history
    assert history.senior_player_id == promoted.json()["senior_player_id"]
    assert session.get(Player, promoted.json()["senior_player_id"]) is not None
    audit_actions = list(session.scalars(select(ClubGrowthAuditEvent.action)).all())
    assert "academy_prospects_generated" in audit_actions
    assert "academy_contract_offered" in audit_actions
    assert "academy_prospect_promoted" in audit_actions


def test_non_owner_is_blocked_from_growth_dashboard(client: TestClient, session: Session) -> None:
    club = _club(session)
    client.app.state.current_user_id = "user-other"

    response = client.get(f"/api/clubs/{club.id}/growth")

    assert response.status_code == 403, response.text
    assert response.json()["detail"] == "club_owner_required"
