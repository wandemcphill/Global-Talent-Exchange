from __future__ import annotations

import os
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.common.enums.competition_format import CompetitionFormat
from app.common.enums.competition_start_mode import CompetitionStartMode
from app.common.enums.competition_status import CompetitionStatus
from app.common.enums.match_status import MatchStatus
from app.core.config import reset_settings_cache
from app.core.database import load_model_modules
from app.ingestion.models import Player
from app.models.base import Base
from app.models.club_profile import ClubProfile
from app.models.competition import Competition
from app.models.competition_match import CompetitionMatch
from app.models.competition_match_event import CompetitionMatchEvent
from app.models.competition_match_execution import CompetitionMatchExecution
from app.models.competition_participant import CompetitionParticipant
from app.models.competition_round import CompetitionRound
from app.models.competition_rule_set import CompetitionRuleSet
from app.models.event_backbone import EventOutbox
from app.models.highlight_event import HighlightEvent
from app.models.player_contract import PlayerContract
from app.models.player_match_performance import PlayerMatchPerformance
from app.models.user import User, UserRole
from app.owner_console.models import OwnerClubEvent, OwnerClubState
from app.replay_archive.persistence import ReplayArchiveRecordRow
from app.services.canonical_live_execution_service import CanonicalLiveExecutionService
from app.services.competition_auto_runner import CompetitionAutoRunner
from backend.tests.support.secrets import MEDIA_SIGNING_TEST_SECRET, TEST_AUTH_SECRET


def _build_phase3_session_factory() -> tuple[sessionmaker[Session], object]:
    os.environ["GTE_AUTH_SECRET"] = TEST_AUTH_SECRET
    os.environ["GTE_MEDIA_SIGNING_SECRET"] = MEDIA_SIGNING_TEST_SECRET
    os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
    reset_settings_cache()
    load_model_modules()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False), engine


def _seed_club_players(session: Session, club: ClubProfile, *, match_date: date, count: int = 18) -> list[Player]:
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
        "defender",
        "forward",
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
            first_name=f"P{idx + 1}",
            last_name=club.short_name or "FC",
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
                ends_on=match_date + timedelta(days=730),
                wage_amount=Decimal("1000.00"),
            )
        )
        players.append(player)
    session.flush()
    return players


