from __future__ import annotations

import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select

from app.common.enums.competition_format import CompetitionFormat
from app.common.enums.match_status import MatchStatus
from app.core.cache import NullCacheBackend
from app.ingestion.models import Player
from app.live_matches.service import LiveMatchHub
from app.models.club_profile import ClubProfile
from app.models.competition_match_execution import CompetitionMatchExecution
from app.models.competition_rule_set import CompetitionRuleSet
from app.owner_console.models import OwnerClubState, OwnerSquadPlayer
from app.services.canonical_live_execution_service import CanonicalLiveExecutionService
from app.services.competition_match_service import CompetitionMatchService


def _phase1():
    path = Path(__file__).with_name("test_canonical_live_execution_phase1.py")
    spec = importlib.util.spec_from_file_location("gtex_phase1_fixture_helpers", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_worker_crash_after_minute_30_resumes_the_checkpoint() -> None:
    helpers = _phase1()
    from app.services.autonomous_match_service import AutonomousMatchExecutionService

    session_factory = helpers._setup_session_factory()
    with session_factory() as session:
        _, match, _, _ = helpers._seed_canonical_fixture(session)
        now = datetime.now(timezone.utc)
        match.scheduled_at = now - timedelta(minutes=5)
        session.commit()
        match_id = match.id
        service = CanonicalLiveExecutionService(session)
        service.start_live_execution(match_id, step_interval_seconds=0)
        _, stepped, _ = service.step_execution(match_id, step_minutes=30, step_interval_seconds=0)
        session.commit()
        assert stepped.current_minute == 30
        committed_at_30 = len(stepped.committed_events_json or [])

    with session_factory() as session:
        auto = AutonomousMatchExecutionService(session)
        summary = auto.start_and_step_live_fixtures(
            reference_at=datetime.now(timezone.utc) + timedelta(minutes=5),
            step_minutes=15,
            step_interval_seconds=0,
        )
        session.commit()
        execution = session.scalar(
            select(CompetitionMatchExecution).where(CompetitionMatchExecution.match_id == match_id)
        )
        assert execution is not None
        assert execution.current_minute == 45
        assert len(execution.committed_events_json or []) >= committed_at_30
        assert summary.get("advanced", 0) >= 1
        assert summary.get("started", 0) == 0


def test_noop_tactical_command_does_not_rebuild_the_remaining_match() -> None:
    helpers = _phase1()
    session_factory = helpers._setup_session_factory()
    with session_factory() as session:
        _, match, _, _ = helpers._seed_canonical_fixture(session)
        service = CanonicalLiveExecutionService(session)
        service.start_live_execution(match.id, step_interval_seconds=0)
        _, stepped, _ = service.step_execution(match.id, step_minutes=20, step_interval_seconds=0)
        session.commit()
        revision = int(stepped.execution_revision)
        checkpoint_before = dict(stepped.checkpoint_json or {})
        tail_before = list(checkpoint_before.get("future_schedule") or [])
        events_before = list(stepped.committed_events_json or [])

        result = service.apply_live_tactical_command(
            match.id,
            side="home",
            actor_user_id="owner-test",
            idempotency_key="noop-empty-body",
        )
        session.commit()
        session.refresh(stepped)
        assert result["noop"] is True
        assert int(stepped.execution_revision) == revision
        assert list(stepped.committed_events_json or []) == events_before
        checkpoint_after = dict(stepped.checkpoint_json or {})
        assert list(checkpoint_after.get("future_schedule") or []) == tail_before


def test_level_penalty_win_awards_the_winner_and_a_level_league_match_stays_a_draw() -> None:
    helpers = _phase1()
    session_factory = helpers._setup_session_factory()
    with session_factory() as session:
        _, cup_match, cup_home, cup_away = helpers._seed_canonical_fixture(
            session,
            stage="final",
            competition_format=CompetitionFormat.CUP,
        )
        _, league_match, league_home, league_away = helpers._seed_canonical_fixture(session)
        cup_rules = session.scalar(
            select(CompetitionRuleSet).where(CompetitionRuleSet.competition_id == cup_match.competition_id)
        )
        league_rules = session.scalar(
            select(CompetitionRuleSet).where(CompetitionRuleSet.competition_id == league_match.competition_id)
        )
        assert cup_rules is not None and league_rules is not None
        service = CompetitionMatchService(session)
        service.complete_match(
            match=cup_match,
            rule_set=cup_rules,
            home_score=1,
            away_score=1,
            decided_by_penalties=True,
            winner_club_id=cup_match.home_club_id,
        )
        service.complete_match(
            match=league_match,
            rule_set=league_rules,
            home_score=1,
            away_score=1,
            decided_by_penalties=False,
        )
        session.commit()
        assert cup_match.home_score == 1 and cup_match.away_score == 1
        assert cup_home.points == 3 and cup_home.wins == 1
        assert cup_away.points == 0 and cup_away.losses == 1 and cup_away.draws == 0
        assert league_home.points == 1 and league_away.points == 1
        assert league_home.draws == 1 and league_away.draws == 1


def test_warm_hub_serves_the_execution_row_ahead_of_a_stale_runtime() -> None:
    helpers = _phase1()
    session_factory = helpers._setup_session_factory()
    with session_factory() as session:
        _, match, _, _ = helpers._seed_canonical_fixture(session)
        service = CanonicalLiveExecutionService(session)
        service.start_live_execution(match.id, step_interval_seconds=0)
        service.step_execution(match.id, step_minutes=30, step_interval_seconds=0)
        match.home_score = 2
        match.away_score = 1
        session.commit()
        match_id = match.id

    hub = LiveMatchHub(session_factory=session_factory, cache_backend=NullCacheBackend())

    class _StaleRuntime:
        last_snapshot = object()

    hub._matches[match_id] = _StaleRuntime()  # type: ignore[assignment]
    state = hub.get_state(match_id)
    assert state is not None
    assert state.spectator_sync.sync_strategy == "canonical_live_execution"
    assert state.snapshot.current_minute == 30
    assert state.snapshot.score.home == 2
    assert state.snapshot.score.away == 1


def test_kickoff_uses_manager_xi_and_rejected_mentality() -> None:
    helpers = _phase1()
    session_factory = helpers._setup_session_factory()
    with session_factory() as session:
        _, match, _, _ = helpers._seed_canonical_fixture(session)
        home_club = session.get(ClubProfile, match.home_club_id)
        assert home_club is not None
        players = sorted(
            session.scalars(select(Player).where(Player.current_club_profile_id == home_club.id)).all(),
            key=lambda player: int(player.full_name.rsplit(" ", 1)[-1]),
        )[:11]
        owner_ids: list[str] = []
        for player in players:
            owner_id = str(uuid4())
            owner_ids.append(owner_id)
            session.add(
                OwnerSquadPlayer(
                    id=owner_id,
                    club_id=home_club.id,
                    player_ref=player.id,
                    name=player.full_name,
                    position=player.position or "midfielder",
                    age=24,
                    rating=80,
                )
            )
        session.add(
            OwnerClubState(
                club_id=home_club.id,
                owner_user_id=home_club.owner_user_id,
                club_name=home_club.club_name,
                facilities_json={
                    "_last_manager_matchday_selection": {
                        "starting_xi_ids": owner_ids,
                        "bench_ids": [],
                        "formation": "4-3-3",
                        "owner_preferred_player_ids": [*owner_ids[:10], "declined-youth"],
                        "decision_outcome": "declined",
                        "verdict_reason": "The manager declined the posted player.",
                        "selected_by_manager_id": "mgr-kickoff",
                        "selected_by_manager_name": "Kickoff Manager",
                        "owner_preference_evaluation": {"declined_starter_ids": ["declined-youth"]},
                    }
                },
            )
        )
        match.metadata_json = {
            "owner_pre_match_tactics": {
                home_club.id: {
                    "mentality": "attacking",
                    "effective_mentality": "defensive",
                    "manager_decision_status": "rejected",
                    "lineup_mode": "strongest",
                }
            }
        }
        session.commit()
        service = CanonicalLiveExecutionService(session)
        _, execution = service.start_live_execution(match.id, step_interval_seconds=0)
        session.commit()
        request = dict(execution.simulation_request_json or {})
        home_team = dict(request.get("home_team") or {})
        starter_ids = [row["player_id"] for row in home_team.get("starters") or []]
        assert starter_ids == [player.id for player in players]
        assert home_team["tactics"]["style"] == "defensive"
        sheet = (match.metadata_json or {})["kickoff_team_sheet"][home_club.id]
        assert sheet["starting_player_ids"] == starter_ids
        assert sheet["declined_starter_ids"] == ["declined-youth"]
        assert sheet["manager"]["manager_name"] == "Kickoff Manager"


def test_projection_records_a_bench_debut_once_and_names_the_kickoff_manager() -> None:
    from app.models.competition_match_event import CompetitionMatchEvent
    from app.owner_console.canonical_match_projection import project_completed_canonical_match
    from app.owner_console.institutional_models import OwnerClubAcademyGraduate
    from app.owner_console.models import OwnerClubEvent

    helpers = _phase1()
    session_factory = helpers._setup_session_factory()
    with session_factory() as session:
        comp, match, _, _ = helpers._seed_canonical_fixture(session)
        home = session.get(ClubProfile, match.home_club_id)
        assert home is not None
        players = sorted(
            session.scalars(select(Player).where(Player.current_club_profile_id == home.id)).all(),
            key=lambda player: int(player.full_name.rsplit(" ", 1)[-1]),
        )
        starter = players[8]
        substitute = players[10]
        substitute_owner_id = str(uuid4())
        declined_owner_id = str(uuid4())
        session.add(
            OwnerSquadPlayer(
                id=substitute_owner_id,
                club_id=home.id,
                player_ref=substitute.id,
                name="Academy Sub",
                position="FWD",
                age=18,
                rating=72,
                is_regen=True,
            )
        )
        session.add(
            OwnerSquadPlayer(
                id=declined_owner_id,
                club_id=home.id,
                name="Declined Youth",
                position="FWD",
                age=17,
                rating=70,
                is_regen=True,
            )
        )
        session.add(
            OwnerClubState(
                club_id=home.id,
                owner_user_id=home.owner_user_id,
                club_name=home.club_name,
                world_day=4,
                manager_json={"name": "Later Manager", "manager_id": "mgr-later"},
                facilities_json={
                    "_last_manager_matchday_selection": {
                        "selected_by_manager_name": "Kickoff Manager",
                        "verdict_reason": "Kept the seniors.",
                        "owner_preference_evaluation": {"declined_starter_ids": [declined_owner_id]},
                    }
                },
            )
        )
        match.status = MatchStatus.COMPLETED.value
        match.completed_at = datetime.now(timezone.utc)
        match.home_score = 1
        match.away_score = 1
        match.metadata_json = {
            "simulation_summary": {
                "player_stats": [
                    {
                        "player_id": starter.id,
                        "team_id": home.id,
                        "minutes_played": 90,
                        "started": True,
                        "goals": 1,
                        "assists": 0,
                    },
                    {
                        "player_id": substitute.id,
                        "team_id": home.id,
                        "minutes_played": 24,
                        "started": False,
                        "goals": 0,
                        "assists": 1,
                    },
                ]
            },
            "kickoff_team_sheet": {
                home.id: {
                    "declined_starter_ids": [declined_owner_id],
                    "verdict_reason": "Kept the seniors.",
                    "manager": {"manager_id": "mgr-kickoff", "manager_name": "Kickoff Manager"},
                }
            },
            "institutional_match_context": {
                "home": {
                    "world_day": 4,
                    "manager_snapshot_supplied": True,
                    "manager": {"name": "Kickoff Manager", "manager_id": "mgr-kickoff"},
                }
            },
        }
        session.add(
            CompetitionMatchEvent(
                competition_id=comp.id,
                match_id=match.id,
                event_type="injury",
                minute=70,
                club_id=home.id,
                player_id=substitute.id,
                event_key=f"injury-{match.id}",
                sequence=1,
                metadata_json={"recovery_days": 9, "injury_type": "knock"},
            )
        )
        session.commit()

        first = project_completed_canonical_match(session, match.id)
        session.commit()
        assert first["status"] in {"projected", "partial"}
        graduate = session.scalar(
            select(OwnerClubAcademyGraduate).where(OwnerClubAcademyGraduate.player_id == substitute_owner_id)
        )
        assert graduate is not None
        assert "Came off the bench" in (graduate.narrative_note or "")
        assert graduate.first_team_minutes == 24
        squad_row = session.get(OwnerSquadPlayer, substitute_owner_id)
        assert squad_row is not None
        assert squad_row.injured_days == 9
        disagreement = session.scalar(
            select(OwnerClubEvent).where(
                OwnerClubEvent.club_id == home.id,
                OwnerClubEvent.event_type == "selection_disagreement",
            )
        )
        assert disagreement is not None
        assert "Kickoff Manager" in disagreement.description
        assert "Later Manager" not in disagreement.description
        assert (disagreement.consequences_json or {}).get("score") == "1-1"

        project_completed_canonical_match(session, match.id)
        session.commit()
        session.refresh(graduate)
        session.refresh(squad_row)
        assert graduate.first_team_minutes == 24
        assert squad_row.injured_days == 9
