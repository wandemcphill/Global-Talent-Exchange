from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.auth.dependencies import get_current_admin, get_current_user, get_session
from backend.app.club_identity.models.reputation import ClubReputationProfile
from backend.app.fan_predictions.router import admin_router, router
from backend.app.models.admin_rules import AdminRewardRule
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
from backend.app.models.creator_fan_engagement import CreatorClubFollow, CreatorFanGroup
from backend.app.models.creator_league import CreatorLeagueConfig, CreatorLeagueSeason, CreatorLeagueSeasonTier
from backend.app.models.creator_monetization import CreatorSeasonPass
from backend.app.models.economy_burn_event import EconomyBurnEvent
from backend.app.models.fan_prediction import (
    FanPredictionFixture,
    FanPredictionOutcome,
    FanPredictionRewardGrant,
    FanPredictionSubmission,
    FanPredictionTokenLedger,
)
from backend.app.models.revenue_share_rule import RevenueShareRule
from backend.app.models.reward_settlement import RewardSettlement
from backend.app.models.spending_control import SpendingControlAuditEvent
from backend.app.models.user import KycStatus, User, UserRole
from backend.app.models.wallet import LedgerAccount, LedgerEntry, LedgerUnit
from backend.app.reward_engine.service import RewardEngineService


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
            CompetitionRuleSet.__table__,
            CompetitionParticipant.__table__,
            CompetitionMatch.__table__,
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
            CreatorLeagueConfig.__table__,
            CreatorLeagueSeason.__table__,
            CreatorLeagueSeasonTier.__table__,
            CreatorSeasonPass.__table__,
            CreatorClubFollow.__table__,
            CreatorFanGroup.__table__,
            FanPredictionFixture.__table__,
            FanPredictionOutcome.__table__,
            FanPredictionSubmission.__table__,
            FanPredictionTokenLedger.__table__,
            FanPredictionRewardGrant.__table__,
            AdminRewardRule.__table__,
            RevenueShareRule.__table__,
            LedgerAccount.__table__,
            LedgerEntry.__table__,
            RewardSettlement.__table__,
            EconomyBurnEvent.__table__,
            SpendingControlAuditEvent.__table__,
        ],
    )
    session_local = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with session_local() as db_session:
        yield db_session
    engine.dispose()


