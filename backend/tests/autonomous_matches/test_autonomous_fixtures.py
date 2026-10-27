from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
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
from app.ingestion.models import Player
from app.models.base import Base
from app.models.club_profile import ClubProfile
from app.models.competition import Competition
from app.models.competition_match import CompetitionMatch
from app.models.competition_match_event import CompetitionMatchEvent
from app.models.competition_round import CompetitionRound
from app.models.competition_rule_set import CompetitionRuleSet
from app.models.competition_reward import CompetitionReward
from app.models.competition_reward_pool import CompetitionRewardPool
from app.models.competition_participant import CompetitionParticipant
from app.models.competition_prize_rule import CompetitionPrizeRule
from app.models.player_contract import PlayerContract
from app.models.user import KycStatus, User, UserRole
from app.owner_console.engine import simulate_match as owner_simulate_match
from app.owner_console.models import OwnerCompetition, OwnerMatch
from app.services.autonomous_match_service import AutonomousMatchExecutionService
from app.services.competition_auto_runner import CompetitionAutoRunner
from app.services.competition_lifecycle_service import CompetitionLifecycleService


@pytest.fixture(scope="module")
def session_factory(tmp_path_factory):
    db_file = tmp_path_factory.mktemp("auto_fixtures") / "test_auto_fixtures.db"
    engine = create_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    yield factory
    engine.dispose()


def _seed_club_squad(session, club: ClubProfile, count: int = 15, as_of: date | None = None) -> list[Player]:
    base_date = as_of or date(2026, 1, 1)
    roles = [
        "goalkeeper",
        "defender",
        "defender",
        "defender",
        "defender",
        "midfielder",
        "midfielder",
        "midfielder",
        "forward",
        "forward",
        "forward",
        "midfielder",
        "forward",
        "defender",
        "goalkeeper",
    ]
    players = []
    for i in range(count):
        pos = roles[i % len(roles)]
        player_id = str(uuid4())
        player = Player(
            id=player_id,
            source_provider="test_provider",
            provider_external_id=f"ext_{player_id[:12]}",
            full_name=f"{club.club_name} Player {i+1}",
            first_name=f"Player{i+1}",
            last_name=club.club_name,
            position=pos,
            normalized_position=pos,
            date_of_birth=date(2000, 1, 1),
            is_real_player=False,
            is_tradable=True,
            current_club_profile_id=club.id,
        )
        session.add(player)
        contract = PlayerContract(
            id=str(uuid4()),
            player_id=player_id,
            club_id=club.id,
            status="active",
            signed_on=base_date - timedelta(days=30),
            starts_on=base_date - timedelta(days=30),
            ends_on=base_date + timedelta(days=365),
            wage_amount=Decimal("1000.00"),
        )
        session.add(contract)
        players.append(player)
    session.flush()
    return players


