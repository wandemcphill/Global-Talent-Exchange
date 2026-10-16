from __future__ import annotations

from collections.abc import Iterator

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_admin, get_session
from app.club_identity.models.reputation import ClubReputationProfile
from app.models.base import Base
from app.models.club_profile import ClubProfile
from app.models.competition import UserCompetition
from app.models.competition_participant import CompetitionParticipant
from app.models.football_world import ClubWorldProfile, FootballCultureProfile, WorldNarrativeArc
from app.models.user import KycStatus, User, UserRole
from app.world_simulation.router import admin_router, router


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
            UserCompetition.__table__,
            CompetitionParticipant.__table__,
            ClubReputationProfile.__table__,
            FootballCultureProfile.__table__,
            ClubWorldProfile.__table__,
            WorldNarrativeArc.__table__,
        ],
    )
    session_local = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with session_local() as db_session:
        yield db_session
    engine.dispose()


@pytest.fixture()
def seeded_context(session: Session) -> dict[str, object]:
    admin = User(
        id="admin-user",
        email="admin@example.com",
        username="admin",
        display_name="Admin",
        password_hash="x",
        role=UserRole.SUPER_ADMIN,
        kyc_status=KycStatus.FULLY_VERIFIED,
        is_active=True,
    )
    owner = User(
        id="owner-alpha",
        email="owner-alpha@example.com",
        username="owner-alpha",
        display_name="Owner Alpha",
        password_hash="x",
        role=UserRole.USER,
        kyc_status=KycStatus.FULLY_VERIFIED,
        is_active=True,
    )
    challenger = User(
        id="owner-bravo",
        email="owner-bravo@example.com",
        username="owner-bravo",
        display_name="Owner Bravo",
        password_hash="x",
        role=UserRole.USER,
        kyc_status=KycStatus.FULLY_VERIFIED,
        is_active=True,
    )
    alpha = ClubProfile(
        id="club-alpha",
        owner_user_id=owner.id,
        club_name="Club Alpha",
        short_name="ALP",
        slug="club-alpha",
        primary_color="#111111",
        secondary_color="#ffffff",
        accent_color="#ff6600",
        country_code="NG",
        region_name="Lagos",
        city_name="Lagos",
        visibility="public",
    )
    bravo = ClubProfile(
        id="club-bravo",
        owner_user_id=challenger.id,
        club_name="Club Bravo",
        short_name="BRV",
        slug="club-bravo",
        primary_color="#001122",
        secondary_color="#eeeeee",
        accent_color="#00cc66",
        country_code="GH",
        region_name="Accra",
        city_name="Accra",
        visibility="public",
    )
    competition = UserCompetition(
        id="competition-1",
        host_user_id=admin.id,
        name="Mythic Derby Cup",
        format="cup",
        visibility="public",
        status="live",
        start_mode="scheduled",
        stage="knockout",
        currency="coin",
        metadata_json={},
    )
    participants = [
        CompetitionParticipant(competition_id=competition.id, club_id=alpha.id, status="joined", seed=1),
        CompetitionParticipant(competition_id=competition.id, club_id=bravo.id, status="joined", seed=2),
    ]
    reputations = [
        ClubReputationProfile(club_id=alpha.id, current_score=340, highest_score=340, prestige_tier="Elite"),
        ClubReputationProfile(club_id=bravo.id, current_score=90, highest_score=90, prestige_tier="Rising"),
    ]
    session.add_all([admin, owner, challenger, alpha, bravo, competition, *participants, *reputations])
    session.commit()
    return {"admin": admin, "club_alpha": alpha, "club_bravo": bravo, "competition": competition}


@pytest.fixture()
def client(session: Session, seeded_context: dict[str, object]) -> Iterator[TestClient]:
    app = FastAPI()
    app.include_router(router)
    app.include_router(admin_router)

    def _get_session() -> Iterator[Session]:
        yield session

    def _get_current_admin() -> User:
        admin = session.get(User, "admin-user")
        assert admin is not None
        return admin

    app.dependency_overrides[get_session] = _get_session
    app.dependency_overrides[get_current_admin] = _get_current_admin

    with TestClient(app) as test_client:
        yield test_client