@pytest.fixture()
def seeded_context(session: Session) -> dict[str, object]:
    users = [
        User(
            id="admin-user",
            email="admin@example.com",
            username="admin",
            display_name="Admin",
            password_hash="x",
            role=UserRole.SUPER_ADMIN,
            kyc_status=KycStatus.FULLY_VERIFIED,
            is_active=True,
        ),
        User(
            id="owner-alpha",
            email="owner-alpha@example.com",
            username="owner-alpha",
            display_name="Owner Alpha",
            password_hash="x",
            role=UserRole.USER,
            kyc_status=KycStatus.FULLY_VERIFIED,
            is_active=True,
        ),
        User(
            id="owner-bravo",
            email="owner-bravo@example.com",
            username="owner-bravo",
            display_name="Owner Bravo",
            password_hash="x",
            role=UserRole.USER,
            kyc_status=KycStatus.FULLY_VERIFIED,
            is_active=True,
        ),
        User(
            id="fan-one",
            email="fan-one@example.com",
            username="fan-one",
            display_name="Fan One",
            password_hash="x",
            role=UserRole.USER,
            kyc_status=KycStatus.FULLY_VERIFIED,
            is_active=True,
        ),
        User(
            id="fan-two",
            email="fan-two@example.com",
            username="fan-two",
            display_name="Fan Two",
            password_hash="x",
            role=UserRole.USER,
            kyc_status=KycStatus.FULLY_VERIFIED,
            is_active=True,
        ),
    ]
    clubs = [
        ClubProfile(
            id="club-alpha",
            owner_user_id="owner-alpha",
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
        ),
        ClubProfile(
            id="club-bravo",
            owner_user_id="owner-bravo",
            club_name="Club Bravo",
            short_name="BRV",
            slug="club-bravo",
            primary_color="#001122",
            secondary_color="#eeeeee",
            accent_color="#00cc66",
            country_code="NG",
            region_name="Lagos",
            city_name="Lagos",
            visibility="public",
        ),
    ]
    config = CreatorLeagueConfig(id="cfg-1", league_key="creator_league", metadata_json={})
    season = CreatorLeagueSeason(
        id="season-1",
        config_id="cfg-1",
        season_number=1,
        name="Creator Season 1",
        status="live",
        start_date=date(2026, 3, 1),
        end_date=date(2026, 5, 31),
        match_frequency_days=7,
        season_duration_days=90,
        metadata_json={},
    )
    competition = UserCompetition(
        id="competition-1",
        host_user_id="admin-user",
        name="Creator Derby",
        format="league",
        visibility="public",
        status="live",
        start_mode="scheduled",
        currency="coin",
        metadata_json={},
    )
    season_tier = CreatorLeagueSeasonTier(
        id="tier-1",
        season_id="season-1",
        tier_id="tier-template-1",
        competition_id="competition-1",
        competition_name="Creator Derby",
        tier_name="Division 1",
        tier_order=1,
        club_ids_json=["club-alpha", "club-bravo"],
        round_count=1,
        fixture_count=1,
        status="live",
        metadata_json={},
    )
    round_ = CompetitionRound(
        id="round-1",
        competition_id="competition-1",
        round_number=1,
        stage="league",
        status="live",
        metadata_json={},
    )
    rule_set = CompetitionRuleSet(
        id="rules-1",
        competition_id="competition-1",
        format="league",
        min_participants=2,
        max_participants=20,
        league_win_points=3,
        league_draw_points=1,
        league_loss_points=0,
        league_tie_break_order=["points", "goal_diff", "goals_for"],
        cup_allowed_participant_sizes=[],
    )
    participants = [
        CompetitionParticipant(id="participant-1", competition_id="competition-1", club_id="club-alpha"),
        CompetitionParticipant(id="participant-2", competition_id="competition-1", club_id="club-bravo"),
    ]
    match = CompetitionMatch(
        id="match-1",
        competition_id="competition-1",
        round_id="round-1",
        round_number=1,
        stage="league",
        home_club_id="club-alpha",
        away_club_id="club-bravo",
        scheduled_at=datetime.now(UTC) + timedelta(hours=1),
        status="scheduled",
        metadata_json={},
    )
    season_pass = CreatorSeasonPass(
        id="pass-1",
        user_id="fan-one",
        creator_user_id="owner-alpha",
        season_id="season-1",
        club_id="club-alpha",
        price_coin=Decimal("100.0000"),
        creator_share_coin=Decimal("50.0000"),
        platform_share_coin=Decimal("50.0000"),
        metadata_json={},
    )
    follow = CreatorClubFollow(id="follow-1", club_id="club-bravo", user_id="fan-two", metadata_json={})

    session.add_all(users + clubs + [config, season, competition, season_tier, round_, rule_set, match, season_pass, follow, *participants])
    session.commit()

    RewardEngineService(session).credit_promo_pool(
        actor=session.get(User, "admin-user"),
        amount=Decimal("1000.0000"),
        unit=LedgerUnit.COIN,
        reference="test-promo-pool",
        note="Test promo pool funding",
    )
    session.commit()

    return {
        "admin": session.get(User, "admin-user"),
        "fan_one": session.get(User, "fan-one"),
        "fan_two": session.get(User, "fan-two"),
        "match": session.get(CompetitionMatch, "match-1"),
        "rule_set": session.get(CompetitionRuleSet, "rules-1"),
    }


@pytest.fixture()
def app(session: Session, seeded_context: dict[str, object]) -> FastAPI:
    application = FastAPI()
    application.include_router(router)
    application.include_router(admin_router)
    user_state = {"current_user": seeded_context["fan_one"], "current_admin": seeded_context["admin"]}

    def override_session() -> Iterator[Session]:
        yield session

    def override_user() -> User:
        return user_state["current_user"]

    def override_admin() -> User:
        return user_state["current_admin"]

    application.dependency_overrides[get_session] = override_session
    application.dependency_overrides[get_current_user] = override_user
    application.dependency_overrides[get_current_admin] = override_admin
    application.state.user_state = user_state
    return application


@pytest.fixture()
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