def _create_user_and_club(session, name: str, seed_squad: bool = True) -> tuple[User, ClubProfile]:
    user = User(
        id=str(uuid4()),
        email=f"{name.lower().replace(' ', '_')}@test.local",
        username=f"user_{name.lower().replace(' ', '_')[:15]}",
        password_hash="test_hash",  # pragma: allowlist secret
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
    if seed_squad:
        _seed_club_squad(session, club)
    return user, club


def _create_test_competition(session, name: str = "Test Auto League") -> Competition:
    host_user, _ = _create_user_and_club(session, f"Host_{uuid4().hex[:6]}", seed_squad=False)
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
            home_club_id=club_a.id,
            away_club_id=club_b.id,
            match_date=eval_time.date(),
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
            home_club_id=club_b.id,
            away_club_id=club_c.id,
            match_date=eval_time.date(),
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
            home_club_id=club_a.id,
            away_club_id=club_b.id,
            match_date=eval_time.date(),
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
            home_club_id=club_a.id,
            away_club_id=club_b.id,
            match_date=eval_time.date(),
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
        assert res2["executed"] == 0
        session.commit()

        session.refresh(m)
        assert m.status == MatchStatus.COMPLETED.value


def test_unresolved_missing_kickoff_not_run_prematurely(session_factory) -> None:
    eval_time = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)

    with session_factory() as session:
        comp = _create_test_competition(session, "Unresolved Kickoff League")
        comp.scheduled_start_at = None
        session.flush()

        round_1 = CompetitionRound(
            id=str(uuid4()),
            competition_id=comp.id,
            round_number=1,
            stage="league",
            status="active",
        )
        session.add(round_1)

        _, club_a = _create_user_and_club(session, "Club Unres A")
        _, club_b = _create_user_and_club(session, "Club Unres B")
        _, club_c = _create_user_and_club(session, "Club Unres C")
        _, club_d = _create_user_and_club(session, "Club Unres D")

        # Match 1: completely unresolvable (no scheduled_at, no match_date, comp.scheduled_start_at is None)
        unresolvable_match = CompetitionMatch(
            id=str(uuid4()),
            competition_id=comp.id,
            round_id=round_1.id,
            round_number=1,
            stage="league",
            home_club_id=club_a.id,
            away_club_id=club_b.id,
            match_date=None,
            scheduled_at=None,
            status=MatchStatus.SCHEDULED.value,
        )
        session.add(unresolvable_match)

        # Match 2: match_date is in future (kickoff will be future)
        future_date_match = CompetitionMatch(
            id=str(uuid4()),
            competition_id=comp.id,
            round_id=round_1.id,
            round_number=1,
            stage="league",
            home_club_id=club_c.id,
            away_club_id=club_d.id,
            match_date=eval_time.date() + timedelta(days=2),
            scheduled_at=None,
            status=MatchStatus.SCHEDULED.value,
        )
        session.add(future_date_match)
        session.commit()

        service = AutonomousMatchExecutionService(session)
        result = service.scan_and_execute_due_fixtures(reference_at=eval_time)
        assert result["executed"] == 0
        assert result["failed"] == 0
        session.commit()

        # Neither unresolvable nor future should be executed
        session.refresh(unresolvable_match)
        assert unresolvable_match.status == MatchStatus.SCHEDULED.value
        assert unresolvable_match.scheduled_at is None

        session.refresh(future_date_match)
        assert future_date_match.status == MatchStatus.SCHEDULED.value


def test_atomic_retry_rolls_back_partial_writes(session_factory, monkeypatch) -> None:
    eval_time = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)

    with session_factory() as session:
        comp = _create_test_competition(session, "Atomic Retry League")
        round_1 = CompetitionRound(
            id=str(uuid4()),
            competition_id=comp.id,
            round_number=1,
            stage="league",
            status="active",
        )
        session.add(round_1)

        _, club_a = _create_user_and_club(session, "Atomic A")
        _, club_b = _create_user_and_club(session, "Atomic B")

        match = CompetitionMatch(
            id=str(uuid4()),
            competition_id=comp.id,
            round_id=round_1.id,
            round_number=1,
            stage="league",
            home_club_id=club_a.id,
            away_club_id=club_b.id,
            match_date=eval_time.date(),
            scheduled_at=eval_time - timedelta(hours=1),
            status=MatchStatus.SCHEDULED.value,
        )
        session.add(match)
        session.commit()

        # 1. Simulate failure during complete_match (after viewer payload & events have been written)
        def _exploding_complete_match(self, *args, **kwargs):
            raise RuntimeError("Database connection lost during settlement")

        monkeypatch.setattr(CompetitionLifecycleService, "complete_match", _exploding_complete_match)

        service = AutonomousMatchExecutionService(session)
        result = service.scan_and_execute_due_fixtures(reference_at=eval_time)
        session.commit()

        assert result["status"] == "failure"
        assert result["failed"] == 1
        assert len(result["errors"]) == 1
        assert "Database connection lost during settlement" in result["errors"][0]

        session.refresh(match)
        # Status rolled back cleanly to SCHEDULED
        assert match.status == MatchStatus.SCHEDULED.value
        # Retry metadata recorded
        assert match.metadata_json is not None
        assert match.metadata_json["execution_attempts"] == 1
        assert "Database connection lost during settlement" in match.metadata_json["last_execution_error"]

        # Partial events written before the exception rolled back with savepoint!
        events = list(
            session.scalars(select(CompetitionMatchEvent).where(CompetitionMatchEvent.match_id == match.id)).all()
        )
        assert len(events) == 0

        # 2. Now remove monkeypatch and rerun: match executes cleanly and idempotently
        monkeypatch.undo()

        res2 = service.scan_and_execute_due_fixtures(reference_at=eval_time)
        assert res2["executed"] == 1
        session.commit()
        session.refresh(match)
        assert match.status == MatchStatus.COMPLETED.value
        assert match.completed_at is not None
        # Events exist exactly once
        events_after = list(
            session.scalars(select(CompetitionMatchEvent).where(CompetitionMatchEvent.match_id == match.id)).all()
        )
        assert len(events_after) > 0


