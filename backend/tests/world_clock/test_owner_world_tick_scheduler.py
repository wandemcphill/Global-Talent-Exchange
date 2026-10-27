from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.world_clock import WorldClockState
from app.owner_console.models import OwnerClubState
from app.owner_console import service as owner_service
from app.services.world_clock_service import DEFAULT_CLOCK_ID, WorldClockService

WORLD_NOW = datetime(2026, 10, 27, 12, 0, tzinfo=timezone.utc)
WORLD_DATE = WORLD_NOW.date()


def _session() -> tuple[Session, object]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[WorldClockState.__table__, OwnerClubState.__table__])
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = factory()
    session.add(
        WorldClockState(
            id=DEFAULT_CLOCK_ID,
            epoch_real_utc=WORLD_NOW,
            virtual_start_time=WORLD_NOW,
            progression_rate=1.0,
            is_paused=False,
            paused_at_virtual_time=None,
            virtual_months_per_season=12,
            metadata_json={"canonical": True},
        )
    )
    session.commit()
    return session, engine


def _state(
    session: Session,
    *,
    state_id: str,
    world_day: int,
    tick_date: date | None,
    last_tick_at: datetime | None = WORLD_NOW,
    stage: str = "active",
) -> OwnerClubState:
    state = OwnerClubState(
        id=state_id,
        club_id=f"club-{state_id}",
        owner_user_id=f"user-{state_id}",
        club_name=f"Club {state_id}",
        stage=stage,
        manager_json={},
        facilities_json={"training": 1, "academy": 1, "medical": 1},
        world_day=world_day,
        last_tick_at=last_tick_at,
        last_world_tick_date=tick_date,
        value_history_json=[],
    )
    session.add(state)
    session.commit()
    return state


def _install_fake_clock_and_tick(monkeypatch, calls: list[tuple[str, date]]) -> None:
    monkeypatch.setattr(WorldClockService, "now_virtual", lambda self: WORLD_NOW)

    def fake_tick(
        session: Session,
        state: OwnerClubState,
        use_ai: bool = True,
        *,
        world_tick_date: date | None = None,
    ) -> dict:
        assert world_tick_date is not None
        state.world_day += 1
        state.last_tick_at = WORLD_NOW
        state.last_world_tick_date = world_tick_date
        calls.append((state.club_id, world_tick_date))
        return {"world_day": state.world_day, "new_items": 0, "growth": []}

    monkeypatch.setattr(owner_service, "tick_club", fake_tick)


def test_owner_ticks_catch_up_to_world_date_and_are_idempotent(monkeypatch) -> None:
    session, engine = _session()
    calls: list[tuple[str, date]] = []
    _install_fake_clock_and_tick(monkeypatch, calls)
    state = _state(
        session,
        state_id="catch-up",
        world_day=12,
        tick_date=date(2026, 10, 24),
    )

    result = owner_service.process_due_owner_world_ticks(session, max_days_per_club=7)
    session.commit()

    assert result["target_world_date"] == "2026-10-27"
    assert result["ticks_executed"] == 3
    assert result["clubs_backlogged"] == 0
    assert calls == [
        (state.club_id, date(2026, 10, 25)),
        (state.club_id, date(2026, 10, 26)),
        (state.club_id, date(2026, 10, 27)),
    ]
    assert state.world_day == 15
    assert state.last_world_tick_date == WORLD_DATE

    second = owner_service.process_due_owner_world_ticks(session)
    session.commit()
    assert second["ticks_executed"] == 0
    assert state.world_day == 15
    assert len(calls) == 3

    session.close()
    engine.dispose()


def test_owner_tick_catch_up_is_bounded_and_reports_backlog(monkeypatch) -> None:
    session, engine = _session()
    calls: list[tuple[str, date]] = []
    _install_fake_clock_and_tick(monkeypatch, calls)
    state = _state(
        session,
        state_id="backlog",
        world_day=4,
        tick_date=date(2026, 10, 20),
    )

    result = owner_service.process_due_owner_world_ticks(session, max_days_per_club=3)
    session.commit()

    assert result["ticks_executed"] == 3
    assert result["clubs_backlogged"] == 1
    assert state.world_day == 7
    assert state.last_world_tick_date == date(2026, 10, 23)
    assert [day for _, day in calls] == [
        date(2026, 10, 21),
        date(2026, 10, 22),
        date(2026, 10, 23),
    ]

    session.close()
    engine.dispose()


def test_paused_world_clock_anchors_legacy_owner_state_without_ticking(monkeypatch) -> None:
    session, engine = _session()
    calls: list[tuple[str, date]] = []
    _install_fake_clock_and_tick(monkeypatch, calls)
    clock_state = session.get(WorldClockState, DEFAULT_CLOCK_ID)
    assert clock_state is not None
    clock_state.is_paused = True
    clock_state.paused_at_virtual_time = WORLD_NOW
    state = _state(
        session,
        state_id="legacy-paused",
        world_day=19,
        tick_date=None,
        last_tick_at=WORLD_NOW - timedelta(days=30),
    )

    result = owner_service.process_due_owner_world_ticks(session)
    session.commit()

    assert result["clock_paused"] is True
    assert result["ticks_executed"] == 0
    assert result["legacy_anchors_created"] == 1
    assert calls == []
    assert state.world_day == 19
    assert state.last_world_tick_date == WORLD_DATE

    session.close()
    engine.dispose()


def test_legacy_owner_tick_history_is_not_replayed_as_global_dates(monkeypatch) -> None:
    session, engine = _session()
    calls: list[tuple[str, date]] = []
    _install_fake_clock_and_tick(monkeypatch, calls)
    state = _state(
        session,
        state_id="legacy-active",
        world_day=31,
        tick_date=None,
        last_tick_at=WORLD_NOW - timedelta(days=90),
    )

    result = owner_service.process_due_owner_world_ticks(session)
    session.commit()

    assert result["legacy_anchors_created"] == 1
    assert result["ticks_executed"] == 0
    assert calls == []
    assert state.world_day == 31
    assert state.last_world_tick_date == WORLD_DATE

    session.close()
    engine.dispose()


def test_new_active_owner_state_gets_one_initial_tick(monkeypatch) -> None:
    session, engine = _session()
    calls: list[tuple[str, date]] = []
    _install_fake_clock_and_tick(monkeypatch, calls)
    state = _state(
        session,
        state_id="brand-new",
        world_day=0,
        tick_date=None,
        last_tick_at=None,
    )

    result = owner_service.process_due_owner_world_ticks(session)
    session.commit()

    assert result["legacy_anchors_created"] == 1
    assert result["ticks_executed"] == 1
    assert calls == [(state.club_id, WORLD_DATE)]
    assert state.world_day == 1
    assert state.last_world_tick_date == WORLD_DATE

    session.close()
    engine.dispose()
