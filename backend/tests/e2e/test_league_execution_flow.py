from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from app.auth.service import AuthService
from app.leagues.models import LeagueClub
from app.leagues.repository import InMemoryLeagueEventRepository, get_league_event_repository
from app.leagues.service import LeagueSeasonLifecycleService
from app.main import create_app


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    club_id: str | None
    user_id: str
    headers: dict[str, str]


def _create_authenticated_user(
    app,
    *,
    club_id: str | None,
    email: str,
    username: str,
    display_name: str,
) -> AuthenticatedUser:
    with app.state.session_factory() as session:
        service = AuthService()
        user = service.register_user(
            session,
            email=email,
            username=username,
            password="SuperSecret1",
            display_name=display_name,
        )
        token, _ = service.issue_access_token(user)
        session.commit()
        session.refresh(user)
        return AuthenticatedUser(
            club_id=club_id,
            user_id=user.id,
            headers={"Authorization": f"Bearer {token}"},
        )


def test_league_fixture_dispatch_execution_replay_and_notifications_flow(tmp_path) -> None:
    repository = get_league_event_repository()
    if isinstance(repository, InMemoryLeagueEventRepository):
        repository.clear()

    database_url = f"sqlite+pysqlite:///{(tmp_path / 'league_e2e.db').as_posix()}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    app = create_app(engine=engine, run_migration_check=True)

    try:
        with TestClient(app) as client:
            assert hasattr(app.state, "league_match_execution")
            assert hasattr(app.state, "match_execution_worker")
            assert hasattr(app.state, "competition_queue_publisher")

            participants = {
                user.club_id: user
                for user in (
                    _create_authenticated_user(
                        app,
                        club_id="club-1",
                        email="club1@example.com",
                        username="club1",
                        display_name="Club One Manager",
                    ),
                    _create_authenticated_user(
                        app,
                        club_id="club-2",
                        email="club2@example.com",
                        username="club2",
                        display_name="Club Two Manager",
                    ),
                    _create_authenticated_user(
                        app,
                        club_id="club-3",
                        email="club3@example.com",
                        username="club3",
                        display_name="Club Three Manager",
                    ),
                    _create_authenticated_user(
                        app,
                        club_id="club-4",
                        email="club4@example.com",
                        username="club4",
                        display_name="Club Four Manager",
                    ),
                )
            }
            spectator = _create_authenticated_user(
                app,
                club_id=None,
                email="spectator@example.com",
                username="spectator",
                display_name="Spectator User",
            )

            clubs = (
                LeagueClub(club_id="club-1", club_name="Lagos Stars", strength_rating=88),
                LeagueClub(club_id="club-2", club_name="Abuja Meteors", strength_rating=85),
                LeagueClub(club_id="club-3", club_name="Kano Waves", strength_rating=81),
                LeagueClub(club_id="club-4", club_name="Enugu City", strength_rating=78),
            )
            league_service = LeagueSeasonLifecycleService()
            season = league_service.register_season(
                season_id="league-e2e",
                buy_in_tier=1000,
                season_start=date(2026, 3, 11),
                clubs=clubs,
            )
            fixtures = tuple(sorted(season.fixtures, key=lambda fixture: (fixture.round_number, fixture.kickoff_at)))

            for index, fixture in enumerate(fixtures, start=1):
                app.state.league_match_execution.schedule_fixture(
                    season_id=season.season_id,
                    fixture=fixture,
                    clubs=clubs,
                    competition_name="Elite League",
                    club_user_ids={club_id: user.user_id for club_id, user in participants.items()},
                    simulation_seed=index,
                    reference_at=fixture.kickoff_at - timedelta(minutes=9),
                )

            completed_state = league_service.get_season_state(season.season_id)
            assert completed_state.status == "completed"
            assert completed_state.completed_fixture_count == len(fixtures)
            assert completed_state.total_fixture_count == len(fixtures)

            settlement_events = [
                event
                for event in app.state.event_publisher.published_events
                if event.name == "competition.season.settlement.completed"
            ]
            assert len(settlement_events) == 1
            assert settlement_events[0].payload["completed_fixture_count"] == len(fixtures)

            replay_events = [
                event
                for event in app.state.event_publisher.published_events
                if event.name == "competition.replay.archived"
            ]
            assert len(replay_events) == len(fixtures)

            published_match_jobs = app.state.competition_queue_publisher.list_published("match_simulation")
            assert len(published_match_jobs) == len(fixtures)

            late_fixture_ids = {fixture.fixture_id for fixture in fixtures if fixture.round_number >= 3}
            early_fixture_ids = {fixture.fixture_id for fixture in fixtures if fixture.round_number <= 2}
            assert late_fixture_ids
            assert early_fixture_ids

            spectator_replays_response = client.get("/replays/me?limit=20", headers=spectator.headers)
            assert spectator_replays_response.status_code == 200
            spectator_replays = spectator_replays_response.json()
            assert {item["fixture_id"] for item in spectator_replays} == late_fixture_ids

            featured_response = client.get("/replays/public/featured?limit=20")
            assert featured_response.status_code == 200
            featured_replays = featured_response.json()
            assert {item["fixture_id"] for item in featured_replays} == late_fixture_ids
            assert all(item["competition_context"]["featured_public"] is True for item in featured_replays)

            public_fixture_id = next(iter(sorted(late_fixture_ids)))
            public_replay_id = f"replay:{public_fixture_id}"
            public_detail_response = client.get(f"/replays/{public_replay_id}", headers=spectator.headers)
            assert public_detail_response.status_code == 200
            public_detail = public_detail_response.json()
            assert public_detail["fixture_id"] == public_fixture_id
            assert public_detail["competition_context"]["resolved_visibility"] == "public"
            assert public_detail["timeline"]

            private_fixture_id = next(iter(sorted(early_fixture_ids)))
            private_replay_response = client.get(f"/replays/replay:{private_fixture_id}", headers=spectator.headers)
            assert private_replay_response.status_code == 404

            public_countdown_response = client.get(f"/replays/countdown/{public_fixture_id}")
            assert public_countdown_response.status_code == 200
            assert public_countdown_response.json()["state"] == "complete"

            private_countdown_response = client.get(f"/replays/countdown/{private_fixture_id}")
            assert private_countdown_response.status_code == 404

            champion = completed_state.standings[0]
            playoff_club = next(row for row in completed_state.standings if row.champions_league_playoff)

            champion_notifications_response = client.get(
                "/notifications/me?limit=100",
                headers=participants[champion.club_id].headers,
            )
            assert champion_notifications_response.status_code == 200
            champion_template_keys = {
                item["template_key"]
                for item in champion_notifications_response.json()
            }
            assert "match_starts_10m" in champion_template_keys
            assert "match_live_now" in champion_template_keys
            assert {"you_won", "you_lost"} & champion_template_keys
            assert "qualified" in champion_template_keys
            assert "qualified_champions_league" in champion_template_keys
            assert "qualified_world_super_cup" in champion_template_keys

            playoff_notifications_response = client.get(
                "/notifications/me?limit=100",
                headers=participants[playoff_club.club_id].headers,
            )
            assert playoff_notifications_response.status_code == 200
            playoff_template_keys = {
                item["template_key"]
                for item in playoff_notifications_response.json()
            }
            assert "qualified" in playoff_template_keys
            assert "reached_playoff" in playoff_template_keys
    finally:
        engine.dispose()
        if isinstance(repository, InMemoryLeagueEventRepository):
            repository.clear()