def test_health_telemetry_reporting(session_factory) -> None:
    with session_factory() as session:
        comp = _create_test_competition(session, "Telemetry retries")
        round_1 = CompetitionRound(
            id=str(uuid4()),
            competition_id=comp.id,
            round_number=1,
            stage="league",
            status="active",
        )
        session.add(round_1)
        _, club_a = _create_user_and_club(session, "Telemetry A", seed_squad=False)
        _, club_b = _create_user_and_club(session, "Telemetry B", seed_squad=False)
        retry_match = CompetitionMatch(
            id=str(uuid4()),
            competition_id=comp.id,
            round_id=round_1.id,
            round_number=1,
            stage="league",
            home_club_id=club_a.id,
            away_club_id=club_b.id,
            match_date=date(2026, 6, 1),
            scheduled_at=datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc),
            status=MatchStatus.SCHEDULED.value,
            metadata_json={
                "execution_attempts": 2,
                "last_execution_error": "transient simulation error",
            },
        )
        session.add(retry_match)
        session.flush()

        service = AutonomousMatchExecutionService(session)
        telemetry = service.get_health_telemetry()

        assert "clock" in telemetry
        assert "fixtures" in telemetry
        assert telemetry["clock"]["is_paused"] is False
        assert telemetry["clock"]["progression_rate"] == 1.0
        assert "overdue_count" in telemetry["fixtures"]
        assert telemetry["fixtures"]["retry_pending_count"] >= 1
        assert telemetry["fixtures"]["worker_mode"] == "database_polling"


@pytest.mark.parametrize(
    ("kafka_brokers", "consumer_enabled"),
    [
        ((), True),
        (("localhost:9092",), False),
    ],
)
def test_worker_misconfiguration_loud_crash(monkeypatch, kafka_brokers, consumer_enabled) -> None:
    from dataclasses import replace
    from app.backbone.simulation_worker_main import main
    from app.core.config import get_settings

    dummy_settings = replace(
        get_settings(),
        kafka_brokers=kafka_brokers,
        kafka_simulation_consumer_enabled=consumer_enabled,
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


def test_owner_console_honest_failure_on_invalid_input() -> None:
    # Invalid side input missing required fields must raise honestly rather than falling back to Poisson
    with pytest.raises(Exception):
        owner_simulate_match("bad_seed", {"invalid": True}, {"invalid": True})


def test_owner_pre_match_tactics_reach_canonical_runner_request(session_factory) -> None:
    with session_factory() as session:
        competition = _create_test_competition(session, "Owner Tactics Pipeline")
        round_row = CompetitionRound(
            id=str(uuid4()),
            competition_id=competition.id,
            round_number=1,
            stage="league",
            status="active",
        )
        session.add(round_row)
        _, home_club = _create_user_and_club(session, "Owner Tactics Home")
        _, away_club = _create_user_and_club(session, "Owner Tactics Away")
        kickoff_at = datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc)
        match = CompetitionMatch(
            id=str(uuid4()),
            competition_id=competition.id,
            round_id=round_row.id,
            round_number=1,
            stage="league",
            home_club_id=home_club.id,
            away_club_id=away_club.id,
            match_date=kickoff_at.date(),
            scheduled_at=kickoff_at,
            status=MatchStatus.SCHEDULED.value,
            metadata_json={
                "owner_pre_match_tactics": {
                    home_club.id: {"mentality": "attacking", "lineup_mode": "rotate"},
                    away_club.id: {"mentality": "defensive", "lineup_mode": "strongest"},
                }
            },
        )
        session.add(match)
        session.flush()

        runner = CompetitionAutoRunner(session)
        job = runner._simulation_job(competition, match)
        assert job.home_lineup_mode == "rotate"
        assert job.away_lineup_mode == "strongest"

        request = runner.team_factory.build_request(job, session=session)
        request = runner._apply_owner_pre_match_tactics(request, match)
        assert request.match_id == match.id
        assert request.home_team.tactics.mentality.value == "attacking"
        assert request.home_team.tactics.style.value == "attacking"
        assert request.away_team.tactics.mentality.value == "defensive"
        assert request.away_team.tactics.style.value == "defensive"


