from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.auth.dependencies import get_current_user, get_session
from backend.app.community_engine.router import router as community_router
from backend.app.models.base import Base
from backend.app.models.club_infra import ClubSupporterHolding
from backend.app.models.club_profile import ClubProfile
from backend.app.models.club_social import RivalryProfile
from backend.app.models.competition import Competition
from backend.app.models.competition_match import CompetitionMatch
from backend.app.models.competition_round import CompetitionRound
from backend.app.models.creator_fan_engagement import (
    CreatorClubFollow,
    CreatorFanCompetition,
    CreatorFanCompetitionEntry,
    CreatorFanGroup,
    CreatorFanGroupMembership,
    CreatorFanWallEvent,
    CreatorMatchChatMessage,
    CreatorMatchChatRoom,
    CreatorMatchTacticalAdvice,
    CreatorRivalrySignalOutput,
)
from backend.app.models.creator_league import CreatorLeagueConfig, CreatorLeagueSeason, CreatorLeagueSeasonTier
from backend.app.models.creator_monetization import CreatorBroadcastPurchase, CreatorMatchGiftEvent, CreatorSeasonPass
from backend.app.models.creator_profile import CreatorProfile
from backend.app.models.creator_provisioning import CreatorSquad
from backend.app.models.media_engine import MatchView, PremiumVideoPurchase
from backend.app.models.user import KycStatus, User, UserRole
from backend.app.services.creator_fan_engagement_service import CreatorFanEngagementService


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
            CompetitionRound.__table__,
            CompetitionMatch.__table__,
            CreatorLeagueConfig.__table__,
            CreatorLeagueSeason.__table__,
            CreatorLeagueSeasonTier.__table__,
            CreatorProfile.__table__,
            CreatorSquad.__table__,
            CreatorSeasonPass.__table__,
            CreatorBroadcastPurchase.__table__,
            CreatorMatchGiftEvent.__table__,
            ClubSupporterHolding.__table__,
            MatchView.__table__,
            PremiumVideoPurchase.__table__,
            RivalryProfile.__table__,
            CreatorMatchChatRoom.__table__,
            CreatorMatchChatMessage.__table__,
            CreatorMatchTacticalAdvice.__table__,
            CreatorClubFollow.__table__,
            CreatorFanGroup.__table__,
            CreatorFanGroupMembership.__table__,
            CreatorFanCompetition.__table__,
            CreatorFanCompetitionEntry.__table__,
            CreatorFanWallEvent.__table__,
            CreatorRivalrySignalOutput.__table__,
        ],
    )
    session_local = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with session_local() as db_session:
        scheduled_at = datetime.now(UTC) + timedelta(minutes=30)
        db_session.add_all(
            [
                User(id="creator-home-user", email="creator-home@example.com", username="creator-home", display_name="Creator Home", password_hash="x", role=UserRole.USER, kyc_status=KycStatus.FULLY_VERIFIED),
                User(id="creator-away-user", email="creator-away@example.com", username="creator-away", display_name="Creator Away", password_hash="x", role=UserRole.USER, kyc_status=KycStatus.FULLY_VERIFIED),
                User(id="fan-season-share", email="fan1@example.com", username="fan-season-share", display_name="Season Share", password_hash="x", role=UserRole.USER, kyc_status=KycStatus.FULLY_VERIFIED),
                User(id="fan-season", email="fan2@example.com", username="fan-season", display_name="Season Only", password_hash="x", role=UserRole.USER, kyc_status=KycStatus.FULLY_VERIFIED),
                User(id="fan-paying", email="fan3@example.com", username="fan-paying", display_name="Paying Viewer", password_hash="x", role=UserRole.USER, kyc_status=KycStatus.FULLY_VERIFIED),
                User(id="fan-share-paying", email="fan4@example.com", username="fan-share-paying", display_name="Share Paying", password_hash="x", role=UserRole.USER, kyc_status=KycStatus.FULLY_VERIFIED),
                User(id="fan-basic", email="fan5@example.com", username="fan-basic", display_name="Basic Fan", password_hash="x", role=UserRole.USER, kyc_status=KycStatus.FULLY_VERIFIED),
                User(id="admin-user", email="admin@example.com", username="admin-user", display_name="Admin User", password_hash="x", role=UserRole.ADMIN, kyc_status=KycStatus.FULLY_VERIFIED),
                ClubProfile(id="club-home", owner_user_id="creator-home-user", club_name="Speed City", short_name="SPD", slug="speed-city", primary_color="#111111", secondary_color="#ffffff", accent_color="#ff5500", home_venue_name="Speed Dome", country_code="NG", region_name="Lagos", city_name="Lagos", visibility="public"),
                ClubProfile(id="club-away", owner_user_id="creator-away-user", club_name="Vision United", short_name="VIS", slug="vision-united", primary_color="#002244", secondary_color="#eeeeee", accent_color="#00aa66", home_venue_name="Vision Park", country_code="NG", region_name="Abuja", city_name="Abuja", visibility="public"),
                CreatorLeagueConfig(id="league-config-1", metadata_json={}),
                CreatorLeagueSeason(id="season-1", config_id="league-config-1", season_number=1, name="Creator League Season 1", status="live", start_date=scheduled_at.date(), end_date=scheduled_at.date(), metadata_json={}),
                Competition(id="competition-1", host_user_id="admin-user", name="Creator League Division 1", description="Creator League", competition_type="league", source_type="creator_league", source_id="season-tier-1", format="league", visibility="public", status="live", start_mode="scheduled", scheduled_start_at=scheduled_at, opened_at=scheduled_at, launched_at=scheduled_at, stage="league", currency="coin", entry_fee_minor=0, platform_fee_bps=0, host_fee_bps=0, host_creation_fee_minor=0, gross_pool_minor=0, net_prize_pool_minor=0, metadata_json={"creator_league": True}),
                CreatorLeagueSeasonTier(id="season-tier-1", season_id="season-1", tier_id="tier-1", competition_id="competition-1", competition_name="Creator League Division 1", tier_name="Division 1", tier_order=1, club_ids_json=["club-home", "club-away"], round_count=1, fixture_count=1, status="live", metadata_json={}),
                CompetitionRound(id="round-1", competition_id="competition-1", round_number=1, stage="league", status="scheduled", metadata_json={}),
                CompetitionMatch(id="match-1", competition_id="competition-1", round_id="round-1", round_number=1, stage="league", home_club_id="club-home", away_club_id="club-away", scheduled_at=scheduled_at, match_date=scheduled_at.date(), status="scheduled", metadata_json={}),
                CreatorProfile(id="creator-profile-home", user_id="creator-home-user", handle="speed_home", display_name="Creator Home"),
                CreatorProfile(id="creator-profile-away", user_id="creator-away-user", handle="vision_away", display_name="Creator Away"),
            ]
        )
        db_session.flush()
        home_profile = db_session.get(CreatorProfile, "creator-profile-home")
        away_profile = db_session.get(CreatorProfile, "creator-profile-away")
        home_profile.tier = "elite"
        away_profile.tier = "elite"
        db_session.add_all(
            [
                CreatorSquad(id="squad-home", club_id="club-home", creator_profile_id="creator-profile-home", first_team_json=[], academy_json=[], metadata_json={}),
                CreatorSquad(id="squad-away", club_id="club-away", creator_profile_id="creator-profile-away", first_team_json=[], academy_json=[], metadata_json={}),
                CreatorSeasonPass(id="season-pass-1", user_id="fan-season-share", creator_user_id="creator-home-user", season_id="season-1", club_id="club-home", price_coin=Decimal("60.0000"), creator_share_coin=Decimal("30.0000"), platform_share_coin=Decimal("30.0000"), metadata_json={}),
                CreatorSeasonPass(id="season-pass-2", user_id="fan-season", creator_user_id="creator-away-user", season_id="season-1", club_id="club-away", price_coin=Decimal("60.0000"), creator_share_coin=Decimal("30.0000"), platform_share_coin=Decimal("30.0000"), metadata_json={}),
                CreatorBroadcastPurchase(id="purchase-1", user_id="fan-paying", season_id="season-1", competition_id="competition-1", match_id="match-1", mode_key="full_match", duration_minutes=90, price_coin=Decimal("10.0000"), platform_share_coin=Decimal("5.0000"), home_creator_share_coin=Decimal("2.5000"), away_creator_share_coin=Decimal("2.5000"), metadata_json={}),
                CreatorBroadcastPurchase(id="purchase-2", user_id="fan-share-paying", season_id="season-1", competition_id="competition-1", match_id="match-1", mode_key="full_match", duration_minutes=90, price_coin=Decimal("10.0000"), platform_share_coin=Decimal("5.0000"), home_creator_share_coin=Decimal("2.5000"), away_creator_share_coin=Decimal("2.5000"), metadata_json={}),
                ClubSupporterHolding(id="holding-1", club_id="club-home", user_id="fan-season-share", token_balance=50, influence_points=10, metadata_json={}),
                ClubSupporterHolding(id="holding-2", club_id="club-away", user_id="fan-share-paying", token_balance=25, influence_points=5, metadata_json={}),
                RivalryProfile(id="rivalry-1", club_a_id="club-home", club_b_id="club-away", intensity_score=40, metadata_json={}, notable_moments_json=[], narrative_tags_json=[]),
            ]
        )
        db_session.commit()
        yield db_session


@pytest.fixture()
def service(session: Session) -> CreatorFanEngagementService:
    return CreatorFanEngagementService(session)


@pytest.fixture()
def user_state(session: Session) -> dict[str, User]:
    return {"user": session.get(User, "fan-season-share")}


@pytest.fixture()
def app(session: Session, user_state: dict[str, User]) -> FastAPI:
    application = FastAPI()
    application.include_router(community_router)

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
