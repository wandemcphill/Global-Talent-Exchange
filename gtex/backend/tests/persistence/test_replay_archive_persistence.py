from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.common.enums.competition_type import CompetitionType
from app.common.enums.replay_visibility import ReplayVisibility
from app.models.base import Base
from app.replay_archive.persistence import (
    DatabaseReplayArchiveRepository,
    ReplayArchiveCountdownRow,
    ReplayArchiveRecordRow,
)
from app.replay_archive.policy import SpectatorVisibilityPolicyService
from app.replay_archive.service import ReplayArchiveService


def test_replay_archive_countdowns_round_trip_with_utc_awareness() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[ReplayArchiveRecordRow.__table__, ReplayArchiveCountdownRow.__table__])
    session_local = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    service = ReplayArchiveService(
        spectator_policy=SpectatorVisibilityPolicyService(),
        repository=DatabaseReplayArchiveRepository(session_local),
    )
    scheduled_start = datetime(2026, 3, 12, 9, 0, tzinfo=UTC)
    service.record_countdown(
        {
            "fixture_id": "fixture-final-upcoming",
            "scheduled_start": scheduled_start,
            "home_club": {"club_id": "club-home", "club_name": "Lagos Stars"},
            "away_club": {"club_id": "club-away", "club_name": "Abuja Meteors"},
            "competition_context": {
                "competition_id": "league-elite",
                "competition_type": CompetitionType.LEAGUE,
                "competition_name": "Elite League",
                "stage_name": "Final",
                "round_number": 6,
                "is_final": True,
                "competition_allows_public": False,
                "replay_visibility": ReplayVisibility.COMPETITION,
            },
        },
        recorded_at=scheduled_start - timedelta(minutes=8),
    )

    rebuilt = ReplayArchiveService(
        spectator_policy=SpectatorVisibilityPolicyService(),
        repository=DatabaseReplayArchiveRepository(session_local),
    )
    countdown = rebuilt.get_public_countdown("fixture-final-upcoming")

    assert countdown is not None
    assert countdown.scheduled_start.tzinfo is not None
    assert countdown.competition_context.featured_public is True
    assert countdown.next_notification_key in {"match_starts_10m", "match_starts_1m", "match_live_now"}

    engine.dispose()