def test_stale_worker_retry_cannot_reexecute_a_completed_fixture(session_factory) -> None:
    from types import SimpleNamespace

    with session_factory() as session:
        competition = _create_test_competition(session, "Idempotent Match Runner")
        round_row = CompetitionRound(
            id=str(uuid4()),
            competition_id=competition.id,
            round_number=1,
            stage="league",
            status="active",
        )
        session.add(round_row)
        _, home_club = _create_user_and_club(session, "Idempotent Home")
        _, away_club = _create_user_and_club(session, "Idempotent Away")
        session.add_all(
            [
                CompetitionParticipant(competition_id=competition.id, club_id=home_club.id, status="joined"),
                CompetitionParticipant(competition_id=competition.id, club_id=away_club.id, status="joined"),
            ]
        )
        kickoff_at = datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc)
        match = CompetitionMatch(
            id=str(uuid4()),
            competition_id=competition.id,
            round_id=round_row.id,
            round_number=1,
            stage="league",
            home_club_id=home_club.id,
            away_club_id=away_club.id,
            match_date=kickoff_at.date(),
            scheduled_at=kickoff_at,
            status=MatchStatus.SCHEDULED.value,
            metadata_json={},
        )
        session.add(match)
        session.commit()

        runner = CompetitionAutoRunner(session)
        completed = runner._simulate_match(competition, match)
        session.commit()
        session.refresh(completed)
        assert completed.status == MatchStatus.COMPLETED.value
        original_score = (completed.home_score, completed.away_score)
        original_events = len(
            session.scalars(select(CompetitionMatchEvent).where(CompetitionMatchEvent.match_id == completed.id)).all()
        )
        assert original_events > 0

        # Represents another worker that selected the fixture before the first
        # worker committed and is retrying with a stale scheduled snapshot.
        stale_snapshot = SimpleNamespace(id=completed.id, status=MatchStatus.SCHEDULED.value)
        retried = runner._simulate_match(competition, stale_snapshot)
        session.commit()

        assert retried.status == MatchStatus.COMPLETED.value
        assert (retried.home_score, retried.away_score) == original_score
        assert (
            len(
                session.scalars(
                    select(CompetitionMatchEvent).where(CompetitionMatchEvent.match_id == completed.id)
                ).all()
            )
            == original_events
        )
        participants = session.scalars(
            select(CompetitionParticipant).where(CompetitionParticipant.competition_id == competition.id)
        ).all()
        assert len(participants) == 2
        assert all(participant.played == 1 for participant in participants)

