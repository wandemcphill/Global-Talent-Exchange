from __future__ import annotations

from datetime import date, timedelta
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.common.enums.competition_type import CompetitionType
from backend.app.common.enums.fixture_window import FixtureWindow
from backend.app.common.enums.match_status import MatchStatus
from backend.app.competition_engine.match_dispatcher import MatchDispatcher
from backend.app.competition_engine.queue_contracts import InMemoryQueuePublisher, MatchSimulationJob
from backend.app.core.events import InMemoryEventPublisher
from backend.app.ingestion.models import Player
from backend.app.leagues.models import LeagueClub
from backend.app.leagues.repository import InMemoryLeagueEventRepository
from backend.app.leagues.service import LeagueSeasonLifecycleService
from backend.app.match_engine.schemas import (
    MatchEventTimelineView,
    MatchEventView,
    MatchFinalSummaryView,
    MatchPlayerReferenceView,
    MatchPlayerStatsView,
    MatchReplayPayloadView,
    MatchTeamStatsView,
    MatchTeamStrengthView,
)
from backend.app.match_engine.services import LeagueFixtureExecutionService, LocalMatchExecutionWorker
from backend.app.match_engine.services.team_factory import SyntheticSquadFactory
from backend.app.match_engine.simulation.models import MatchCompetitionType, MatchEventType, PlayerRole
from backend.app.models.base import Base
from backend.app.models.club_profile import ClubProfile
from backend.app.models.player_contract import PlayerContract
from backend.app.models.player_injury_case import PlayerInjuryCase
from backend.app.models.player_lifecycle_event import PlayerLifecycleEvent
from backend.app.models.user import KycStatus, User, UserRole
from backend.app.notifications.service import NotificationCenter
from backend.app.replay_archive.persistence import InMemoryReplayArchiveRepository
from backend.app.replay_archive.policy import SpectatorVisibilityPolicyService
from backend.app.replay_archive.service import ReplayArchiveService


def test_local_execution_worker_runs_league_pipeline_end_to_end() -> None:
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
    worker = LocalMatchExecutionWorker(
        dispatcher=dispatcher,
        event_publisher=event_publisher,
        league_service=league_service,
    )
    event_publisher.subscribe(worker.handle_event)
    execution = LeagueFixtureExecutionService(
        dispatcher=dispatcher,
        event_publisher=event_publisher,
        execution_worker=worker,
    )

    clubs = (
        LeagueClub(club_id="club-home", club_name="Home Stars", strength_rating=84),
        LeagueClub(club_id="club-away", club_name="Away Meteors", strength_rating=78),
    )
    season = league_service.register_season(
        season_id="league-runtime",
        buy_in_tier=300,
        season_start=date(2026, 3, 11),
        clubs=clubs,
    )

    fixtures = tuple(sorted(season.fixtures, key=lambda fixture: fixture.round_number))
    for index, fixture in enumerate(fixtures, start=1):
        execution.schedule_fixture(
            season_id=season.season_id,
            fixture=fixture,
            clubs=clubs,
            competition_name="Runtime League",
            club_user_ids={
                "club-home": "user-home",
                "club-away": "user-away",
            },
            simulation_seed=index,
            reference_at=fixture.kickoff_at - timedelta(minutes=9),
        )

    completed_state = league_service.get_season_state(season.season_id)
    assert completed_state.status == "completed"
    assert completed_state.completed_fixture_count == len(fixtures)
    assert len(queue_publisher.list_published("match_simulation")) == len(fixtures)

    home_replays = replay_archive.list_for_user("user-home", limit=10)
    assert {item.fixture_id for item in home_replays} == {fixture.fixture_id for fixture in fixtures}

    latest_replay = replay_archive.repository.get_latest_record(f"replay:{fixtures[-1].fixture_id}")
    assert latest_replay is not None
    assert latest_replay.competition_context.presentation_duration_minutes in {3, 4, 5}
    assert latest_replay.timeline

    home_notifications = notifications.list_for_user("user-home", limit=20)
    template_keys = {item.template_key for item in home_notifications}
    assert "match_starts_10m" in template_keys
    assert "match_live_now" in template_keys
    assert {"you_won", "you_lost"} & template_keys
    assert "qualified" in template_keys

    settlement_events = [
        event
        for event in event_publisher.published_events
        if event.name == "competition.season.settlement.completed"
    ]
    assert len(settlement_events) == 1
    assert settlement_events[0].payload["status"] == "completed"