def _seed_phase3_fixture(session: Session) -> dict[str, object]:
    suffix = uuid4().hex[:8]
    home_owner = User(
        id=f"u-h-{suffix}",
        email=f"h-{suffix}@gtex.test",
        username=f"h_{suffix}",
        password_hash="hash",  # pragma: allowlist secret
        role=UserRole.USER,
        is_active=True,
    )
    away_owner = User(
        id=f"u-a-{suffix}",
        email=f"a-{suffix}@gtex.test",
        username=f"a_{suffix}",
        password_hash="hash",  # pragma: allowlist secret
        role=UserRole.USER,
        is_active=True,
    )
    home_ftm = User(
        id=f"u-h-ftm-{suffix}",
        email=f"hftm-{suffix}@gtex.test",
        username=f"hftm_{suffix}",
        password_hash="hash",  # pragma: allowlist secret
        role=UserRole.USER,
        is_active=True,
    )
    session.add_all([home_owner, away_owner, home_ftm])
    session.flush()

    club_home = ClubProfile(
        id=f"ch-{suffix}",
        owner_user_id=home_owner.id,
        club_name=f"Atlas FC {suffix}",
        short_name="ATL",
        slug=f"atlas-{suffix}",
        primary_color="#112233",
        secondary_color="#ffffff",
        accent_color="#22cc88",
    )
    club_away = ClubProfile(
        id=f"ca-{suffix}",
        owner_user_id=away_owner.id,
        club_name=f"Borealis FC {suffix}",
        short_name="BOR",
        slug=f"borealis-{suffix}",
        primary_color="#332211",
        secondary_color="#eeeeee",
        accent_color="#cc8822",
    )
    session.add_all([club_home, club_away])
    session.flush()

    match_date = date(2026, 6, 20)
    home_players = _seed_club_players(session, club_home, match_date=match_date)
    away_players = _seed_club_players(session, club_away, match_date=match_date)

    session.add(
        OwnerClubState(
            club_id=club_home.id,
            club_name=club_home.club_name,
            owner_user_id=home_owner.id,
            manager_json={"user_id": home_ftm.id},
            facilities_json={},
        )
    )
    session.add(
        OwnerClubState(
            club_id=club_away.id,
            club_name=club_away.club_name,
            owner_user_id=away_owner.id,
            manager_json={},
            facilities_json={},
        )
    )

    comp = Competition(
        id=f"comp3-{suffix}",
        host_user_id=home_owner.id,
        name=f"Canonical League {suffix}",
        format=CompetitionFormat.LEAGUE.value,
        source_type="gtex_platform",
        status=CompetitionStatus.LIVE.value,
        start_mode=CompetitionStartMode.SCHEDULED.value,
        stage="league",
        currency="coin",
        metadata_json={},
    )
    session.add(comp)
    session.flush()

    session.add(
        CompetitionRuleSet(
            id=f"rules3-{suffix}",
            competition_id=comp.id,
            format=CompetitionFormat.LEAGUE.value,
            min_participants=2,
            max_participants=2,
            league_win_points=3,
            league_draw_points=1,
            league_loss_points=0,
        )
    )
    p_home = CompetitionParticipant(id=f"ph3-{suffix}", competition_id=comp.id, club_id=club_home.id)
    p_away = CompetitionParticipant(id=f"pa3-{suffix}", competition_id=comp.id, club_id=club_away.id)
    comp_round = CompetitionRound(
        id=f"rnd3-{suffix}",
        competition_id=comp.id,
        round_number=1,
        stage="league",
        status="active",
    )
    session.add_all([p_home, p_away, comp_round])
    session.flush()

    match = CompetitionMatch(
        id=f"match3-{suffix}",
        competition_id=comp.id,
        round_id=comp_round.id,
        round_number=1,
        stage="league",
        home_club_id=club_home.id,
        away_club_id=club_away.id,
        match_date=match_date,
        scheduled_at=datetime(2026, 6, 20, 15, 0, tzinfo=UTC),
        status=MatchStatus.SCHEDULED.value,
        requires_winner=False,
        metadata_json={},
    )
    session.add(match)
    session.commit()
    return {
        "competition": comp,
        "match": match,
        "club_home": club_home,
        "club_away": club_away,
        "home_ftm": home_ftm,
        "home_players": home_players,
        "away_players": away_players,
        "p_home": p_home,
        "p_away": p_away,
    }


