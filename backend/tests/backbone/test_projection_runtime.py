from __future__ import annotations

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.backbone.kafka import KafkaMessage
from app.backbone.projection_runtime import ProjectionWorkerService
from app.core.database import ensure_database_schema_current
from app.models.notification_record import NotificationRecord
from app.models.projections import CompetitionStandingProjection, PlayerStatsProjection, ProjectionEventReceipt
from app.models.story_feed import StoryFeedItem


class FakeKafkaConsumer:
    def __init__(self, *batches: list[KafkaMessage]) -> None:
        self._batches = list(batches)
        self.commit_calls = 0
        self.closed = False

    def poll(self) -> list[KafkaMessage]:
        if not self._batches:
            return []
        return self._batches.pop(0)

    def commit(self) -> None:
        self.commit_calls += 1

    def close(self) -> None:
        self.closed = True


def _build_session_factory(tmp_path):
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'projection-runtime.db').as_posix()}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    ensure_database_schema_current(engine)
    return engine, sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def test_projection_worker_materializes_match_completed_events_once(tmp_path) -> None:
    engine, session_factory = _build_session_factory(tmp_path)

    envelope = {
        "event_id": "f32cb422-fefd-4eb0-b49e-06d1e75cb66a",
        "event_type": "match.completed",
        "aggregate_id": "fixture-500",
        "aggregate_type": "fixture",
        "version": 1,
        "timestamp": "2026-03-27T12:00:00+00:00",
        "producer": "simulation-service",
        "partition_key": "fixture-500",
        "payload": {
            "competition_id": "league-alpha",
            "season_id": "season-2026",
            "competition_type": "league",
            "fixture_id": "fixture-500",
            "home_club_id": "club-home",
            "home_club_name": "North City",
            "away_club_id": "club-away",
            "away_club_name": "South Town",
            "home_goals": 2,
            "away_goals": 1,
            "winner_team_id": "club-home",
            "is_final": False,
            "user_ids": ["user-1", "user-2"],
            "player_stats": [
                {
                    "player_id": "player-home-9",
                    "player_name": "Home Nine",
                    "team_id": "club-home",
                    "team_name": "North City",
                    "started": True,
                    "minutes_played": 90,
                    "goals": 1,
                    "assists": 1,
                    "saves": 0,
                    "yellow_cards": 0,
                    "red_card": False,
                    "xg": 0.84,
                    "rating": 8.3,
                },
                {
                    "player_id": "player-away-1",
                    "player_name": "Away Keeper",
                    "team_id": "club-away",
                    "team_name": "South Town",
                    "started": True,
                    "minutes_played": 90,
                    "goals": 0,
                    "assists": 0,
                    "saves": 4,
                    "yellow_cards": 1,
                    "red_card": False,
                    "xg": 0.0,
                    "rating": 6.9,
                },
            ],
        },
        "headers": {},
    }
    message = KafkaMessage(
        topic="gtex.match.completed",
        key="fixture-500",
        value=envelope,
        headers={"event_type": "match.completed"},
    )
    consumer = FakeKafkaConsumer([message], [message])
    service = ProjectionWorkerService(session_factory=session_factory, consumer=consumer)

    assert service.poll_once() == 1
    assert service.poll_once() == 1
    assert consumer.commit_calls == 2

    with session_factory() as session:
        standings = list(
            session.scalars(
                select(CompetitionStandingProjection).order_by(CompetitionStandingProjection.club_id.asc())
            ).all()
        )
        assert len(standings) == 2
        assert standings[0].club_id == "club-away"
        assert standings[0].matches_played == 1
        assert standings[0].losses == 1
        assert standings[0].points == 0
        assert standings[1].club_id == "club-home"
        assert standings[1].matches_played == 1
        assert standings[1].wins == 1
        assert standings[1].points == 3
        assert standings[1].goals_for == 2
        assert standings[1].goals_against == 1

        player_rows = list(session.scalars(select(PlayerStatsProjection).order_by(PlayerStatsProjection.player_id.asc())).all())
        assert len(player_rows) == 2
        assert player_rows[0].player_id == "player-away-1"
        assert player_rows[0].appearances == 1
        assert player_rows[0].saves == 4
        assert player_rows[0].yellow_cards == 1
        assert player_rows[0].losses == 1
        assert player_rows[1].player_id == "player-home-9"
        assert player_rows[1].appearances == 1
        assert player_rows[1].goals == 1
        assert player_rows[1].assists == 1
        assert player_rows[1].wins == 1

        receipts = list(session.scalars(select(ProjectionEventReceipt)).all())
        assert len(receipts) == 3

        stories = list(session.scalars(select(StoryFeedItem)).all())
        assert len(stories) == 1
        assert stories[0].story_type == "match_completed"
        assert stories[0].subject_id == "fixture-500"

        notifications = list(session.scalars(select(NotificationRecord).order_by(NotificationRecord.user_id.asc())).all())
        assert len(notifications) == 2
        assert notifications[0].user_id == "user-1"
        assert notifications[1].user_id == "user-2"

    engine.dispose()
