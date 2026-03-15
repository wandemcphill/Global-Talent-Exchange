from __future__ import annotations

from datetime import date, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.auth.dependencies import get_current_user
from backend.app.club_identity.models.reputation import ClubReputationProfile, ReputationEventLog, ReputationSnapshot
from backend.app.competition_engine.match_dispatcher import MatchDispatcher
from backend.app.competition_engine.queue_contracts import InMemoryQueuePublisher
from backend.app.core.events import InMemoryEventPublisher
from backend.app.db import get_session
from backend.app.leagues.models import LeagueClub
from backend.app.leagues.repository import InMemoryLeagueEventRepository
from backend.app.leagues.service import LeagueSeasonLifecycleService
from backend.app.match_engine.services import LeagueFixtureExecutionService, LocalMatchExecutionWorker
from backend.app.models.base import Base
from backend.app.models.club_branding_asset import ClubBrandingAsset
from backend.app.models.club_dynasty_milestone import ClubDynastyMilestone
from backend.app.models.club_dynasty_progress import ClubDynastyProgress
from backend.app.models.club_identity_theme import ClubIdentityTheme
from backend.app.models.club_jersey_design import ClubJerseyDesign
from backend.app.models.club_profile import ClubProfile
from backend.app.models.club_showcase_snapshot import ClubShowcaseSnapshot
from backend.app.models.club_trophy import ClubTrophy
from backend.app.models.club_trophy_cabinet import ClubTrophyCabinet
from backend.app.models.competition import Competition
from backend.app.models.competition_entry import CompetitionEntry
from backend.app.models.competition_invite import CompetitionInvite
from backend.app.models.competition_participant import CompetitionParticipant
from backend.app.models.competition_prize_rule import CompetitionPrizeRule
from backend.app.models.competition_reward_pool import CompetitionRewardPool
from backend.app.models.competition_rule_set import CompetitionRuleSet
from backend.app.models.competition_seed_rule import CompetitionSeedRule
from backend.app.models.competition_visibility_rule import CompetitionVisibilityRule
from backend.app.models.competition_wallet_ledger import CompetitionWalletLedger
from backend.app.models.user import KycStatus, User, UserRole
from backend.app.notifications.service import NotificationCenter
from backend.app.replay_archive.persistence import InMemoryReplayArchiveRepository
from backend.app.replay_archive.policy import SpectatorVisibilityPolicyService
from backend.app.replay_archive.service import ReplayArchiveService
from backend.app.routes.clubs import router as clubs_router
from backend.app.routes.competitions import router as competitions_router
from backend.app.services.competition_orchestrator import CompetitionOrchestrator, get_competition_orchestrator


def test_gtex_happy_path_smoke() -> None:
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
            ClubReputationProfile.__table__,
            ReputationEventLog.__table__,
            ReputationSnapshot.__table__,
            ClubTrophyCabinet.__table__,
            ClubTrophy.__table__,
            ClubDynastyProgress.__table__,
            ClubDynastyMilestone.__table__,
            ClubBrandingAsset.__table__,
            ClubJerseyDesign.__table__,
            ClubIdentityTheme.__table__,
            ClubShowcaseSnapshot.__table__,
            Competition.__table__,
            CompetitionRuleSet.__table__,
            CompetitionPrizeRule.__table__,
            CompetitionRewardPool.__table__,
            CompetitionSeedRule.__table__,
            CompetitionVisibilityRule.__table__,
            CompetitionInvite.__table__,
            CompetitionEntry.__table__,
            CompetitionParticipant.__table__,
            CompetitionWalletLedger.__table__,
        ],
    )
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session: Session = SessionLocal()
    session.add(
        User(
            id="user-owner",
            email="owner@example.com",
            username="owner",
            display_name="Owner",
            password_hash="x",
            role=UserRole.USER,
            kyc_status=KycStatus.VERIFIED,
        )
    )
    session.commit()

    app = FastAPI()
    app.include_router(clubs_router)
    app.include_router(competitions_router)
    orchestrator = CompetitionOrchestrator(session)
    app.dependency_overrides[get_competition_orchestrator] = lambda: orchestrator
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_current_user] = lambda: session.get(User, "user-owner")

    with TestClient(app) as client:
        home = client.post(
            "/api/clubs",
            json={
                "club_name": "Metro FC",
                "short_name": "MFC",
                "slug": "metro-fc",
                "primary_color": "#112233",
                "secondary_color": "#445566",
                "accent_color": "#ddeeff",
                "visibility": "public",
            },
        )
        away = client.post(
            "/api/clubs",
            json={
                "club_name": "River FC",
                "short_name": "RFC",
                "slug": "river-fc",
                "primary_color": "#221144",
                "secondary_color": "#ffffff",
                "accent_color": "#ff9900",
                "visibility": "public",
            },
        )
        assert home.status_code == 201, home.text
        assert away.status_code == 201, away.text
        home_id = home.json()["profile"]["id"]
        away_id = away.json()["profile"]["id"]

        created = client.post(
            "/api/competitions",
            json={
                "name": "GTEX League Smoke",
                "format": "league",
                "visibility": "public",
                "entry_fee": "0.00",
                "currency": "credit",
                "capacity": 2,
                "creator_id": home_id,
                "creator_name": "Metro FC",
                "payout_structure": [{"place": 1, "percent": "1.00"}],
            },
        )
        assert created.status_code == 201, created.text
        competition_id = created.json()["id"]

        published = client.post(f"/api/competitions/{competition_id}/publish", json={"open_for_join": True})
        assert published.status_code == 200, published.text

        joined = client.post(
            f"/api/competitions/{competition_id}/join",
            json={"user_id": away_id, "user_name": "River FC"},
        )
        assert joined.status_code == 200, joined.text

    repository = InMemoryLeagueEventRepository()
    league_service = LeagueSeasonLifecycleService(repository=repository)
    event_publisher = InMemoryEventPublisher()
    notifications = NotificationCenter()
    replay_archive = ReplayArchiveService(
        spectator_policy=SpectatorVisibilityPolicyService(),
        repository=InMemoryReplayArchiveRepository(),
    )
    event_publisher.subscribe(notifications.handle_event)
    event_publisher.subscribe(replay_archive.handle_event)
    queue_publisher = InMemoryQueuePublisher(event_publisher=event_publisher)
    dispatcher = MatchDispatcher(queue_publisher=queue_publisher)
    worker = LocalMatchExecutionWorker(dispatcher=dispatcher, event_publisher=event_publisher, league_service=league_service)
    event_publisher.subscribe(worker.handle_event)
    execution = LeagueFixtureExecutionService(dispatcher=dispatcher, event_publisher=event_publisher, execution_worker=worker)

    clubs = (
        LeagueClub(club_id=home_id, club_name="Metro FC", strength_rating=82),
        LeagueClub(club_id=away_id, club_name="River FC", strength_rating=79),
    )
    season = league_service.register_season(season_id=competition_id, buy_in_tier=25, season_start=date(2026, 3, 12), clubs=clubs)
    fixture = season.fixtures[0]
    execution.schedule_fixture(
        season_id=season.season_id,
        fixture=fixture,
        clubs=clubs,
        competition_name="GTEX League Smoke",
        club_user_ids={home_id: "user-owner", away_id: "user-away"},
        simulation_seed=1,
        reference_at=fixture.kickoff_at - timedelta(minutes=9),
    )

    replay = replay_archive.repository.get_latest_record(f"replay:{fixture.fixture_id}")
    assert replay is not None
    assert replay.timeline
