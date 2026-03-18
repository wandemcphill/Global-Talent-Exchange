from __future__ import annotations

from collections.abc import Iterator

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.auth.dependencies import get_current_admin, get_session
from backend.app.competitions.creator_league_router import router as creator_league_router
from backend.app.models.admin_rules import AdminRewardRule
from backend.app.models.base import Base
from backend.app.models.club_profile import ClubProfile
from backend.app.models.competition import Competition
from backend.app.models.competition_match import CompetitionMatch
from backend.app.models.competition_participant import CompetitionParticipant
from backend.app.models.competition_round import CompetitionRound
from backend.app.models.competition_rule_set import CompetitionRuleSet
from backend.app.models.competition_schedule_job import CompetitionScheduleJob
from backend.app.models.creator_league import CreatorLeagueConfig, CreatorLeagueSeason, CreatorLeagueSeasonTier, CreatorLeagueTier
from backend.app.models.creator_monetization import CreatorRevenueSettlement, CreatorStadiumControl
from backend.app.models.creator_share_market import CreatorClubShareMarketControl
from backend.app.models.risk_ops import AuditLog
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
            Competition.__table__,
            CompetitionRuleSet.__table__,
            CompetitionParticipant.__table__,
            CompetitionRound.__table__,
            CompetitionMatch.__table__,
            CompetitionScheduleJob.__table__,
            AdminRewardRule.__table__,
            CreatorLeagueConfig.__table__,
            CreatorLeagueTier.__table__,
            CreatorLeagueSeason.__table__,
            CreatorLeagueSeasonTier.__table__,
            CreatorRevenueSettlement.__table__,
            CreatorStadiumControl.__table__,
            CreatorClubShareMarketControl.__table__,
            AuditLog.__table__,
        ],
    )
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    db = SessionLocal()
    db.add_all(
        [
            User(
                id="admin-user",
                email="admin@example.com",
                username="admin",
                full_name="Admin",
                display_name="Admin",
                password_hash="not-used",
                role=UserRole.ADMIN,
                kyc_status=KycStatus.FULLY_VERIFIED,
                is_active=True,
            ),
            User(
                id="club-owner",
                email="owner@example.com",
                username="club-owner",
                full_name="Club Owner",
                display_name="Club Owner",
                password_hash="not-used",
                role=UserRole.USER,
                kyc_status=KycStatus.FULLY_VERIFIED,
                is_active=True,
            ),
        ]
    )
    db.commit()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


@pytest.fixture()
def seeded_clubs(session: Session) -> list[ClubProfile]:
    clubs = [
        ClubProfile(
            id=f"club-{index:02d}",
            owner_user_id="club-owner",
            club_name=f"Creator Club {index:02d}",
            short_name=f"CC{index:02d}",
            slug=f"creator-club-{index:02d}",
            primary_color="#111111",
            secondary_color="#eeeeee",
            accent_color="#ff6600",
            home_venue_name=f"Venue {index:02d}",
            country_code="NG",
            region_name="Lagos",
            city_name="Lagos",
            description="Creator League test club",
            visibility="public",
        )
        for index in range(1, 81)
    ]
    session.add_all(clubs)
    session.commit()
    return clubs


@pytest.fixture()
def api_client(session: Session) -> Iterator[TestClient]:
    app = FastAPI()
    app.include_router(creator_league_router, prefix="/api/competitions")

    def _override_session() -> Iterator[Session]:
        yield session

    def _override_admin() -> User:
        return session.get(User, "admin-user")

    app.dependency_overrides[get_session] = _override_session
    app.dependency_overrides[get_current_admin] = _override_admin

    with TestClient(app) as client:
        yield client
