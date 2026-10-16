from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from app.common.enums.competition_type import CompetitionType
from app.common.enums.fixture_window import FixtureWindow
from app.common.enums.replay_visibility import ReplayVisibility
from app.competition_engine.queue_contracts import MatchSimulationJob
from app.workers.base_worker import WorkerEvent
from app.workers.simulation_worker import SimulationWorker, run_match_simulation
from backend.tests.match_engine.helpers import build_request, build_team


class _FakeBroker:
    def connect(self) -> None:
        return None

    def consume(self):
        return None

    def publish(self, event: WorkerEvent) -> None:
        return None

    def close(self) -> None:
        return None


def test_simulation_worker_emits_rich_completed_payload_for_queue_jobs() -> None:
    worker = SimulationWorker(broker=_FakeBroker())
    job = MatchSimulationJob(
        fixture_id="fixture-rich-1",
        competition_id="league-rich",
        competition_type=CompetitionType.LEAGUE,
        match_date=date(2026, 3, 29),
        window=FixtureWindow.SENIOR_2,
        season_id="league-rich",
        competition_name="Rich League",
        stage_name="Round 5",
        round_number=5,
        scheduled_kickoff_at=datetime(2026, 3, 29, 18, 0, tzinfo=timezone.utc),
        simulation_seed=17,
        home_club_id="club-home",
        home_club_name="Club Home",
        home_strength_rating=82,
        away_club_id="club-away",
        away_club_name="Club Away",
        away_strength_rating=78,
        replay_visibility=ReplayVisibility.COMPETITION,
    )

    completed = worker.handle_event(
        WorkerEvent(
            type="competition_engine.queue.match_simulation.queued",
            payload={"job_payload": job.model_dump(mode="json")},
        )
    )

    simulation = completed.payload["simulation"]

    assert completed.type == "match.completed"
    assert completed.payload["queue"]["results_topic"] == "match.completed"
    assert simulation["engine"] == "gtex-match-engine-v2"
    assert simulation["competition"]["type"] == "league"
    assert simulation["home"]["score"] >= 0
    assert simulation["away"]["score"] >= 0
    assert "cards" in simulation["discipline"]
    assert "suspensions" in simulation["discipline"]
    assert isinstance(simulation["injuries"], list)
    assert simulation["performance_outputs"]["players"]
    assert simulation["growth_hook"]["destination"] == "thread_b_growth_engine"
    assert simulation["growth_hook"]["players"] == simulation["performance_outputs"]["players"]


def test_run_match_simulation_projects_suspensions_when_discipline_breaks_down() -> None:
    stable_home = build_team("stable-home", "Stable Home", 80)
    volatile_away = build_team(
        "volatile-away",
        "Volatile Away",
        79,
        aggression=100,
        discipline=18,
        fitness=68,
        substitution_windows=(88,),
        yellow_card_substitution_minute=89,
    )
    home_team = stable_home.model_copy(
        update={
            "tactics": stable_home.tactics.model_copy(update={"allow_substitutions": False}),
        }
    )
    away_team = volatile_away.model_copy(
        update={
            "tactics": volatile_away.tactics.model_copy(
                update={
                    "allow_substitutions": False,
                    "yellow_card_substitution_minute": 89,
                }
            ),
        }
    )

    simulation: dict | None = None
    for seed in range(1, 220):
        payload = build_request(seed=seed, home_team=home_team, away_team=away_team).model_dump(mode="json")
        candidate = run_match_simulation(payload)
        if candidate["discipline"]["suspensions"]:
            simulation = candidate
            break

    assert simulation is not None
    suspension = simulation["discipline"]["suspensions"][0]

    assert suspension["matches"] == 1
    assert suspension["reason"] in {"straight_red", "second_yellow", "yellow_accumulation"}
    assert suspension["applies_from"] == "next_match"
    assert simulation["growth_hook"]["players"]


def test_run_match_simulation_rejects_invalid_payload_without_legacy_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GTE_ENABLE_LEGACY_MATCH_SIMULATION", raising=False)

    with pytest.raises(ValueError, match="legacy mock simulation is disabled"):
        run_match_simulation({"fixture_id": "fixture-missing-teams"})


def test_run_match_simulation_rejects_legacy_mock_in_protected_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GTE_ENABLE_LEGACY_MATCH_SIMULATION", "true")
    monkeypatch.setenv("GTE_APP_ENV", "production")

    with pytest.raises(ValueError, match="legacy mock simulation is disabled"):
        run_match_simulation({"fixture_id": "fixture-missing-teams"})
