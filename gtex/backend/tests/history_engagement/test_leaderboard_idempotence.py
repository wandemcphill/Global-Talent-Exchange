from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.history_engagement.service import HistoryEngagementService
from app.models.base import Base
from app.models.history_engagement import HistoricalLeaderboardEntry


def test_leaderboard_generation_updates_existing_rows_on_duplicate() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[HistoricalLeaderboardEntry.__table__])
    session_local = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with session_local() as session:
        service = HistoryEngagementService(session)
        original = HistoricalLeaderboardEntry(
            board_key="top_players_ever",
            entity_type="player",
            entity_id="player-1",
            entity_name="Old Name",
            rank=99,
            score=1,
            score_breakdown_json={"old": True},
            generated_at=datetime.now(UTC) - timedelta(days=1),
            metadata_json={"version": "old"},
        )
        replacement = HistoricalLeaderboardEntry(
            board_key="top_players_ever",
            entity_type="player",
            entity_id="player-1",
            entity_name="Ayo Ade",
            rank=1,
            score=432.5,
            score_breakdown_json={"goals": 88},
            generated_at=datetime.now(UTC),
            metadata_json={"version": "new"},
        )

        service._upsert_leaderboard_entries([original])
        service._upsert_leaderboard_entries([replacement])
        session.flush()

        rows = session.scalars(
            select(HistoricalLeaderboardEntry).where(
                HistoricalLeaderboardEntry.board_key == "top_players_ever",
                HistoricalLeaderboardEntry.entity_id == "player-1",
            )
        ).all()
        assert len(rows) == 1
        assert rows[0].entity_name == "Ayo Ade"
        assert rows[0].rank == 1
        assert rows[0].score == 432.5
        assert rows[0].score_breakdown_json == {"goals": 88}
        assert rows[0].metadata_json == {"version": "new"}
    engine.dispose()
