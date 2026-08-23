"""Phase B regression tests for the match execution runtime.

These cover the lifecycle guarantees that the runtime previously did not hold:

1. A simulated result is durably persisted *and* linked to its replay before any
   advancement, notification or settlement job is dispatched.
2. A persistence failure aborts the pipeline instead of being swallowed, and releases
   the execution claim so the job can be retried.
3. A settled, abandoned or cancelled match can never be re-settled by a duplicate or
   late worker.
4. Live stream frames carry a monotonic, minute-ordered sequence so consumers can
   order, de-duplicate and resume the stream.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.common.enums.competition_type import CompetitionType
from app.common.enums.fixture_window import FixtureWindow
from app.common.enums.match_status import MatchStatus
from app.competition_engine.match_dispatcher import MatchDispatcher
from app.competition_engine.queue_contracts import InMemoryQueuePublisher, MatchSimulationJob
from app.core.events import InMemoryEventPublisher
from app.match_engine.services.execution_runtime import (
    LocalMatchExecutionWorker,
    MatchResultPersistenceError,
)
from app.match_engine.services.team_factory import SyntheticSquadFactory
from app.models.base import Base
from app.models.competition_match import CompetitionMatch

FIXTURE_ID = "fixture-hardening-1"
COMPETITION_ID = "competition-hardening-1"


def _session_factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # The runtime also writes player lifecycle incidents, so the full schema is needed.
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def _seed_match(factory: sessionmaker[Session], *, status: str = "queued", **overrides: Any) -> None:
    with factory() as session:
        session.add(
            CompetitionMatch(
                id=FIXTURE_ID,
                competition_id=COMPETITION_ID,
                round_id="round-1",
                round_number=1,
                home_club_id="club-home",
                away_club_id="club-away",
                status=status,
                metadata_json={},
                **overrides,
            )
        )
        session.commit()


@dataclass(slots=True)
class _ExplodingPersistenceWorker(LocalMatchExecutionWorker):
    """Worker whose result persistence always fails."""

    def _persist_match_viewer_payload(self, job, replay_payload) -> None:  # type: ignore[override]
        raise RuntimeError("database is gone")


@dataclass(slots=True)
class _FlakyPersistenceWorker(LocalMatchExecutionWorker):
    """Worker whose result persistence fails once, then succeeds."""

    attempts: int = 0

    def _persist_match_viewer_payload(self, job, replay_payload) -> None:  # type: ignore[override]
        self.attempts += 1
        if self.attempts == 1:
            raise RuntimeError("transient write failure")
        super()._persist_match_viewer_payload(job, replay_payload)


@dataclass(slots=True)
class _FixedTimelineWorker(LocalMatchExecutionWorker):
    """Worker returning a hand-built timeline that straddles the id-padding boundary."""

    def _build_replay_timeline(self, replay_payload) -> list[dict[str, Any]]:  # type: ignore[override]
        return [
            {"event_id": "m:0999", "minute": 40, "event_type": "goals", "home_score": 1, "away_score": 0},
            {"event_id": "m:1000", "minute": 40, "event_type": "goals", "home_score": 2, "away_score": 0},
            {"event_id": "m:1001", "minute": 41, "event_type": "yellow_cards", "home_score": 2, "away_score": 0},
        ]


def _build_worker(
    factory: sessionmaker[Session] | None,
    *,
    worker_cls: type[LocalMatchExecutionWorker] = LocalMatchExecutionWorker,
) -> tuple[LocalMatchExecutionWorker, InMemoryEventPublisher, InMemoryQueuePublisher]:
    event_publisher = InMemoryEventPublisher()
    queue_publisher = InMemoryQueuePublisher(event_publisher=event_publisher)
    worker = worker_cls(
        dispatcher=MatchDispatcher(queue_publisher=queue_publisher),
        event_publisher=event_publisher,
        session_factory=factory,
        team_factory=SyntheticSquadFactory(allow_synthetic_fallback=True),
        # Keep the live pacing loop out of the test; it is wall-clock only.
        stream_update_interval_seconds=0.0,
    )
    return worker, event_publisher, queue_publisher


def _job(**overrides: Any) -> MatchSimulationJob:
    payload: dict[str, Any] = {
        "fixture_id": FIXTURE_ID,
        "competition_id": COMPETITION_ID,
        "competition_type": CompetitionType.CHAMPIONS_LEAGUE,
        "match_date": date(2026, 4, 2),
        "window": FixtureWindow.SENIOR_1,
        "home_club_id": "club-home",
        "home_club_name": "Home Stars",
        "home_strength_rating": 82,
        "away_club_id": "club-away",
        "away_club_name": "Away Meteors",
        "away_strength_rating": 78,
        "simulation_seed": 7,
        "is_cup_match": True,
        "round_number": 2,
    }
    payload.update(overrides)
    return MatchSimulationJob.model_validate(payload)


def test_simulation_settles_the_match_row_and_links_it_to_the_replay() -> None:
    factory = _session_factory()
    _seed_match(factory)
    worker, _publisher, _queue = _build_worker(factory)

    replay = worker.execute_match_simulation(_job())
    assert replay is not None

    with factory() as session:
        match = session.get(CompetitionMatch, FIXTURE_ID)
        assert match is not None
        assert match.status == MatchStatus.COMPLETED.value
        assert match.completed_at is not None
        assert (match.home_score, match.away_score) == (
            replay.summary.home_score,
            replay.summary.away_score,
        )
        metadata = match.metadata_json or {}
        # Replay and result must remain linked on the same row.
        assert metadata["replay_id"] == "replay:" + FIXTURE_ID
        assert metadata["simulation_seed"] == replay.seed
        assert metadata["replay_payload"]["match_id"] == replay.match_id
        assert metadata["simulation_summary"]["home_score"] == replay.summary.home_score


def test_persistence_failure_aborts_before_advancement_and_settlement() -> None:
    """A failed result write must not let advancement or settlement be dispatched."""
    factory = _session_factory()
    _seed_match(factory)
    worker, event_publisher, queue_publisher = _build_worker(factory, worker_cls=_ExplodingPersistenceWorker)

    with pytest.raises(RuntimeError, match="database is gone"):
        worker.execute_match_simulation(_job())

    assert not queue_publisher.list_published("bracket_advancement")
    assert not queue_publisher.list_published("payout_settlement")

    published = {event.name for event in event_publisher.published_events}
    assert "competition.match.execution.failed" in published
    assert "competition.match.result.generated" not in published
    assert "competition.replay.archived" not in published

    with factory() as session:
        match = session.get(CompetitionMatch, FIXTURE_ID)
        assert match.status == MatchStatus.QUEUED.value
        assert match.completed_at is None


def test_failed_execution_releases_the_claim_so_a_retry_can_succeed() -> None:
    factory = _session_factory()
    _seed_match(factory)
    worker, _publisher, _queue = _build_worker(factory, worker_cls=_FlakyPersistenceWorker)

    with pytest.raises(RuntimeError, match="transient write failure"):
        worker.execute_match_simulation(_job())

    # The retry must not be swallowed by the in-memory duplicate-execution claim.
    replay = worker.execute_match_simulation(_job())
    assert replay is not None
    assert worker.attempts == 2  # type: ignore[attr-defined]

    with factory() as session:
        assert session.get(CompetitionMatch, FIXTURE_ID).status == MatchStatus.COMPLETED.value


def test_duplicate_simulation_of_a_settled_match_does_not_re_settle_it() -> None:
    """A second worker (or a restarted process) must not overwrite a settled result."""
    factory = _session_factory()
    _seed_match(
        factory,
        status=MatchStatus.COMPLETED.value,
        home_score=4,
        away_score=0,
        winner_club_id="club-home",
    )
    worker, _publisher, queue_publisher = _build_worker(factory)

    with pytest.raises(MatchResultPersistenceError, match="already settled"):
        worker.execute_match_simulation(_job())

    assert not queue_publisher.list_published("bracket_advancement")
    with factory() as session:
        match = session.get(CompetitionMatch, FIXTURE_ID)
        assert (match.home_score, match.away_score) == (4, 0)
        assert match.winner_club_id == "club-home"


def test_abandoned_match_cannot_be_settled_by_a_late_worker() -> None:
    factory = _session_factory()
    _seed_match(factory, status=MatchStatus.ABANDONED.value)
    worker, _publisher, queue_publisher = _build_worker(factory)

    with pytest.raises(MatchResultPersistenceError, match="abandoned"):
        worker.execute_match_simulation(_job())

    assert not queue_publisher.list_published("bracket_advancement")
    with factory() as session:
        match = session.get(CompetitionMatch, FIXTURE_ID)
        assert match.status == MatchStatus.ABANDONED.value
        assert (match.home_score, match.away_score) == (0, 0)
        assert match.completed_at is None


def test_cancelled_match_cannot_be_settled_by_a_late_worker() -> None:
    factory = _session_factory()
    _seed_match(factory, status=MatchStatus.CANCELLED.value)
    worker, _publisher, _queue = _build_worker(factory)

    with pytest.raises(MatchResultPersistenceError, match="cancelled"):
        worker.execute_match_simulation(_job())


def test_live_frames_carry_a_monotonic_minute_ordered_sequence() -> None:
    worker, _publisher, _queue = _build_worker(None)
    job = _job()
    replay = worker.match_service.build_replay_payload(worker.team_factory.build_request(job))

    frames = worker._build_live_stream_frames(job, replay)

    sequences = [frame["sequence"] for frame in frames]
    assert sequences == list(range(1, len(frames) + 1)), "sequence must be dense and monotonic"

    minutes = [int(frame.get("minute") or 0) for frame in frames[:-1]]
    assert minutes == sorted(minutes), "frames must be emitted in minute order"

    assert len({frame["event_id"] for frame in frames}) == len(frames), "event ids must be unique"
    assert frames[0]["event_type"] == "kickoff"
    assert frames[-1]["event_type"] == "full_time"
    assert frames[-1]["status"] == "completed"


def test_live_frames_stay_ordered_past_the_zero_padded_event_id_boundary() -> None:
    """Ordering must not depend on a lexicographic event_id sort.

    Event ids are ``{match_id}:{sequence:03d}``; once the sequence passes 999 the string
    ``"...:1000"`` sorts *before* ``"...:0999"`` only by luck of padding, and any
    unpadded id reorders same-minute events outright.
    """
    worker, _publisher, _queue = _build_worker(None, worker_cls=_FixedTimelineWorker)
    job = _job()
    replay = worker.match_service.build_replay_payload(worker.team_factory.build_request(job))

    frames = worker._build_live_stream_frames(job, replay)
    emitted = [frame["event_id"] for frame in frames if str(frame["event_id"]).startswith("m:")]
    assert emitted == ["m:0999", "m:1000", "m:1001"]


def test_cached_stream_payloads_round_trip_through_the_live_view_schemas() -> None:
    """The cache feeds the spectator API directly, and those schemas forbid extra keys.

    A frame field the view does not declare makes ``LiveMatchHub.get_state`` fail
    validation and return ``None``, silently blanking the live match for every viewer.
    """
    from app.live_matches.schemas import LiveMatchStateView, LiveMatchStreamEventView

    worker, _publisher, _queue = _build_worker(None)
    job = _job()
    replay = worker.match_service.build_replay_payload(worker.team_factory.build_request(job))
    frames = worker._build_live_stream_frames(job, replay)

    for index, frame in enumerate(frames, start=1):
        event = LiveMatchStreamEventView.model_validate(
            worker._build_cached_live_event(match_id=FIXTURE_ID, frame=frame)
        )
        assert event.sequence == index

        state = LiveMatchStateView.model_validate(
            worker._build_cached_match_state(
                match_id=FIXTURE_ID,
                home_team_name="Home Stars",
                away_team_name="Away Meteors",
                frame=frame,
                event_count=index,
            )
        )
        assert state.last_sequence == index


def test_a_scheduled_fixture_is_settled_by_the_worker() -> None:
    """Rows still at the model default status must not be rejected by the guard."""
    factory = _session_factory()
    _seed_match(factory, status=MatchStatus.SCHEDULED.value)
    worker, _publisher, _queue = _build_worker(factory)

    replay = worker.execute_match_simulation(_job())
    assert replay is not None

    with factory() as session:
        match = session.get(CompetitionMatch, FIXTURE_ID)
        assert match.status == MatchStatus.COMPLETED.value
        assert match.completed_at is not None
