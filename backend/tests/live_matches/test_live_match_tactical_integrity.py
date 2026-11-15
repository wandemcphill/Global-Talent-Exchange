from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.live_matches.service import (
    LiveMatchError,
    LiveMatchHub,
    LiveMatchNotFoundError,
    LiveMatchNotLiveError,
    LiveMatchResimulationError,
    LiveMatchUnavailableError,
)
from app.models.base import Base
from app.models.competition_match import CompetitionMatch
from app.models.competition_match_event import CompetitionMatchEvent


def _database() -> tuple[object, sessionmaker[Session]]:
    from app.db import load_model_modules

    load_model_modules()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine, expire_on_commit=False)


def _insert_match(
    session_factory: sessionmaker[Session],
    *,
    match_id: str = "canonical-match-1",
    status: str = "in_progress",
    completed_at: datetime | None = None,
) -> None:
    with session_factory() as session:
        session.add(
            CompetitionMatch(
                id=match_id,
                competition_id="competition-1",
                round_id="round-1",
                round_number=1,
                home_club_id="club-home",
                away_club_id="club-away",
                status=status,
                home_score=0,
                away_score=0,
                completed_at=completed_at,
                metadata_json={"simulation_summary": {"home_score": 0, "away_score": 0}},
            )
        )
        session.commit()


@pytest.mark.parametrize("status", ["in_progress", "paused"])
def test_canonical_live_status_is_accepted_without_an_in_memory_runtime(status: str) -> None:
    engine, session_factory = _database()
    try:
        _insert_match(session_factory, status=status)
        hub = LiveMatchHub(session_factory=session_factory)

        result = hub.set_tactics(
            "canonical-match-1",
            side="home",
            formation="4-2-3-1",
            press_intensity=68,
            require_live=True,
        )

        assert result["formation"] == "4-2-3-1"
        with session_factory() as session:
            match = session.get(CompetitionMatch, "canonical-match-1")
            assert match is not None
            assert match.metadata_json["tactics"]["home"]["press_intensity"] == 68
            assert match.status == status
            assert match.completed_at is None

        # Tactical settings are recoverable after a worker/runtime reconnect.
        reconnected_hub = LiveMatchHub(session_factory=session_factory)
        recovered = reconnected_hub.get_tactics("canonical-match-1")
        assert recovered["home"]["formation"] == "4-2-3-1"
        assert recovered["home"]["press_intensity"] == 68
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    "status",
    ["scheduled", "queued", "completed", "halted", "cancelled", "postponed", "abandoned", "failed", "unknown", ""],
)
def test_live_status_whitelist_rejects_non_live_states(status: str) -> None:
    engine, session_factory = _database()
    try:
        _insert_match(session_factory, status=status)
        hub = LiveMatchHub(session_factory=session_factory)

        with pytest.raises(LiveMatchNotLiveError):
            hub.set_tactics(
                "canonical-match-1",
                side="home",
                formation="4-2-3-1",
                require_live=True,
            )

        assert hub._tactics == {}
        assert hub._matches == {}
        assert hub._hot_cache.backend.get("match:canonical-match-1:tactics") is None
        with session_factory() as session:
            match = session.get(CompetitionMatch, "canonical-match-1")
            assert match is not None
            assert "tactics" not in (match.metadata_json or {})
    finally:
        engine.dispose()


def test_completed_at_blocks_a_row_that_still_says_in_progress() -> None:
    engine, session_factory = _database()
    try:
        _insert_match(session_factory, status="in_progress", completed_at=datetime.now(UTC))
        hub = LiveMatchHub(session_factory=session_factory)
        with pytest.raises(LiveMatchNotLiveError):
            hub.set_tactics("canonical-match-1", side="home", tempo=72, require_live=True)
        assert hub._tactics == {}
    finally:
        engine.dispose()


def test_missing_canonical_match_is_rejected_without_mutation() -> None:
    engine, session_factory = _database()
    try:
        hub = LiveMatchHub(session_factory=session_factory)
        with pytest.raises(LiveMatchNotFoundError):
            hub.set_tactics("missing-match", side="home", press_intensity=61, require_live=True)
        assert hub._tactics == {}
        assert hub._matches == {}
    finally:
        engine.dispose()


def test_database_lookup_failure_returns_unavailable_and_does_not_mutate_state() -> None:
    def unavailable_session_factory():
        raise RuntimeError("database connection refused")

    hub = LiveMatchHub(session_factory=unavailable_session_factory)
    with pytest.raises(LiveMatchUnavailableError):
        hub.set_tactics(
            "canonical-match-1",
            side="home",
            formation="4-2-3-1",
            require_live=True,
        )

    assert hub._tactics == {}
    assert hub._matches == {}
    assert hub._hot_cache.backend.get("match:canonical-match-1:tactics") is None


def test_live_runtime_cannot_resimulate_against_an_unreconciled_competition_result() -> None:
    engine, session_factory = _database()
    try:
        _insert_match(session_factory, status="in_progress")
        hub = LiveMatchHub(session_factory=session_factory)
        viewer_state = object()
        event_batches = [["existing-event-batch"]]
        published_events = []
        runtime = SimpleNamespace(
            live=True,
            completed_at=None,
            last_snapshot=SimpleNamespace(status="live"),
            viewer_state=viewer_state,
            event_batches=event_batches,
            published_events=published_events,
        )
        hub._matches["canonical-match-1"] = runtime

        with pytest.raises(LiveMatchResimulationError):
            hub.set_tactics(
                "canonical-match-1",
                side="home",
                formation="3-5-2",
                mentality="attacking",
                require_live=True,
            )

        assert hub._tactics == {}
        assert hub._matches["canonical-match-1"] is runtime
        assert runtime.viewer_state is viewer_state
        assert runtime.event_batches == [["existing-event-batch"]]
        assert runtime.published_events == []
        with session_factory() as session:
            match = session.get(CompetitionMatch, "canonical-match-1")
            assert match is not None
            assert (match.home_score, match.away_score) == (0, 0)
            assert match.status == "in_progress"
            assert "tactics" not in (match.metadata_json or {})
            event_count = session.scalar(select(func.count()).select_from(CompetitionMatchEvent))
            assert event_count == 0
    finally:
        engine.dispose()


def test_halted_hub_kill_switch_rejects_tactics_before_mutation() -> None:
    engine, session_factory = _database()
    try:
        _insert_match(session_factory, status="in_progress")
        hub = LiveMatchHub(session_factory=session_factory)
        hub._halted_matches["canonical-match-1"] = {"reason": "integrity hold"}

        with pytest.raises(LiveMatchError, match="halted"):
            hub.set_tactics(
                "canonical-match-1",
                side="home",
                press_intensity=64,
                require_live=True,
            )
        assert hub._tactics == {}
    finally:
        engine.dispose()
