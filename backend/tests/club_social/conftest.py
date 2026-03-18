from __future__ import annotations

from collections.abc import Iterator

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.auth.dependencies import get_current_user
from backend.app.club_identity.models.reputation import ClubReputationProfile
from backend.app.club_social.router import router as club_social_router
from backend.app.club_social.service import ClubSocialService
from backend.app.db import get_session
from backend.app.models.base import Base
from backend.app.models.club_profile import ClubProfile
from backend.app.models.club_social import (
    ChallengeShareEvent,
    ClubChallenge,
    ClubChallengeLink,
    ClubChallengeResponse,
    ClubIdentityMetrics,
    MatchReactionEvent,
    RivalryMatchHistory,
    RivalryProfile,
)
from backend.app.models.competition import UserCompetition
from backend.app.models.competition_match import CompetitionMatch
from backend.app.models.competition_match_event import CompetitionMatchEvent
from backend.app.models.competition_participant import CompetitionParticipant
from backend.app.models.competition_round import CompetitionRound
from backend.app.models.competition_rule_set import CompetitionRuleSet
from backend.app.models.user import KycStatus, User, UserRole


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
            CompetitionRound.__table__,
            CompetitionMatch.__table__,
            CompetitionRuleSet.__table__,
            CompetitionParticipant.__table__,
            CompetitionMatchEvent.__table__,
            ClubChallenge.__table__,
            ClubChallengeResponse.__table__,
            ClubChallengeLink.__table__,
            ChallengeShareEvent.__table__,
            ClubIdentityMetrics.__table__,
            MatchReactionEvent.__table__,
            RivalryProfile.__table__,
            RivalryMatchHistory.__table__,
            ClubReputationProfile.__table__,
        ],
    )
    session_local = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with session_local() as db_session:
        db_session.add_all(
            [
                User(
                    id="user-alpha",
                    email="alpha@example.com",
                    username="alpha",
                    display_name="Alpha Owner",
                    password_hash="x",
                    role=UserRole.USER,
                    kyc_status=KycStatus.FULLY_VERIFIED,
                ),
                User(
                    id="user-bravo",
                    email="bravo@example.com",
                    username="bravo",
                    display_name="Bravo Owner",
                    password_hash="x",
                    role=UserRole.USER,
                    kyc_status=KycStatus.FULLY_VERIFIED,
                ),
                User(
                    id="user-charlie",
                    email="charlie@example.com",
                    username="charlie",
                    display_name="Charlie Owner",
                    password_hash="x",
                    role=UserRole.USER,
                    kyc_status=KycStatus.FULLY_VERIFIED,
                ),
                ClubProfile(
                    id="club-alpha",
                    owner_user_id="user-alpha",
                    club_name="Alpha FC",
                    short_name="ALP",
                    slug="alpha-fc",
                    primary_color="#101820",
                    secondary_color="#ffffff",
                    accent_color="#ff5500",
                    country_code="US",
                    region_name="California",
                    city_name="Los Angeles",
                    visibility="public",
                ),
                ClubProfile(
                    id="club-bravo",
                    owner_user_id="user-bravo",
                    club_name="Bravo United",
                    short_name="BRV",
                    slug="bravo-united",
                    primary_color="#002244",
                    secondary_color="#eeeeee",
                    accent_color="#33aa33",
                    country_code="US",
                    region_name="California",
                    city_name="Los Angeles",
                    visibility="public",
                ),
                ClubProfile(
                    id="club-charlie",
                    owner_user_id="user-charlie",
                    club_name="Charlie Town",
                    short_name="CHR",
                    slug="charlie-town",
                    primary_color="#550000",
                    secondary_color="#dddddd",
                    accent_color="#ffaa00",
                    country_code="US",
                    region_name="Texas",
                    city_name="Austin",
                    visibility="public",
                ),
                ClubReputationProfile(club_id="club-alpha", current_score=260, highest_score=260, prestige_tier="Established"),
                ClubReputationProfile(club_id="club-bravo", current_score=60, highest_score=60, prestige_tier="Rising"),
                ClubReputationProfile(club_id="club-charlie", current_score=180, highest_score=180, prestige_tier="Established"),
            ]
        )
        db_session.commit()
        yield db_session


@pytest.fixture()
def user_state(session: Session) -> dict[str, User]:
    return {"user": session.get(User, "user-alpha")}


@pytest.fixture()
def app(session: Session, user_state: dict[str, User]) -> FastAPI:
    application = FastAPI()
    application.include_router(club_social_router)

    def override_session() -> Iterator[Session]:
        yield session

    def override_user() -> User:
        return user_state["user"]

    application.dependency_overrides[get_session] = override_session
    application.dependency_overrides[get_current_user] = override_user
    return application


@pytest.fixture()
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def service(session: Session) -> ClubSocialService:
    return ClubSocialService(session)
