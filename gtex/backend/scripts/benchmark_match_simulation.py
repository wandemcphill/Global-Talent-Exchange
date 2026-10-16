from __future__ import annotations

import json
from pathlib import Path
import sys
import time

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.match_engine.schemas import (
    MatchCompetitionContextInput,
    MatchPlayerInput,
    MatchSimulationRequest,
    MatchTeamInput,
    TeamTacticalPlanInput,
)
from app.match_engine.services.match_simulation_service import MatchSimulationService
from app.match_engine.simulation.models import MatchCompetitionType, PlayerRole, TacticalStyle


def build_request(*, seed: int, match_id: str) -> MatchSimulationRequest:
    return MatchSimulationRequest(
        match_id=match_id,
        seed=seed,
        competition=MatchCompetitionContextInput(
            competition_type=MatchCompetitionType.LEAGUE,
            stage="regular",
            is_final=False,
        ),
        home_team=build_team("home", "North City", 82),
        away_team=build_team("away", "South Town", 78),
    )


def build_team(team_id: str, team_name: str, base_overall: int) -> MatchTeamInput:
    starter_roles = [PlayerRole.GOALKEEPER] + ([PlayerRole.DEFENDER] * 4) + ([PlayerRole.MIDFIELDER] * 3) + ([PlayerRole.FORWARD] * 3)
    bench_roles = (
        PlayerRole.GOALKEEPER,
        PlayerRole.DEFENDER,
        PlayerRole.DEFENDER,
        PlayerRole.MIDFIELDER,
        PlayerRole.MIDFIELDER,
        PlayerRole.FORWARD,
        PlayerRole.FORWARD,
    )
    tactics = TeamTacticalPlanInput(
        style=TacticalStyle.BALANCED,
        pressing=55,
        tempo=55,
        aggression=50,
        substitution_windows=(60, 72, 82),
        red_card_fallback_formation="4-4-1",
        injury_auto_substitution=True,
        yellow_card_substitution_minute=70,
        yellow_card_replacement_roles=(PlayerRole.DEFENDER, PlayerRole.MIDFIELDER),
        max_substitutions=5,
    )
    starters = [build_player(team_id, index + 1, role, base_overall) for index, role in enumerate(starter_roles)]
    bench = [build_player(team_id, index + 12, role, base_overall - 3) for index, role in enumerate(bench_roles)]
    return MatchTeamInput(
        team_id=team_id,
        team_name=team_name,
        formation="4-3-3",
        tactics=tactics,
        starters=starters,
        bench=bench,
    )


def build_player(team_id: str, shirt_number: int, role: PlayerRole, base_overall: int) -> MatchPlayerInput:
    return MatchPlayerInput(
        player_id=f"{team_id}-{shirt_number}",
        player_name=f"{team_id.title()} Player {shirt_number}",
        shirt_number=shirt_number,
        role=role,
        overall=max(40, min(99, base_overall)),
        finishing=base_overall,
        creativity=base_overall,
        defending=base_overall,
        goalkeeping=max(18, base_overall if role is PlayerRole.GOALKEEPER else 20),
        discipline=72,
        fitness=74,
        pace=max(40, min(99, base_overall)),
        composure=68,
        decision_making=68,
        positioning=67,
        off_ball_movement=66,
        aerial_ability=64,
        technique=69,
        stamina_curve=70,
        consistency=67,
        clutch_factor=65,
        big_match_temperament=64,
        leadership=60,
        recent_form=65,
        morale=64,
        motivation=66,
    )


def main() -> None:
    service = MatchSimulationService()
    iterations = 100
    requests = [build_request(seed=index + 1, match_id=f"bench-{index + 1}") for index in range(iterations)]
    started_at = time.perf_counter()
    event_count = 0
    for request in requests:
        payload = service.build_replay_payload(request)
        event_count += len(payload.timeline.events)
    elapsed = time.perf_counter() - started_at
    result = {
        "benchmark": "match_simulation_cpu",
        "iterations": iterations,
        "elapsed_seconds": round(elapsed, 4),
        "matches_per_second": round(iterations / elapsed, 2) if elapsed else None,
        "average_timeline_events": round(event_count / iterations, 2),
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