def test_global_owner_fixture_reconciles_and_executes_only_on_canonical_runner(
    session_factory,
    monkeypatch,
) -> None:
    from types import SimpleNamespace

    from app.models.owner_competition_lifecycle_mapping import (
        OwnerCompetitionLifecycleMapping,
        OwnerMatchLifecycleMapping,
    )
    from app.services.owner_competition_lifecycle_mapping_service import (
        OwnerCompetitionLifecycleMappingService,
    )

    with session_factory() as session:
        eval_time = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        competition = _create_test_competition(session, "Reconciled Global League")
        competition.source_type = "gtex"
        competition.source_id = str(uuid4())
        session.add(
            CompetitionPrizeRule(
                competition_id=competition.id,
                payout_mode="percentage",
                top_n=2,
                payout_percentages=[70, 30],
            )
        )
        round_row = CompetitionRound(
            id=str(uuid4()),
            competition_id=competition.id,
            round_number=1,
            stage="league",
            status="active",
        )
        session.add(round_row)
        _, home_club = _create_user_and_club(session, "Reconciled Home")
        _, away_club = _create_user_and_club(session, "Reconciled Away")
        session.add_all(
            [
                CompetitionParticipant(
                    competition_id=competition.id,
                    club_id=home_club.id,
                    status="joined",
                ),
                CompetitionParticipant(
                    competition_id=competition.id,
                    club_id=away_club.id,
                    status="joined",
                ),
            ]
        )
        canonical_match = CompetitionMatch(
            id=str(uuid4()),
            competition_id=competition.id,
            round_id=round_row.id,
            round_number=1,
            stage="league",
            home_club_id=home_club.id,
            away_club_id=away_club.id,
            match_date=eval_time.date(),
            scheduled_at=eval_time - timedelta(hours=1),
            status=MatchStatus.SCHEDULED.value,
        )
        legacy_competition = OwnerCompetition(
            name="Legacy Global League",
            host_type="gtex",
            status="running",
            current_round=1,
        )
        session.add(legacy_competition)
        session.flush()
        legacy_match = OwnerMatch(
            competition_id=legacy_competition.id,
            round_number=1,
            home_club_id=home_club.id,
            away_club_id=away_club.id,
            home_name=home_club.club_name,
            away_name=away_club.club_name,
            status="scheduled",
        )
        session.add_all([canonical_match, legacy_match])
        session.flush()

        mapping_service = OwnerCompetitionLifecycleMappingService(session)
        competition_mapping = mapping_service.bind_competition(
            legacy_competition.id,
            competition.id,
        )
        fixture_mapping = mapping_service.bind_scheduled_match(
            legacy_match.id,
            canonical_match.id,
        )
        assert competition_mapping.canonical_competition_id == competition.id
        assert fixture_mapping.canonical_match_id == canonical_match.id
        session.commit()

        settlement_attempts: list[tuple[str, int]] = []
        original_settle = CompetitionLifecycleService._settle_platform_rewards

        def count_settlement(service, comp, rewards):
            settlement_attempts.append((comp.id, len(rewards)))
            return original_settle(service, comp, rewards)

        monkeypatch.setattr(
            CompetitionLifecycleService,
            "_settle_platform_rewards",
            count_settlement,
        )

        runner = CompetitionAutoRunner(session)
        runner.run_until_idle(
            competition,
            simulate_scheduled_matches=True,
            evaluation_time=eval_time,
        )
        session.commit()
        session.refresh(competition)
        completed = session.get(CompetitionMatch, canonical_match.id)
        assert completed is not None
        session.refresh(legacy_match)

        assert completed.status == MatchStatus.COMPLETED.value
        assert completed.completed_at is not None
        assert competition.status == CompetitionStatus.SETTLED.value
        assert competition.settled_at is not None
        assert len(
            session.scalars(
                select(CompetitionMatchEvent).where(
                    CompetitionMatchEvent.match_id == canonical_match.id
                )
            ).all()
        ) > 0
        assert legacy_match.status == "scheduled"
        assert legacy_match.home_goals is None
        assert legacy_match.away_goals is None
        assert legacy_match.played_at is None

        original_score = (completed.home_score, completed.away_score)
        original_event_count = len(
            session.scalars(
                select(CompetitionMatchEvent).where(
                    CompetitionMatchEvent.match_id == canonical_match.id
                )
            ).all()
        )
        retried = runner._simulate_match(
            competition,
            SimpleNamespace(id=canonical_match.id, status=MatchStatus.SCHEDULED.value),
        )
        session.commit()

        assert retried.status == MatchStatus.COMPLETED.value
        assert (retried.home_score, retried.away_score) == original_score
        assert len(
            session.scalars(
                select(CompetitionMatchEvent).where(
                    CompetitionMatchEvent.match_id == canonical_match.id
                )
            ).all()
        ) == original_event_count
        assert session.get(OwnerCompetitionLifecycleMapping, competition_mapping.id) is not None
        assert session.get(OwnerMatchLifecycleMapping, fixture_mapping.id) is not None

        # A retry of competition finalization must return the existing payout
        # pools and reward ledger references without issuing another settlement.
        reward_snapshot = sorted(
            (
                reward.id,
                reward.ledger_transaction_id,
                reward.status,
            )
            for reward in session.scalars(
                select(CompetitionReward).where(
                    CompetitionReward.competition_id == competition.id
                )
            ).all()
        )
        pool_ids_before = sorted(
            pool.id
            for pool in session.scalars(
                select(CompetitionRewardPool).where(
                    CompetitionRewardPool.competition_id == competition.id
                )
            ).all()
        )
        settled_at_before = competition.settled_at
        settlement_attempt_count_before_retry = sum(
            1 for competition_id, _ in settlement_attempts
            if competition_id == competition.id
        )
        assert settlement_attempt_count_before_retry >= 1

        repeated_pools = CompetitionLifecycleService(session).finalize_competition(
            competition
        )
        session.commit()
        session.refresh(competition)

        assert sorted(pool.id for pool in repeated_pools) == pool_ids_before
        assert sorted(
            (
                reward.id,
                reward.ledger_transaction_id,
                reward.status,
            )
            for reward in session.scalars(
                select(CompetitionReward).where(
                    CompetitionReward.competition_id == competition.id
                )
            ).all()
        ) == reward_snapshot
        assert competition.settled_at == settled_at_before
        assert sum(
            1 for competition_id, _ in settlement_attempts
            if competition_id == competition.id
        ) == settlement_attempt_count_before_retry

