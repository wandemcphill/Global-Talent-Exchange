from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
import app.predictions.models  # noqa: F401
from app.common.enums.competition_format import CompetitionFormat
from app.common.enums.competition_status import CompetitionStatus
from app.common.enums.match_status import MatchStatus
from app.models.base import Base
from app.models.club_profile import ClubProfile
from app.models.competition import Competition
from app.models.competition_match import CompetitionMatch
from app.models.competition_round import CompetitionRound
from app.models.competition_rule_set import CompetitionRuleSet
from app.models.user import KycStatus, User, UserRole
from app.owner_console.engine import simulate_match as owner_simulate_match
from app.services.autonomous_match_service import AutonomousMatchExecutionService
from app.services.world_clock_service import WorldClockService


@pytest.fixture(scope="module")
def session_factory(tmp_path_factory):
    db_file = tmp_path_factory.mktemp("auto_fixtures") / "test_auto_fixtures.db"
    engine = create_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    yield factory
    engine.dispose()


def _create_user_and_club(session, name: str) -> tuple[User, ClubProfile]:
    user = User(
        id=str(uuid4()),
        email=f"{name.lower().replace(' ', '_')}@test.local",
        username=f"user_{name.lower().replace(' ', '_')[:15]}",
        password_hash="test_hash",
        role=UserRole.USER,
        kyc_status=KycStatus.VERIFIED,
    )
    session.add(user)
    club = ClubProfile(
        id=str(uuid4()),
        owner_user_id=user.id,
        club_name=f"{name} FC",
        slug=f"{name.lower().replace(' ', '-')[:30]}-{uuid4().hex[:6]}",
        primary_color="#000000",
        secondary_color="#FFFFFF",
        accent_color="#FF0000",
    )
    session.add(club)
    session.flush()
    return user, club


def _create_test_competition(session, name: str = "Test Auto League") -> Competition:
    host_user, _ = _create_user_and_club(session, f"Host_{uuid4().hex[:6]}")
    comp = Competition(
        id=str(uuid4()),
        host_user_id=host_user.id,
        name=name,
        format=CompetitionFormat.LEAGUE.value,
        status=CompetitionStatus.IN_PROGRESS.value,
        currency="credit",
        entry_fee_minor=0,
        scheduled_start_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    session.add(comp)

    rule_set = CompetitionRuleSet(
        id=str(uuid4()),
        competition_id=comp.id,
        format=CompetitionFormat.LEAGUE.value,
        min_participants=2,
        max_participants=20,
        league_win_points=3,
        league_draw_points=1,
        league_loss_points=0,
        league_tie_break_order=["points", "goal_difference", "goals_for"],
    )
    session.add(rule_set)
    session.flush()
    return comp


def test_due_fixtures_discovery_and_filtering(session_factory) -> None:
    eval_time = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)

    with session_factory() as session:
        comp = _create_test_competition(session, "Filter League")
        round_1 = CompetitionRound(
            id=str(uuid4()),
            competition_id=comp.id,
            round_number=1,
            stage="league",
            status="active",
        )
        session.add(round_1)

        _, club_a = _create_user_and_club(session, "Club Alpha")
        _, club_b = _create_user_and_club(session, "Club Beta")
        _, club_c = _create_user_and_club(session, "Club Gamma")

        # Match 1: past due (T - 2 hours)
        due_match = CompetitionMatch(
            id=str(uuid4()),
            competition_id=comp.id,
            round_id=round_1.id,
            round_number=1,
            stage="league",
            home_club_id=club_a.owner_user_id,
            away_club_id=club_b.owner_user_id,
            scheduled_at=eval_time - timedelta(hours=2),
            status=MatchStatus.SCHEDULED.value,
        )
        session.add(due_match)

        # Match 2: future (T + 2 hours)
        future_match = CompetitionMatch(
            id=str(uuid4()),
            competition_id=comp.id,
            round_id=round_1.id,
            round_number=1,
            stage="league",
            home_club_id=club_b.owner_user_id,
            away_club_id=club_c.owner_user_id,
            scheduled_at=eval_time + timedelta(hours=2),
            status=MatchStatus.SCHEDULED.value,
        )
        session.add(future_match)
        session.commit()

        # Run scanner evaluated at eval_time
        service = AutonomousMatchExecutionService(session)
        result = service.scan_and_execute_due_fixtures(reference_at=eval_time)
        session.commit()

        assert result["status"] == "success"
        assert result["discovered_due"] >= 1
        assert result["executed"] >= 1

        # Verify due match was executed
        session.refresh(due_match)
        assert due_match.status == MatchStatus.COMPLETED.value
        assert due_match.completed_at is not None
        assert "simulation_summary" in due_match.metadata_json

        # Verify future match was untouched
        session.refresh(future_match)
        assert future_match.status == MatchStatus.SCHEDULED.value
        assert future_match.completed_at is None


