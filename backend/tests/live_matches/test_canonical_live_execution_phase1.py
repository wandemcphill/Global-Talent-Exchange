from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select

from app.common.enums.competition_format import CompetitionFormat
from app.common.enums.competition_start_mode import CompetitionStartMode
from app.common.enums.competition_status import CompetitionStatus
from app.common.enums.match_status import MatchStatus
from app.core.cache import NullCacheBackend
from app.core.database import create_database_engine, create_session_factory, load_model_modules
from app.ingestion.models import Player
from app.live_matches.service import LiveMatchHub
from app.models.base import Base
from app.models.club_profile import ClubProfile
from app.models.competition import Competition
from app.models.competition_match import CompetitionMatch
from app.models.competition_match_event import CompetitionMatchEvent
from app.models.competition_match_execution import CompetitionMatchExecution
from app.models.competition_participant import CompetitionParticipant
from app.models.competition_round import CompetitionRound
from app.models.competition_rule_set import CompetitionRuleSet
from app.models.player_contract import PlayerContract
from app.models.user import User, UserRole
from app.services.canonical_live_execution_service import (
    CanonicalLiveExecutionService,
    CanonicalMatchNotLiveError,
)


def _setup_session_factory():
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    load_model_modules()
    Base.metadata.create_all(bind=engine)
    return create_session_factory(engine)


def _seed_club_squad(session, club: ClubProfile, *, match_date: date, count: int = 16) -> list[Player]:
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
        "goalkeeper",
        "defender",
        "midfielder",
        "forward",
        "midfielder",
    ]
    players: list[Player] = []
    for idx in range(count):
        pos = roles[idx % len(roles)]
        player_id = str(uuid4())
        player = Player(
            id=player_id,
            source_provider="test_provider",
            provider_external_id=f"ext_{player_id[:12]}",
            full_name=f"{club.club_name} Player {idx + 1}",
            first_name=f"Player{idx + 1}",
            last_name=club.club_name,
            position=pos,
            normalized_position=pos,
            date_of_birth=date(2000, 1, 1),
            is_real_player=False,
            is_tradable=True,
            current_club_profile_id=club.id,
        )
        session.add(player)
        session.add(
            PlayerContract(
                id=str(uuid4()),
                player_id=player_id,
                club_id=club.id,
                status="active",
                signed_on=match_date - timedelta(days=30),
                starts_on=match_date - timedelta(days=30),
                ends_on=match_date + timedelta(days=365),
                wage_amount=Decimal("1000.00"),
            )
        )
        players.append(player)
    session.flush()
    return players


