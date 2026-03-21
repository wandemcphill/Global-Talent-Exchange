from __future__ import annotations

from collections.abc import Callable, Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.common.enums.creator_profile_status import CreatorProfileStatus
from app.models.base import Base
from app.models.calendar_engine import CalendarEvent
from app.models.club_profile import ClubProfile
from app.models.competition import Competition
from app.models.competition_match import CompetitionMatch
from app.models.competition_match_event import CompetitionMatchEvent
from app.models.competition_participant import CompetitionParticipant
from app.models.competition_playoff import CompetitionPlayoff
from app.models.competition_round import CompetitionRound
from app.models.competition_rule_set import CompetitionRuleSet
from app.models.competition_schedule_job import CompetitionScheduleJob
from app.models.competition_seed_rule import CompetitionSeedRule
from app.models.creator_profile import CreatorProfile
from app.models.creator_provisioning import CreatorSquad
from app.models.fan_war import (
    CountryCreatorAssignment,
    FanWarPoint,
    FanWarProfile,
    FanbaseRanking,
    NationsCupEntry,
    NationsCupFanMetric,
)
from app.models.story_feed import StoryFeedItem
from app.models.user import KycStatus, User, UserRole
from app.models.user_region import UserRegionProfile


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
            UserRegionProfile.__table__,
            ClubProfile.__table__,
            CreatorProfile.__table__,
            CreatorSquad.__table__,
            Competition.__table__,
            CompetitionRuleSet.__table__,
            CompetitionSeedRule.__table__,
            CompetitionParticipant.__table__,
            CompetitionRound.__table__,
            CompetitionMatch.__table__,
            CompetitionMatchEvent.__table__,
            CompetitionPlayoff.__table__,
            CompetitionScheduleJob.__table__,
            CalendarEvent.__table__,
            StoryFeedItem.__table__,
            FanWarProfile.__table__,
            CountryCreatorAssignment.__table__,
            NationsCupEntry.__table__,
            FanWarPoint.__table__,
            NationsCupFanMetric.__table__,
            FanbaseRanking.__table__,
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
                id="fan-user",
                email="fan@example.com",
                username="fan",
                full_name="Fan User",
                display_name="Fan User",
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
def admin_user(session: Session) -> User:
    return session.get(User, "admin-user")


@pytest.fixture()
def fan_user(session: Session) -> User:
    return session.get(User, "fan-user")


@pytest.fixture()
def creator_factory(session: Session) -> Callable[[str, str, str], dict[str, object]]:
    counter = 0

    def _create(display_name: str, handle: str, country_code: str, *, tier: str = "established") -> dict[str, object]:
        nonlocal counter
        counter += 1
        user_id = f"creator-user-{counter}"
        creator_id = f"creator-profile-{counter}"
        club_id = f"creator-club-{counter}"
        session.add(
            User(
                id=user_id,
                email=f"{handle}@example.com",
                username=handle,
                full_name=display_name,
                display_name=display_name,
                password_hash="not-used",
                role=UserRole.USER,
                kyc_status=KycStatus.FULLY_VERIFIED,
                is_active=True,
            )
        )
        session.add(UserRegionProfile(user_id=user_id, region_code=country_code))
        creator_profile = CreatorProfile(
            id=creator_id,
            user_id=user_id,
            handle=handle,
            display_name=display_name,
            tier=tier,
            status=CreatorProfileStatus.ACTIVE,
            payout_config_json={},
        )
        club = ClubProfile(
            id=club_id,
            owner_user_id=user_id,
            club_name=f"{display_name} FC",
            short_name=handle[:4].upper(),
            slug=f"{handle}-club",
            primary_color="#112233",
            secondary_color="#eeeeee",
            accent_color="#ff6600",
            home_venue_name=f"{display_name} Arena",
            country_code=country_code,
            region_name="Region",
            city_name="City",
            description="Test creator club",
            visibility="public",
        )
        squad = CreatorSquad(
            id=f"creator-squad-{counter}",
            club_id=club_id,
            creator_profile_id=creator_id,
            first_team_json=[],
            academy_json=[],
            metadata_json={},
        )
        session.add_all([creator_profile, club, squad])
        session.flush()
        return {"user": session.get(User, user_id), "creator_profile": creator_profile, "club": club, "squad": squad}

    return _create
