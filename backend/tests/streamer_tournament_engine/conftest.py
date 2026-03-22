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

from app.auth.dependencies import get_current_admin, get_current_user, get_session
from app.models.admin_rules import AdminRewardRule
from app.models.base import Base
from app.models.club_profile import ClubProfile
from app.models.competition import Competition
from app.models.competition_entry import CompetitionEntry
from app.models.competition_match import CompetitionMatch
from app.models.competition_participant import CompetitionParticipant
from app.models.competition_round import CompetitionRound
from app.models.creator_league import CreatorLeagueSeason
from app.models.creator_monetization import CreatorMatchGiftEvent, CreatorSeasonPass
from app.models.creator_profile import CreatorProfile
from app.models.creator_provisioning import CreatorSquad
from app.models.creator_share_market import (
    CreatorClubShareDistribution,
    CreatorClubShareHolding,
    CreatorClubShareMarket,
    CreatorClubShareMarketControl,
    CreatorClubSharePayout,
    CreatorClubSharePurchase,
)
from app.models.economy_burn_event import EconomyBurnEvent
from app.models.revenue_share_rule import RevenueShareRule
from app.models.reward_settlement import RewardSettlement
from app.models.streamer_tournament import (
    StreamerTournament,
    StreamerTournamentEntry,
    StreamerTournamentInvite,
    StreamerTournamentPolicy,
    StreamerTournamentReward,
    StreamerTournamentRewardGrant,
    StreamerTournamentRiskSignal,
)
from app.models.user import KycStatus, User, UserRole
from app.models.wallet import LedgerAccount, LedgerEntry
from app.streamer_tournament_engine.router import admin_router, router


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
            CreatorProfile.__table__,
            CreatorSquad.__table__,
            CreatorLeagueSeason.__table__,
            Competition.__table__,
            CompetitionRound.__table__,
            CompetitionMatch.__table__,
            CompetitionEntry.__table__,
            CompetitionParticipant.__table__,
            CreatorSeasonPass.__table__,
            CreatorMatchGiftEvent.__table__,
            CreatorClubShareMarketControl.__table__,
            CreatorClubShareMarket.__table__,
            CreatorClubShareHolding.__table__,
            CreatorClubSharePurchase.__table__,
            CreatorClubShareDistribution.__table__,
            CreatorClubSharePayout.__table__,
            StreamerTournamentPolicy.__table__,
            StreamerTournament.__table__,
            StreamerTournamentInvite.__table__,
            StreamerTournamentEntry.__table__,
            StreamerTournamentReward.__table__,
            StreamerTournamentRiskSignal.__table__,
            StreamerTournamentRewardGrant.__table__,
            RevenueShareRule.__table__,
            AdminRewardRule.__table__,
            RewardSettlement.__table__,
            EconomyBurnEvent.__table__,
            LedgerAccount.__table__,
            LedgerEntry.__table__,
        ],
    )
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