def _seed_canonical_fixture(
    session,
    *,
    stage: str = "league",
    competition_format: CompetitionFormat = CompetitionFormat.LEAGUE,
    extra_meta: dict | None = None,
):
    suffix = uuid4().hex[:8]
    user_home = User(
        id=f"user-home-{suffix}",
        email=f"home-{suffix}@gtex.test",
        username=f"home_{suffix}",
        password_hash="hash",
        role=UserRole.USER,
    )
    user_away = User(
        id=f"user-away-{suffix}",
        email=f"away-{suffix}@gtex.test",
        username=f"away_{suffix}",
        password_hash="hash",
        role=UserRole.USER,
    )
    session.add_all([user_home, user_away])
    session.flush()

    club_home = ClubProfile(
        id=f"club-home-{suffix}",
        owner_user_id=user_home.id,
        club_name=f"Home FC {suffix}",
        short_name="HOM",
        slug=f"home-fc-{suffix}",
        primary_color="#112233",
        secondary_color="#ffffff",
        accent_color="#22cc88",
    )
    club_away = ClubProfile(
        id=f"club-away-{suffix}",
        owner_user_id=user_away.id,
        club_name=f"Away FC {suffix}",
        short_name="AWY",
        slug=f"away-fc-{suffix}",
        primary_color="#332211",
        secondary_color="#eeeeee",
        accent_color="#cc8822",
    )
    session.add_all([club_home, club_away])
    session.flush()
    match_date = date(2026, 6, 15)
    _seed_club_squad(session, club_home, match_date=match_date)
    _seed_club_squad(session, club_away, match_date=match_date)

    comp = Competition(
        id=f"comp-{suffix}",
        host_user_id=user_home.id,
        name=f"Canonical Test Comp {suffix}",
        format=competition_format.value,
        source_type="gtex_platform",
        status=CompetitionStatus.LIVE.value,
        start_mode=CompetitionStartMode.SCHEDULED.value,
        stage=stage,
        currency="coin",
        metadata_json=dict(extra_meta or {}),
    )
    session.add(comp)
    session.flush()

    rule_set = CompetitionRuleSet(
        id=f"rules-{suffix}",
        competition_id=comp.id,
        format=competition_format.value,
        min_participants=2,
        max_participants=2,
        league_win_points=3,
        league_draw_points=1,
        league_loss_points=0,
    )
    session.add(rule_set)
    session.flush()

    p_home = CompetitionParticipant(
        id=f"part-h-{suffix}",
        competition_id=comp.id,
        club_id=club_home.id,
    )
    p_away = CompetitionParticipant(
        id=f"part-a-{suffix}",
        competition_id=comp.id,
        club_id=club_away.id,
    )
    session.add_all([p_home, p_away])

    comp_round = CompetitionRound(
        id=f"round-{suffix}",
        competition_id=comp.id,
        round_number=1,
        stage=stage,
        status="active",
    )
    session.add(comp_round)
    session.flush()

    match = CompetitionMatch(
        id=f"match-{suffix}",
        competition_id=comp.id,
        round_id=comp_round.id,
        round_number=1,
        stage=stage,
        home_club_id=club_home.id,
        away_club_id=club_away.id,
        match_date=date(2026, 6, 15),
        scheduled_at=datetime(2026, 6, 15, 15, 0, tzinfo=timezone.utc),
        status=MatchStatus.SCHEDULED.value,
        requires_winner=(competition_format is CompetitionFormat.CUP),
        metadata_json={},
    )
    session.add(match)
    session.commit()
    return comp, match, p_home, p_away


def test_canonical_progressive_execution_halftime_pause_and_fulltime_settlement() -> None:
    session_factory = _setup_session_factory()
    with session_factory() as session:
        _, match, p_home, p_away = _seed_canonical_fixture(session)
        service = CanonicalLiveExecutionService(session)

        # 1. Start execution: match becomes live, NOT completed/settled
        started_match, execution = service.start_live_execution(match.id)
        session.commit()

        assert started_match.status == MatchStatus.IN_PROGRESS.value
        assert started_match.stats_applied is False
        assert started_match.completed_at is None
        assert execution.execution_status == "in_progress"
        assert execution.execution_revision == 1
        assert execution.assigned_duration_seconds <= 600
        assert execution.current_minute == 0

        # Duplicate kickoff is idempotent on live match
        dup_match, dup_exec = service.start_live_execution(match.id)
        assert dup_exec.id == execution.id
        assert dup_match.status == MatchStatus.IN_PROGRESS.value

        # 2. Step 0 -> 20
        m20, e20, ev20 = service.step_execution(match.id, step_minutes=20)
        session.commit()
        assert m20.status == MatchStatus.IN_PROGRESS.value
        assert m20.stats_applied is False
        assert e20.current_minute == 20
        assert e20.clock_phase == "first_half"
        assert isinstance(ev20, list)

        # 3. Step to 45 -> pauses at halftime
        m45, e45, _ = service.step_execution(match.id, target_minute=50, stop_at_halftime=True)
        session.commit()
        assert m45.status == MatchStatus.PAUSED.value
        assert m45.stats_applied is False
        assert e45.execution_status == "paused"
        assert e45.paused_reason == "halftime"
        assert e45.current_minute == 45
        assert e45.clock_phase == "halftime"

        # Step without resume_halftime while halftime break active does not jump ahead
        _, e45_wait, wait_events = service.step_execution(
            match.id,
            step_minutes=15,
            resume_halftime=False,
            reference_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        )
        assert e45_wait.current_minute == 45
        assert wait_events == []

        # 4. Resume halftime and advance to 70 -> still in progress, no premature settlement
        m70, e70, _ = service.step_execution(match.id, target_minute=70, resume_halftime=True)
        session.commit()
        assert m70.status == MatchStatus.IN_PROGRESS.value
        assert m70.stats_applied is False
        assert e70.current_minute == 70
        assert e70.clock_phase == "second_half"

        # 5. Step to 90 -> settles ONCE atomically
        m90, e90, _ = service.step_execution(match.id, target_minute=90)
        session.commit()
        assert m90.status == MatchStatus.COMPLETED.value
        assert m90.stats_applied is True
        assert m90.completed_at is not None
        assert e90.execution_status == "completed"
        assert e90.settled_at is not None

        session.refresh(p_home)
        session.refresh(p_away)
        assert p_home.played == 1
        assert p_away.played == 1

        # Re-attempting start or step on settled match stays idempotent / fail-closed
        try:
            service.start_live_execution(match.id)
            raise AssertionError("Expected CanonicalMatchNotLiveError for completed fixture")
        except CanonicalMatchNotLiveError:
            pass

        events = list(
            session.scalars(
                select(CompetitionMatchEvent).where(CompetitionMatchEvent.match_id == match.id)
            ).all()
        )
        assert any(ev.event_type == "kickoff" for ev in events)
        assert any(ev.event_type == "halftime" for ev in events)
        assert any(ev.event_type == "fulltime" for ev in events)