def test_atomic_settlement_rolls_back_cleanly_on_failure_and_recovers(monkeypatch):
    session_factory, engine = _build_phase3_session_factory()
    try:
        with session_factory() as session:
            seeded = _seed_phase3_fixture(session)
            match_id = seeded["match"].id
            comp_id = seeded["competition"].id

            svc = CanonicalLiveExecutionService(session)
            svc.start_live_execution(match_id)
            match, execution, _ = svc.step_execution(
                match_id,
                target_minute=120,
                stop_at_halftime=False,
                resume_halftime=True,
                settle_on_completion=False,
            )
            assert execution.clock_phase == "completed"
            assert execution.execution_status != "completed"
            assert match.status == MatchStatus.IN_PROGRESS.value
            assert match.stats_applied is False
            session.commit()

            # Inject a stale non-canonical row to prove savepoint rollback preserves prior DB state on failure.
            session.add(
                CompetitionMatchEvent(
                    competition_id=comp_id,
                    match_id=match_id,
                    event_type="goal",
                    minute=88,
                    club_id=seeded["club_home"].id,
                    highlight=True,
                    sequence=999999,
                    execution_revision=1,
                    event_key="seq:999999:goal",
                    metadata_json={"ghost": True},
                )
            )
            session.commit()

            original_flush = svc._emit_outbox

            def _explode_on_outbox(*args, **kwargs):
                original_flush(*args, **kwargs)
                raise RuntimeError("Simulated DB/outbox fault right before settlement commit")

            monkeypatch.setattr(svc, "_emit_outbox", _explode_on_outbox)
            with pytest.raises(RuntimeError, match="Simulated DB/outbox fault"):
                svc.settle_completed_execution(match, execution)

            # Even WITHOUT calling session.rollback(), the outer savepoint rolled back ALL settlement writes.
            p_home = session.get(CompetitionParticipant, seeded["p_home"].id)
            p_away = session.get(CompetitionParticipant, seeded["p_away"].id)
            assert match.status == MatchStatus.IN_PROGRESS.value
            assert match.stats_applied is False
            assert p_home.played == 0
            assert p_away.played == 0
            assert execution.execution_status != "completed"
            ghost_still_there = session.scalar(
                select(CompetitionMatchEvent).where(CompetitionMatchEvent.event_key == "seq:999999:goal")
            )
            assert ghost_still_there is not None
            settled_outbox = session.scalars(
                select(EventOutbox).where(
                    EventOutbox.aggregate_id == match_id,
                    EventOutbox.event_type == "competition.match.execution.settled",
                )
            ).all()
            assert settled_outbox == []

            # Retry settlement cleanly without the fault -> succeeds atomically once.
            monkeypatch.setattr(svc, "_emit_outbox", original_flush)
            completed = svc.settle_completed_execution(match, execution)
            session.commit()

            assert completed.status == MatchStatus.COMPLETED.value
            assert completed.stats_applied is True
            assert execution.execution_status == "completed"
            p_home = session.get(CompetitionParticipant, seeded["p_home"].id)
            p_away = session.get(CompetitionParticipant, seeded["p_away"].id)
            assert p_home.played == 1
            assert p_away.played == 1

            # Calling settle_completed_execution a second time is strictly idempotent.
            svc.settle_completed_execution(completed, execution)
            session.commit()
            session.refresh(p_home)
            session.refresh(p_away)
            assert p_home.played == 1
            assert p_away.played == 1
            assert (
                len(
                    session.scalars(
                        select(CompetitionMatchEvent).where(CompetitionMatchEvent.event_key == "seq:999999:goal")
                    ).all()
                )
                == 0
            )
            settled_outbox = session.scalars(
                select(EventOutbox).where(
                    EventOutbox.aggregate_id == match_id,
                    EventOutbox.event_type == "competition.match.execution.settled",
                )
            ).all()
            assert len(settled_outbox) == 1
    finally:
        engine.dispose()