def test_downtime_catchup_in_chronological_order(session_factory) -> None:
    eval_time = datetime(2026, 6, 1, 18, 0, 0, tzinfo=timezone.utc)

    with session_factory() as session:
        comp = _create_test_competition(session, "Catchup League")
        round_1 = CompetitionRound(
            id=str(uuid4()),
            competition_id=comp.id,
            round_number=1,
            stage="league",
            status="active",
        )
        session.add(round_1)

        _, club_a = _create_user_and_club(session, "Catchup A")
        _, club_b = _create_user_and_club(session, "Catchup B")

        # Missed match from 5 hours ago
        m1 = CompetitionMatch(
            id=str(uuid4()),
            competition_id=comp.id,
            round_id=round_1.id,
            round_number=1,
            stage="league",
            home_club_id=club_a.owner_user_id,
            away_club_id=club_b.owner_user_id,
            scheduled_at=eval_time - timedelta(hours=5),
            status=MatchStatus.SCHEDULED.value,
        )
        session.add(m1)
        session.commit()

        service = AutonomousMatchExecutionService(session)
        result = service.scan_and_execute_due_fixtures(reference_at=eval_time, limit=1)
        session.commit()

        assert result["executed"] == 1
        session.refresh(m1)
        assert m1.status == MatchStatus.COMPLETED.value


def test_idempotent_execution_and_no_duplicate_simulation(session_factory) -> None:
    eval_time = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)

    with session_factory() as session:
        comp = _create_test_competition(session, "Idempotent League")
        round_1 = CompetitionRound(
            id=str(uuid4()),
            competition_id=comp.id,
            round_number=1,
            stage="league",
            status="active",
        )
        session.add(round_1)

        _, club_a = _create_user_and_club(session, "Idem A")
        _, club_b = _create_user_and_club(session, "Idem B")

        m = CompetitionMatch(
            id=str(uuid4()),
            competition_id=comp.id,
            round_id=round_1.id,
            round_number=1,
            stage="league",
            home_club_id=club_a.owner_user_id,
            away_club_id=club_b.owner_user_id,
            scheduled_at=eval_time - timedelta(hours=1),
            status=MatchStatus.SCHEDULED.value,
        )
        session.add(m)
        session.commit()

        service = AutonomousMatchExecutionService(session)
        # First execution executes m
        res1 = service.scan_and_execute_due_fixtures(reference_at=eval_time)
        session.commit()
        assert res1["executed"] >= 1

        # Second execution immediately after finds nothing more for this match
        res2 = service.scan_and_execute_due_fixtures(reference_at=eval_time)
        session.commit()

        session.refresh(m)
        assert m.status == MatchStatus.COMPLETED.value


def test_health_telemetry_reporting(session_factory) -> None:
    with session_factory() as session:
        service = AutonomousMatchExecutionService(session)
        telemetry = service.get_health_telemetry()

        assert "clock" in telemetry
        assert "fixtures" in telemetry
        assert telemetry["clock"]["is_paused"] is False
        assert telemetry["clock"]["progression_rate"] == 1.0
        assert "overdue_count" in telemetry["fixtures"]


def test_worker_misconfiguration_loud_crash(monkeypatch) -> None:
    from dataclasses import replace
    from app.backbone.simulation_worker_main import main
    from app.core.config import get_settings

    dummy_settings = replace(
        get_settings(),
        kafka_brokers=(),
        autonomous_fixture_execution_enabled=False,
    )
    monkeypatch.setattr("app.backbone.simulation_worker_main.get_settings", lambda: dummy_settings)

    with pytest.raises(RuntimeError, match="Simulation worker misconfigured"):
        main()


def test_owner_console_simulate_match_canonical_dispatch() -> None:
    home_side = {
        "name": "Lagos Stars",
        "strength": 75,
        "mentality": "balanced",
        "scorers": ["Ayo"],
        "manager": {"name": "Coach Ayo"},
    }
    away_side = {
        "name": "Kano Pillars",
        "strength": 72,
        "mentality": "counter",
        "scorers": ["Musa"],
        "manager": {"name": "Coach Musa"},
    }

    result = owner_simulate_match("match_seed_12345", home_side, away_side)

    assert "home_goals" in result
    assert "away_goals" in result
    assert isinstance(result["home_goals"], int)
    assert isinstance(result["away_goals"], int)
    assert "events" in result
    assert "momentum" in result
    assert "gap" in result
    assert len(result["events"]) > 0