def test_major_knockout_broadcast_cap_up_to_900_seconds() -> None:
    session_factory = _setup_session_factory()
    with session_factory() as session:
        _, match, _, _ = _seed_canonical_fixture(
            session,
            stage="final",
            competition_format=CompetitionFormat.CUP,
        )
        service = CanonicalLiveExecutionService(session)
        _, execution = service.start_live_execution(match.id)
        session.commit()
        assert 600 < execution.assigned_duration_seconds <= 900


def test_hub_recovery_and_expired_lease_claim_resume() -> None:
    session_factory = _setup_session_factory()
    with session_factory() as session:
        _, match, _, _ = _seed_canonical_fixture(session)
        service = CanonicalLiveExecutionService(session)
        service.start_live_execution(match.id, lease_owner="worker-crashed", lease_ttl_seconds=1)
        service.step_execution(
            match.id,
            target_minute=25,
            lease_owner="worker-crashed",
            step_interval_seconds=0,
        )
        # Simulate crashed worker holding an expired lease on the row
        row = session.scalar(select(CompetitionMatchExecution).where(CompetitionMatchExecution.match_id == match.id))
        assert row is not None
        row.lease_owner = "worker-crashed"
        row.lease_expires_at = datetime.now(timezone.utc) - timedelta(minutes=2)
        row.next_step_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        session.commit()

    # Cold LiveMatchHub (empty memory & empty cache) recovers live state/events/tactics directly from DB
    recovered_hub = LiveMatchHub(session_factory=session_factory, cache_backend=NullCacheBackend())
    state = recovered_hub.get_state(match.id)
    assert state is not None
    assert state.is_live is True
    assert state.snapshot.current_minute == 25
    assert state.spectator_sync is not None
    assert state.spectator_sync.pause_replay_enabled is False
    events, cursor = recovered_hub.get_events_since(match.id, 0)
    assert cursor >= 1
    assert any(ev.event_type == "kickoff" for ev in events)
    assert match.id in recovered_hub.list_active_matches()

    # A new healthy worker claims the expired lease and completes the match cleanly
    with session_factory() as session:
        recovery_service = CanonicalLiveExecutionService(session, hub=recovered_hub)
        summary = recovery_service.claim_and_advance_due_executions(
            step_minutes=100,
            lease_owner="worker-healthy",
            step_interval_seconds=0,
            halftime_pause_seconds=0,
        )
        session.commit()
        assert summary["advanced"] == 1
        updated_exec = recovery_service.get_execution(match.id)
        assert updated_exec is not None
        # Stopped at halftime first; claim again resumes through full-time
        summary2 = recovery_service.claim_and_advance_due_executions(
            reference_at=datetime.now(timezone.utc) + timedelta(seconds=5),
            step_minutes=100,
            lease_owner="worker-healthy",
            step_interval_seconds=0,
        )
        session.commit()
        assert summary2["settled"] == 1