def test_resimulated_settlement_reconciles_events_minutes_standings_archive_and_projections():
    session_factory, engine = _build_phase3_session_factory()
    try:
        with session_factory() as session:
            seeded = _seed_phase3_fixture(session)
            match_id = seeded["match"].id
            home_club_id = seeded["club_home"].id
            away_club_id = seeded["club_away"].id
            home_ftm_id = seeded["home_ftm"].id

            svc = CanonicalLiveExecutionService(session)
            svc.start_live_execution(match_id)
            # Play up to halftime (minute 45)
            _, execution, _ = svc.step_execution(match_id, target_minute=45, stop_at_halftime=True)
            assert execution.clock_phase == "halftime"

            # Identify one active starter and one bench outfield player to substitute at halftime (minute 45).
            snap = dict(execution.home_tactics_json)
            req = execution.simulation_request_json
            home_lineup = req["home_team"]["starters"]
            home_bench = req["home_team"]["bench"]
            starter_out = next(
                p
                for p in home_lineup
                if p["role"] != "GK" and p["player_id"] in set(snap["active_player_ids"])
            )
            bench_in = next(
                p
                for p in home_bench
                if p["role"] != "GK" and p["player_id"] not in set(snap["active_player_ids"])
            )

            tactic_res = svc.apply_live_tactical_command(
                match_id,
                side="home",
                actor_user_id=home_ftm_id,
                mentality="ultra_attacking",
                tempo=88,
                press_intensity=84,
                defensive_line=78,
                risk_level=80,
                substitutions=[
                    {
                        "outgoing_player_id": starter_out["player_id"],
                        "incoming_player_id": bench_in["player_id"],
                        "reason": "halftime tactical switch",
                    }
                ],
                expected_revision=int(execution.execution_revision),
                idempotency_key="phase3-ht-sub-1",
            )
            assert tactic_res["applied_immediately"] is True
            assert tactic_res["effective_minute"] == 45

            # Plant a phantom future event as if an abandoned pre-resimulation draft existed.
            session.add(
                CompetitionMatchEvent(
                    competition_id=seeded["competition"].id,
                    match_id=match_id,
                    event_type="goal",
                    minute=79,
                    club_id=away_club_id,
                    highlight=True,
                    sequence=888888,
                    execution_revision=1,
                    event_key="seq:888888:goal",
                    metadata_json={"ghost_goal": True},
                )
            )
            session.commit()

            completed, execution, _ = svc.step_execution(
                match_id,
                target_minute=120,
                stop_at_halftime=False,
                resume_halftime=True,
                settle_on_completion=True,
            )
            session.commit()

            assert completed.status == MatchStatus.COMPLETED.value
            assert completed.stats_applied is True
            assert execution.execution_status == "completed"

            # 1. Ghost goal eliminated; every CompetitionMatchEvent has unique seq:{sequence}:{type}
            events = session.scalars(
                select(CompetitionMatchEvent)
                .where(CompetitionMatchEvent.match_id == match_id)
                .order_by(CompetitionMatchEvent.sequence.asc())
            ).all()
            assert not any(ev.event_key == "seq:888888:goal" for ev in events)
            replay = dict((completed.metadata_json or {})["replay_payload"])
            replay_events = replay["timeline"]["events"]
            assert len(events) == len(replay_events)
            assert any(ev.event_type == "substitution" and ev.minute == 45 for ev in events)

            # 2. Match score aligns identically with simulation summary, last timeline event, standings & archive.
            summary = replay["summary"]
            assert completed.home_score == summary["home_score"]
            assert completed.away_score == summary["away_score"]
            assert replay_events[-1]["home_score"] == completed.home_score
            assert replay_events[-1]["away_score"] == completed.away_score

            p_home = session.get(CompetitionParticipant, seeded["p_home"].id)
            p_away = session.get(CompetitionParticipant, seeded["p_away"].id)
            assert p_home.played == 1
            assert p_away.played == 1
            assert p_home.goals_for == completed.home_score
            assert p_home.goals_against == completed.away_score
            assert p_away.goals_for == completed.away_score
            assert p_away.goals_against == completed.home_score

            # 3. PlayerMatchPerformance minutes reconcile cleanly with simulation summary & substitutions.
            perf_rows = {
                row.player_id: row
                for row in session.scalars(
                    select(PlayerMatchPerformance).where(PlayerMatchPerformance.match_id == match_id)
                ).all()
            }
            assert len(perf_rows) > 0
            summary_stats_by_id = {
                item["player_id"]: item for item in summary["player_stats"] if item.get("player_id")
            }
            assert perf_rows[starter_out["player_id"]].started is True
            assert perf_rows[starter_out["player_id"]].minutes_played == 45
            assert perf_rows[bench_in["player_id"]].started is False
            bench_sub_out = summary_stats_by_id.get(bench_in["player_id"], {}).get("substituted_out_minute")
            expected_bench_minutes = (int(bench_sub_out) - 45) if bench_sub_out is not None else 45
            assert perf_rows[bench_in["player_id"]].minutes_played == expected_bench_minutes
            subbed_in_ids = {
                ev.player_id
                for ev in events
                if ev.event_type == "substitution" and ev.player_id
            }
            subbed_out_ids = {
                ev.secondary_player_id
                for ev in events
                if ev.event_type == "substitution" and ev.secondary_player_id
            }
            for sub_ev in [ev for ev in events if ev.event_type == "substitution" and ev.player_id]:
                in_id = sub_ev.player_id
                if in_id in perf_rows:
                    assert perf_rows[in_id].started is False
                    assert perf_rows[in_id].minutes_played > 0

            # Full-90 starters who weren't subbed out recorded 90 minutes matching simulation summary.
            full90_starters = [
                p["player_id"]
                for p in home_lineup
                if p["player_id"] not in subbed_out_ids
            ]
            assert len(full90_starters) > 0
            for pid in full90_starters:
                assert perf_rows[pid].started is True
                assert perf_rows[pid].minutes_played == summary_stats_by_id[pid]["minutes_played"] == 90

            # Unused bench players are omitted from rated performances or have 0 minutes.
            unused_bench_ids = [
                p["player_id"]
                for p in home_bench
                if p["player_id"] != bench_in["player_id"] and p["player_id"] not in subbed_in_ids
            ]
            assert len(unused_bench_ids) > 0
            for unused_id in unused_bench_ids:
                if unused_id in summary_stats_by_id:
                    assert summary_stats_by_id[unused_id]["minutes_played"] == 0
                if unused_id in perf_rows:
                    assert perf_rows[unused_id].minutes_played == 0
                    assert perf_rows[unused_id].eligible_for_valuation is False

            # Every red-carded player in replay has red_card=True persisted on performance row.
            for red_ev in [ev for ev in replay_events if ev["event_type"] == "red_card"]:
                pid = (red_ev.get("primary_player") or {}).get("player_id")
                if pid and pid in perf_rows:
                    assert perf_rows[pid].red_card is True

            # 4. ReplayArchiveRecordRow & HighlightEvent & OwnerClubEvent persisted cleanly inside settlement.
            archive_row = session.scalar(
                select(ReplayArchiveRecordRow).where(ReplayArchiveRecordRow.fixture_id == match_id)
            )
            assert archive_row is not None
            assert archive_row.scoreline_json["home_goals"] == completed.home_score
            assert archive_row.scoreline_json["away_goals"] == completed.away_score

            highlight_rows = session.scalars(select(HighlightEvent).where(HighlightEvent.match_id == match_id)).all()
            assert isinstance(highlight_rows, list)

            owner_events = session.scalars(
                select(OwnerClubEvent).where(
                    OwnerClubEvent.source_type == "canonical_match",
                    OwnerClubEvent.source_id == match_id,
                    OwnerClubEvent.club_id.in_([home_club_id, away_club_id]),
                )
            ).all()
            assert len(owner_events) == 2
            assert all(ev.status == "resolved" for ev in owner_events)
    finally:
        engine.dispose()


