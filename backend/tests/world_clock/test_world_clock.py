from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.models.base import Base
from app.models.world_clock import WorldClockState
from app.regen_career.policy_service import RegenCareerPolicyService
from app.regen_universe.models import RegenSeason
from app.regen_universe.service import RegenUniverseService
from app.services.world_clock_service import DEFAULT_CLOCK_ID, WorldClockService


@pytest.fixture(scope="module")
def session_factory(tmp_path_factory):
    db_file = tmp_path_factory.mktemp("world_clock") / "test_world_clock.db"
    engine = create_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    yield factory
    engine.dispose()


def test_clock_persistence_and_deterministic_progression(session_factory) -> None:
    # Session 1: initialize clock state
    with session_factory() as session:
        clock = WorldClockService(session)
        state = clock.get_or_create_state()
        assert state.id == DEFAULT_CLOCK_ID
        assert state.progression_rate == 1.0
        assert state.is_paused is False
        assert state.virtual_months_per_season == 12
        session.commit()

    # Session 2: new session/process instance reads same clock state
    with session_factory() as session:
        clock = WorldClockService(session)
        now_v = clock.now_virtual()
        assert now_v is not None
        assert now_v.tzinfo == timezone.utc
        assert isinstance(clock.now_virtual_date(), date)


def test_progression_rate_scaling(session_factory) -> None:
    with session_factory() as session:
        clock = WorldClockService(session)
        clock.get_or_create_state()

        # Manually anchor epoch 100 seconds in the past
        state = session.get(WorldClockState, DEFAULT_CLOCK_ID)
        now_real = datetime.now(timezone.utc)
        state.epoch_real_utc = now_real - timedelta(seconds=100)
        state.virtual_start_time = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        state.progression_rate = 10.0  # 10x speed
        state.is_paused = False
        state.paused_at_virtual_time = None
        session.commit()

    with session_factory() as session:
        clock = WorldClockService(session)
        v_time = clock.now_virtual()
        # 100 real seconds * 10 = ~1000 virtual seconds
        expected_min = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc) + timedelta(seconds=990)
        assert v_time >= expected_min


def test_clock_pausing_and_resumption(session_factory) -> None:
    with session_factory() as session:
        clock = WorldClockService(session)
        # Reset to 1.0x
        clock.set_rate(1.0)
        paused_state = clock.pause()
        assert paused_state.is_paused is True
        frozen_time = paused_state.paused_at_virtual_time
        assert frozen_time is not None
        session.commit()

    # In a separate session, virtual time remains frozen
    with session_factory() as session:
        clock = WorldClockService(session)
        assert clock.now_virtual() == frozen_time

        # Resume clock
        resumed_state = clock.resume()
        assert resumed_state.is_paused is False
        assert resumed_state.paused_at_virtual_time is None
        session.commit()

    with session_factory() as session:
        clock = WorldClockService(session)
        assert clock.now_virtual() >= frozen_time


def test_new_and_seeded_seasons_satisfy_virtual_age_contract(session_factory) -> None:
    with session_factory() as session:
        universe_service = RegenUniverseService(session)
        universe_service.seed_defaults()
        session.commit()

    with session_factory() as session:
        seasons = list(session.scalars(select(RegenSeason).order_by(RegenSeason.season_number.asc())).all())
        assert len(seasons) >= 1
        for s in seasons:
            meta = s.metadata_json or {}
            assert "virtual_age_month_index" in meta
            assert isinstance(meta["virtual_age_month_index"], int)

        # Create a new season explicitly
        universe_service = RegenUniverseService(session)
        max_num = max(s.season_number for s in seasons)
        new_season = universe_service.create_season(
            season_number=max_num + 1,
            start_date=date(2030, 1, 1),
            end_date=date(2030, 12, 31),
            is_active=False,
        )
        session.commit()
        assert "virtual_age_month_index" in new_season.metadata_json
        expected_index = (new_season.season_number - 1) * 12
        assert new_season.metadata_json["virtual_age_month_index"] == expected_index


def test_historical_season_backfill_and_career_policy_integration(session_factory) -> None:
    with session_factory() as session:
        # Create an unmapped legacy season
        legacy_season = RegenSeason(
            season_number=99,
            start_date=date(2099, 1, 1),
            end_date=date(2099, 12, 31),
            is_active=False,
            metadata_json={"legacy_field": "preserved"},
        )
        session.add(legacy_season)
        session.commit()

    with session_factory() as session:
        # Backfill
        clock = WorldClockService(session)
        backfilled_count = clock.backfill_existing_seasons()
        session.commit()
        assert backfilled_count >= 1

        updated = session.scalar(select(RegenSeason).where(RegenSeason.season_number == 99))
        assert updated is not None
        assert updated.metadata_json["virtual_age_month_index"] == (99 - 1) * 12
        assert updated.metadata_json["legacy_field"] == "preserved"

        # Verify career policy service mapping succeeds
        policy_service = RegenCareerPolicyService(session)
        mapping = policy_service._season_virtual_month_index()
        assert 99 in mapping
        assert mapping[99] == (99 - 1) * 12