def test_admin_halt_resume_and_abandon_cancel() -> None:
    session_factory = _setup_session_factory()
    hub = LiveMatchHub(session_factory=session_factory, cache_backend=NullCacheBackend())
    with session_factory() as session:
        _, live_match, _, _ = _seed_canonical_fixture(session)
        _, pre_match, _, _ = _seed_canonical_fixture(session)
        service = CanonicalLiveExecutionService(session, hub=hub)

        service.start_live_execution(live_match.id)
        service.halt_execution(live_match.id, reason="integrity_review", actor_user_id="admin-1")
        session.commit()

        assert hub.is_match_halted(live_match.id) is True
        _, halted_exec, halted_events = service.step_execution(live_match.id, step_minutes=20)
        assert halted_exec.execution_status == "halted"
        assert halted_events == []

        resumed_match, resumed_exec = service.resume_halted_execution(live_match.id, actor_user_id="admin-1")
        session.commit()
        assert resumed_match.status == MatchStatus.IN_PROGRESS.value
        assert resumed_exec.execution_status == "in_progress"
        assert hub.is_match_halted(live_match.id) is False

        abandoned = service.cancel_or_abandon_execution(live_match.id, reason="pitch_unsafe", actor_user_id="admin-1")
        cancelled = service.cancel_or_abandon_execution(pre_match.id, reason="walkover", actor_user_id="admin-1")
        session.commit()
        assert abandoned.status == MatchStatus.ABANDONED.value
        assert abandoned.stats_applied is False
        assert cancelled.status == MatchStatus.CANCELLED.value
        assert cancelled.stats_applied is False


def test_autonomous_live_step_and_sync_autorunner_use_canonical_execution() -> None:
    from app.services.autonomous_match_service import AutonomousMatchExecutionService
    from app.services.competition_auto_runner import CompetitionAutoRunner

    session_factory = _setup_session_factory()
    with session_factory() as session:
        comp, live_match, p_home, p_away = _seed_canonical_fixture(session)
        comp2, batch_match, _, _ = _seed_canonical_fixture(session)
        now = datetime.now(timezone.utc)
        live_match.scheduled_at = now - timedelta(minutes=1)
        batch_match.scheduled_at = now + timedelta(hours=2)
        session.commit()

        # Autonomous live stepping starts due fixture in_progress (unsettled)
        auto = AutonomousMatchExecutionService(session)
        step1 = auto.start_and_step_live_fixtures(reference_at=now, step_minutes=20, step_interval_seconds=0)
        session.commit()
        assert step1["started"] == 1
        session.refresh(live_match)
        assert live_match.status == MatchStatus.IN_PROGRESS.value
        assert live_match.stats_applied is False
        exec_row = session.scalar(
            select(CompetitionMatchExecution).where(CompetitionMatchExecution.match_id == live_match.id)
        )
        assert exec_row is not None
        assert exec_row.current_minute == 20

        # Direct CompetitionAutoRunner synchronous catch-up on an unstarted fixture also persists canonical execution
        runner = CompetitionAutoRunner(session)
        settled = runner._simulate_match(comp2, batch_match)
        session.commit()
        assert settled.status == MatchStatus.COMPLETED.value
        assert settled.stats_applied is True
        batch_exec = session.scalar(
            select(CompetitionMatchExecution).where(CompetitionMatchExecution.match_id == batch_match.id)
        )
        assert batch_exec is not None
        assert batch_exec.execution_status == "completed"