def test_competition_auto_runner_uses_identical_canonical_settlement_keys():
    session_factory, engine = _build_phase3_session_factory()
    try:
        with session_factory() as session:
            seeded = _seed_phase3_fixture(session)
            match_id = seeded["match"].id
            comp_id = seeded["competition"].id

            runner = CompetitionAutoRunner(session)
            comp = session.get(Competition, comp_id)
            match = session.get(CompetitionMatch, match_id)
            runner._simulate_match(comp, match)
            session.commit()

            execution = session.scalar(
                select(CompetitionMatchExecution).where(CompetitionMatchExecution.match_id == match_id)
            )
            assert execution is not None
            assert execution.execution_status == "completed"
            assert execution.settled_at is not None

            events = session.scalars(
                select(CompetitionMatchEvent).where(CompetitionMatchEvent.match_id == match_id)
            ).all()
            assert events
            assert all(ev.event_key and ev.event_key.startswith("seq:") for ev in events)

            archive_row = session.scalar(
                select(ReplayArchiveRecordRow).where(ReplayArchiveRecordRow.fixture_id == match_id)
            )
            assert archive_row is not None
            outbox_settled = session.scalar(
                select(EventOutbox).where(
                    EventOutbox.aggregate_id == match_id,
                    EventOutbox.event_type == "competition.match.execution.settled",
                )
            )
            assert outbox_settled is not None
    finally:
        engine.dispose()
