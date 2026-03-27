from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_user, get_session
from app.club_finance.router import router as club_finance_router
from app.club_finance.service import ClubFinanceService
from app.ingestion.models import Club as IngestionClub
from app.ingestion.models import Competition as IngestionCompetition
from app.ingestion.models import Country, InternalLeague, LiquidityBand, Player, SupplyTier
from app.live_ops.router import router as live_ops_router
from app.live_ops.service import LiveOpsService
from app.models.base import Base
from app.models.club_profile import ClubProfile
from app.models.competition import UserCompetition
from app.models.competition_match import CompetitionMatch
from app.models.competition_participant import CompetitionParticipant
from app.models.competition_round import CompetitionRound
from app.models.notification_record import NotificationRecord
from app.models.player_contract import PlayerContract
from app.models.user import KycStatus, User, UserRole
from app.predictions.router import router as predictions_router


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
            CompetitionParticipant.__table__,
            CompetitionMatch.__table__,
            NotificationRecord.__table__,
            Country.__table__,
            InternalLeague.__table__,
            SupplyTier.__table__,
            LiquidityBand.__table__,
            IngestionCompetition.__table__,
            IngestionClub.__table__,
            Player.__table__,
            PlayerContract.__table__,
        ],
    )
    from app.club_finance.models import ClubFinanceProfile, ClubFinanceTransaction, Sponsor
    from app.live_ops.models import LiveEvent, SeasonPass, SeasonPassClaim, SeasonPassXpGrant
    from app.predictions.models import Prediction

    Base.metadata.create_all(
        engine,
        tables=[
            Prediction.__table__,
            ClubFinanceProfile.__table__,
            Sponsor.__table__,
            ClubFinanceTransaction.__table__,
            SeasonPass.__table__,
            SeasonPassClaim.__table__,
            SeasonPassXpGrant.__table__,
            LiveEvent.__table__,
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
            id="owner-home",
            email="owner-home@example.com",
            username="owner-home",
            display_name="Owner Home",
            password_hash="x",
            role=UserRole.USER,
            kyc_status=KycStatus.FULLY_VERIFIED,
            is_active=True,
        ),
        User(
            id="owner-away",
            email="owner-away@example.com",
            username="owner-away",
            display_name="Owner Away",
            password_hash="x",
            role=UserRole.USER,
            kyc_status=KycStatus.FULLY_VERIFIED,
            is_active=True,
        ),
        User(
            id="fan-user",
            email="fan@example.com",
            username="fan-user",
            display_name="Prediction Fan",
            password_hash="x",
            role=UserRole.USER,
            kyc_status=KycStatus.FULLY_VERIFIED,
            is_active=True,
        ),
    ]
    clubs = [
        ClubProfile(
            id="club-home",
            owner_user_id="owner-home",
            club_name="Home Club",
            short_name="HOME",
            slug="home-club",
            primary_color="#111111",
            secondary_color="#eeeeee",
            accent_color="#f4b400",
            visibility="public",
        ),
        ClubProfile(
            id="club-away",
            owner_user_id="owner-away",
            club_name="Away Club",
            short_name="AWAY",
            slug="away-club",
            primary_color="#0b2a4a",
            secondary_color="#ffffff",
            accent_color="#34a853",
            visibility="public",
        ),
    ]
    competition = UserCompetition(
        id="competition-1",
        host_user_id="owner-home",
        name="Elite Test League",
        format="league",
        visibility="public",
        status="live",
        currency="coin",
    )
    round_record = CompetitionRound(
        id="round-1",
        competition_id="competition-1",
        round_number=1,
        stage="league",
        status="scheduled",
    )
    match = CompetitionMatch(
        id="match-1",
        competition_id="competition-1",
        round_id="round-1",
        round_number=1,
        home_club_id="club-home",
        away_club_id="club-away",
        status="scheduled",
        scheduled_at=datetime.now(UTC) + timedelta(hours=6),
    )
    participants = [
        CompetitionParticipant(
            id="participant-home",
            competition_id="competition-1",
            club_id="club-home",
            wins=4,
            goals_for=8,
            goal_diff=5,
            points=12,
        ),
        CompetitionParticipant(
            id="participant-away",
            competition_id="competition-1",
            club_id="club-away",
            wins=1,
            goals_for=3,
            goal_diff=-3,
            points=3,
        ),
    ]
    league = InternalLeague(id="league-1", code="league-a", name="League A", rank=1)
    supply_tier = SupplyTier(
        id="supply-1",
        code="gold",
        name="Gold",
        rank=1,
        min_score=0,
        max_score=100,
        target_share=1.0,
        circulating_supply=100,
        daily_pack_supply=10,
        season_mint_cap=1000,
    )
    liquidity_band = LiquidityBand(
        id="band-1",
        code="stable",
        name="Stable",
        rank=1,
        min_price_credits=0,
        max_price_credits=1000,
        max_spread_bps=100,
        maker_inventory_target=10,
        instant_sell_fee_bps=50,
    )
    players = [
        Player(
            id="player-1",
            source_provider="test",
            provider_external_id="player-1",
            full_name="Player One",
            current_club_profile_id="club-home",
            internal_league_id="league-1",
            supply_tier_id="supply-1",
            liquidity_band_id="band-1",
        ),
        Player(
            id="player-2",
            source_provider="test",
            provider_external_id="player-2",
            full_name="Player Two",
            current_club_profile_id="club-home",
            internal_league_id="league-1",
            supply_tier_id="supply-1",
            liquidity_band_id="band-1",
        ),
    ]
    session.add_all(users + clubs + [competition, round_record, match, league, supply_tier, liquidity_band] + participants + players)
    ClubFinanceService(session).seed_defaults()
    LiveOpsService(session).seed_defaults()
    session.commit()
    return {
        "owner_home": session.get(User, "owner-home"),
        "owner_away": session.get(User, "owner-away"),
        "fan_user": session.get(User, "fan-user"),
        "match": session.get(CompetitionMatch, "match-1"),
    }


@pytest.fixture()
def engagement_app(session: Session, seeded_context: dict[str, object]) -> FastAPI:
    app = FastAPI()
    app.include_router(predictions_router)
    app.include_router(club_finance_router)
    app.include_router(live_ops_router)
    state = {"current_user": seeded_context["fan_user"]}

    def _get_session_override() -> Iterator[Session]:
        yield session

    def _get_current_user_override() -> User:
        return state["current_user"]

    app.dependency_overrides[get_session] = _get_session_override
    app.dependency_overrides[get_current_user] = _get_current_user_override
    app.state.user_state = state
    return app


@pytest.fixture()
def engagement_client(engagement_app: FastAPI) -> Iterator[TestClient]:
    with TestClient(engagement_app) as client:
        yield client