@pytest.fixture()
def seeded_context(session: Session) -> dict[str, object]:
    users = [
        User(
            id="admin-user",
            email="admin@example.com",
            username="admin",
            full_name="Admin User",
            display_name="Admin User",
            password_hash="x",
            role=UserRole.ADMIN,
            kyc_status=KycStatus.FULLY_VERIFIED,
            is_active=True,
        ),
        User(
            id="creator-user",
            email="creator@example.com",
            username="creator",
            full_name="Creator User",
            display_name="Creator User",
            password_hash="x",
            role=UserRole.USER,
            kyc_status=KycStatus.FULLY_VERIFIED,
            is_active=True,
        ),
        User(
            id="invitee-user",
            email="invitee@example.com",
            username="invitee",
            full_name="Invitee User",
            display_name="Invitee User",
            password_hash="x",
            role=UserRole.USER,
            kyc_status=KycStatus.FULLY_VERIFIED,
            is_active=True,
        ),
        User(
            id="season-fan",
            email="season@example.com",
            username="season-fan",
            full_name="Season Fan",
            display_name="Season Fan",
            password_hash="x",
            role=UserRole.USER,
            kyc_status=KycStatus.FULLY_VERIFIED,
            is_active=True,
        ),
        User(
            id="playoff-fan",
            email="playoff@example.com",
            username="playoff-fan",
            full_name="Playoff Fan",
            display_name="Playoff Fan",
            password_hash="x",
            role=UserRole.USER,
            kyc_status=KycStatus.FULLY_VERIFIED,
            is_active=True,
        ),
        User(
            id="gifter-fan",
            email="gifter@example.com",
            username="gifter-fan",
            full_name="Gifter Fan",
            display_name="Gifter Fan",
            password_hash="x",
            role=UserRole.USER,
            kyc_status=KycStatus.FULLY_VERIFIED,
            is_active=True,
        ),
        User(
            id="other-gifter",
            email="other-gifter@example.com",
            username="other-gifter",
            full_name="Other Gifter",
            display_name="Other Gifter",
            password_hash="x",
            role=UserRole.USER,
            kyc_status=KycStatus.FULLY_VERIFIED,
            is_active=True,
        ),
    ]
    session.add_all(users)

    creator_club = ClubProfile(
        id="creator-club",
        owner_user_id="creator-user",
        club_name="Creator Club",
        short_name="CC",
        slug="creator-club",
        primary_color="#111111",
        secondary_color="#ffffff",
        accent_color="#ff5500",
        home_venue_name="Creator Arena",
        country_code="NG",
        region_name="Lagos",
        city_name="Lagos",
        description="Creator club",
        visibility="public",
    )
    playoff_club = ClubProfile(
        id="playoff-club",
        owner_user_id="playoff-fan",
        club_name="Playoff Club",
        short_name="PC",
        slug="playoff-club",
        primary_color="#0000ff",
        secondary_color="#ffffff",
        accent_color="#00ff00",
        home_venue_name="Playoff Dome",
        country_code="NG",
        region_name="Lagos",
        city_name="Lagos",
        description="Playoff club",
        visibility="public",
    )
    session.add_all([creator_club, playoff_club])

    creator_profile = CreatorProfile(
        id="creator-profile",
        user_id="creator-user",
        handle="creator-handle",
        display_name="Creator User",
        status="active",
    )
    session.add(creator_profile)
    session.add(
        CreatorSquad(
            id="creator-squad",
            club_id="creator-club",
            creator_profile_id="creator-profile",
            first_team_json=[],
            academy_json=[],
            metadata_json={},
        )
    )

    season = CreatorLeagueSeason(
        id="season-1",
        config_id="season-config",
        season_number=1,
        name="Season One",
        status="live",
        start_date=datetime(2026, 1, 1, tzinfo=UTC).date(),
        end_date=datetime(2026, 12, 31, tzinfo=UTC).date(),
        metadata_json={},
    )
    session.add(season)

    competition = Competition(
        id="competition-1",
        host_user_id="creator-user",
        name="Source Competition",
        competition_type="league",
        source_type="creator_league",
        source_id="season-tier-1",
        format="league",
        visibility="public",
        status="live",
        start_mode="scheduled",
        stage="playoffs",
        currency="coin",
        metadata_json={},
    )
    session.add(competition)
    round_one = CompetitionRound(
        id="round-1",
        competition_id="competition-1",
        round_number=1,
        stage="league",
        name="Round 1",
        status="completed",
        metadata_json={},
    )
    session.add(round_one)
    match = CompetitionMatch(
        id="match-1",
        competition_id="competition-1",
        round_id="round-1",
        round_number=1,
        stage="league",
        home_club_id="creator-club",
        away_club_id="playoff-club",
        scheduled_at=datetime(2026, 3, 1, 12, 0, tzinfo=UTC),
        match_date=datetime(2026, 3, 1, 12, 0, tzinfo=UTC).date(),
        status="completed",
        completed_at=datetime(2026, 3, 1, 14, 0, tzinfo=UTC),
        metadata_json={},
    )
    session.add(match)

    session.add(
        CompetitionEntry(
            id="playoff-entry",
            competition_id="competition-1",
            club_id="playoff-club",
            user_id="playoff-fan",
            entry_type="direct",
            status="accepted",
            metadata_json={},
        )
    )
    session.add(
        CompetitionParticipant(
            id="playoff-participant",
            competition_id="competition-1",
            club_id="playoff-club",
            entry_id="playoff-entry",
            status="joined",
            seed=2,
            advanced=True,
            points=9,
        )
    )

    session.add(
        CreatorSeasonPass(
            id="season-pass-1",
            user_id="season-fan",
            creator_user_id="creator-user",
            season_id="season-1",
            club_id="creator-club",
            price_coin=Decimal("25.0000"),
            creator_share_coin=Decimal("12.5000"),
            platform_share_coin=Decimal("12.5000"),
            metadata_json={},
        )
    )

    session.add_all(
        [
            CreatorMatchGiftEvent(
                id="gift-1",
                season_id="season-1",
                competition_id="competition-1",
                match_id="match-1",
                sender_user_id="gifter-fan",
                recipient_creator_user_id="creator-user",
                club_id="creator-club",
                gift_label="Mega Cheer",
                gross_amount_coin=Decimal("300.0000"),
                creator_share_coin=Decimal("210.0000"),
                platform_share_coin=Decimal("90.0000"),
                metadata_json={},
            ),
            CreatorMatchGiftEvent(
                id="gift-2",
                season_id="season-1",
                competition_id="competition-1",
                match_id="match-1",
                sender_user_id="other-gifter",
                recipient_creator_user_id="creator-user",
                club_id="creator-club",
                gift_label="Cheer",
                gross_amount_coin=Decimal("100.0000"),
                creator_share_coin=Decimal("70.0000"),
                platform_share_coin=Decimal("30.0000"),
                metadata_json={},
            ),
        ]
    )

    session.add(
        RevenueShareRule(
            id="reward-split",
            rule_key="competition-reward-default",
            scope="competition_reward",
            title="Competition reward split",
            description="Default split",
            platform_share_bps=1000,
            creator_share_bps=0,
            recipient_share_bps=None,
            burn_bps=0,
            priority=10,
            active=True,
        )
    )
    session.commit()
    return {
        "admin": session.get(User, "admin-user"),
        "creator": session.get(User, "creator-user"),
        "invitee": session.get(User, "invitee-user"),
        "season_fan": session.get(User, "season-fan"),
        "playoff_fan": session.get(User, "playoff-fan"),
        "gifter_fan": session.get(User, "gifter-fan"),
    }


@pytest.fixture()
def api_client(session: Session, seeded_context: dict[str, object]) -> Iterator[TestClient]:
    app = FastAPI()
    app.include_router(router)
    app.include_router(admin_router)
    app.state.current_user_id = "creator-user"

    def _override_session() -> Iterator[Session]:
        yield session

    def _override_user() -> User:
        return session.get(User, app.state.current_user_id)

    def _override_admin() -> User:
        return session.get(User, app.state.current_user_id)

    app.dependency_overrides[get_session] = _override_session
    app.dependency_overrides[get_current_user] = _override_user
    app.dependency_overrides[get_current_admin] = _override_admin

    with TestClient(app) as client:
        yield client
