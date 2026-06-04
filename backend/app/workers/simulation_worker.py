from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import ValidationError

from app.competition_engine.queue_contracts import MatchSimulationJob
from app.core.config import Settings
from app.match_engine.schemas import MatchSimulationRequest
from app.match_engine.services.match_simulation_service import MatchSimulationService
from app.match_engine.services.team_factory import SyntheticSquadFactory
from app.match_engine.simulation.models import MatchEventType
from app.workers.base_worker import BaseWorker, EventBroker, RetryPolicy, WorkerEvent, run_worker

_REQUEST_KEYS = (
    "match_id",
    "seed",
    "kickoff_at",
    "competition",
    "home_team",
    "away_team",
    "tactical_changes",
)


def _enum_value(value: Any) -> Any:
    return value.value if hasattr(value, "value") else value


def _candidate_payload(payload: dict[str, Any]) -> dict[str, Any]:
    job_payload = payload.get("job_payload")
    if isinstance(job_payload, Mapping):
        return dict(job_payload)
    nested_request = payload.get("simulation_request")
    if isinstance(nested_request, Mapping):
        return dict(nested_request)
    return dict(payload)


def _match_request_from_payload(
    payload: dict[str, Any],
    *,
    team_factory: SyntheticSquadFactory,
) -> MatchSimulationRequest | None:
    candidate = _candidate_payload(payload)
    if {"match_id", "home_team", "away_team"} <= set(candidate):
        request_payload = {key: candidate[key] for key in _REQUEST_KEYS if key in candidate}
        try:
            return MatchSimulationRequest.model_validate(request_payload)
        except ValidationError:
            return None
    try:
        job = MatchSimulationJob.model_validate(candidate)
    except ValidationError:
        return None
    return team_factory.build_request(job)


def _performance_outputs(replay_payload) -> dict[str, Any]:
    player_rows = sorted(
        (
            {
                "player_id": item.player_id,
                "player_name": item.player_name,
                "team_id": item.team_id,
                "team_name": item.team_name,
                "role": _enum_value(item.role),
                "minutes_played": item.minutes_played,
                "goals": item.goals,
                "assists": item.assists,
                "saves": item.saves,
                "shots_on_target": item.shots_on_target,
                "missed_chances": item.missed_chances,
                "yellow_cards": item.yellow_cards,
                "red_card": item.red_card,
                "injured": item.injured,
                "rating": round(float(item.rating or 0.0), 2),
                "summary": item.rating_summary,
            }
            for item in replay_payload.summary.player_stats
        ),
        key=lambda item: (
            -item["rating"],
            -item["goals"],
            -item["assists"],
            item["team_name"],
            item["player_name"],
        ),
    )
    team_rows = [
        {
            "team_id": replay_payload.summary.home_stats.team_id,
            "team_name": replay_payload.summary.home_stats.team_name,
            "goals": replay_payload.summary.home_score,
            "shots": replay_payload.summary.home_stats.shots,
            "shots_on_target": replay_payload.summary.home_stats.shots_on_target,
            "possession": replay_payload.summary.home_stats.possession,
            "rating_anchor": round(float(replay_payload.summary.home_stats.strength.overall), 2),
        },
        {
            "team_id": replay_payload.summary.away_stats.team_id,
            "team_name": replay_payload.summary.away_stats.team_name,
            "goals": replay_payload.summary.away_score,
            "shots": replay_payload.summary.away_stats.shots,
            "shots_on_target": replay_payload.summary.away_stats.shots_on_target,
            "possession": replay_payload.summary.away_stats.possession,
            "rating_anchor": round(float(replay_payload.summary.away_stats.strength.overall), 2),
        },
    ]
    return {
        "mvp": player_rows[0] if player_rows else None,
        "players": player_rows,
        "teams": team_rows,
    }


def _discipline_seed_state(payload: dict[str, Any]) -> dict[str, dict[str, int]]:
    candidate = _candidate_payload(payload)
    raw_state = payload.get("discipline_state")
    if not isinstance(raw_state, Mapping):
        raw_state = candidate.get("discipline_state")
    if not isinstance(raw_state, Mapping):
        return {}
    resolved: dict[str, dict[str, int]] = {}
    for player_id, state in raw_state.items():
        if not isinstance(state, Mapping):
            continue
        resolved[str(player_id)] = {
            "yellow_cards": max(0, int(state.get("yellow_cards", 0) or 0)),
            "pending_suspensions": max(0, int(state.get("pending_suspensions", 0) or 0)),
        }
    return resolved


def _red_card_sources(replay_payload) -> dict[str, str]:
    sources: dict[str, str] = {}
    for event in replay_payload.timeline.events:
        if event.event_type is not MatchEventType.RED_CARD or event.primary_player is None:
            continue
        source = str(event.metadata.get("source") or "red_card")
        sources[event.primary_player.player_id] = source
    return sources


def _discipline_report(replay_payload, payload: dict[str, Any]) -> dict[str, Any]:
    seed_state = _discipline_seed_state(payload)
    red_sources = _red_card_sources(replay_payload)
    cards: list[dict[str, Any]] = []
    suspensions: list[dict[str, Any]] = []
    next_state: dict[str, dict[str, int]] = {}

    for item in replay_payload.summary.player_stats:
        prior = seed_state.get(item.player_id, {})
        prior_yellow = max(0, int(prior.get("yellow_cards", 0) or 0))
        prior_pending = max(0, int(prior.get("pending_suspensions", 0) or 0))
        yellow_total = prior_yellow + item.yellow_cards
        triggered_matches = 0
        trigger_reason: str | None = None

        if item.yellow_cards > 0 or item.red_card:
            cards.append(
                {
                    "player_id": item.player_id,
                    "player_name": item.player_name,
                    "team_id": item.team_id,
                    "team_name": item.team_name,
                    "yellow_cards": item.yellow_cards,
                    "red_card": item.red_card,
                    "prior_yellow_cards": prior_yellow,
                    "yellow_total": yellow_total,
                }
            )

        if item.red_card:
            triggered_matches = 1
            trigger_reason = red_sources.get(item.player_id, "red_card")
        elif item.yellow_cards > 0 and yellow_total >= 2:
            triggered_matches = 1
            trigger_reason = "yellow_accumulation"

        if triggered_matches > 0 and trigger_reason is not None:
            suspensions.append(
                {
                    "player_id": item.player_id,
                    "player_name": item.player_name,
                    "team_id": item.team_id,
                    "team_name": item.team_name,
                    "reason": trigger_reason,
                    "matches": triggered_matches,
                    "applies_from": "next_match",
                }
            )

        carry_yellow = 0 if triggered_matches > 0 else yellow_total
        next_state[item.player_id] = {
            "yellow_cards": carry_yellow,
            "pending_suspensions": prior_pending + triggered_matches,
        }

    return {
        "cards": sorted(cards, key=lambda item: (-item["red_card"], -item["yellow_total"], item["player_name"])),
        "suspensions": sorted(suspensions, key=lambda item: (item["team_name"], item["player_name"])),
        "state": next_state,
        "totals": {
            "home": {
                "team_id": replay_payload.summary.home_stats.team_id,
                "team_name": replay_payload.summary.home_stats.team_name,
                "yellow_cards": replay_payload.summary.home_stats.yellow_cards,
                "red_cards": replay_payload.summary.home_stats.red_cards,
            },
            "away": {
                "team_id": replay_payload.summary.away_stats.team_id,
                "team_name": replay_payload.summary.away_stats.team_name,
                "yellow_cards": replay_payload.summary.away_stats.yellow_cards,
                "red_cards": replay_payload.summary.away_stats.red_cards,
            },
        },
    }


def _injury_outputs(replay_payload) -> list[dict[str, Any]]:
    return [
        {
            "minute": item.minute,
            "team_name": item.team_name,
            "player_name": item.player_name,
            "severity": item.severity,
            "tactical_impact": item.tactical_impact,
        }
        for item in replay_payload.summary.injury_report
    ]


def _full_match_simulation(payload: dict[str, Any], replay_payload) -> dict[str, Any]:
    summary = replay_payload.summary
    performance = _performance_outputs(replay_payload)
    discipline = _discipline_report(replay_payload, payload)
    injuries = _injury_outputs(replay_payload)
    winner_side = "draw"
    if summary.winner_team_id == summary.home_stats.team_id:
        winner_side = "home"
    elif summary.winner_team_id == summary.away_stats.team_id:
        winner_side = "away"

    return {
        "match_id": summary.match_id,
        "status": _enum_value(summary.status),
        "engine": "gtex-match-engine-v2",
        "competition": {
            "type": _enum_value(summary.competition_type),
            "stage": summary.stage,
            "is_final": summary.is_final,
            "requires_winner": summary.requires_winner,
        },
        "home": {
            "id": summary.home_stats.team_id,
            "name": summary.home_stats.team_name,
            "score": summary.home_score,
            "stats": {
                "shots": summary.home_stats.shots,
                "shots_on_target": summary.home_stats.shots_on_target,
                "possession": summary.home_stats.possession,
                "yellow_cards": summary.home_stats.yellow_cards,
                "red_cards": summary.home_stats.red_cards,
                "injuries": summary.home_stats.injuries,
            },
            "strength": {
                "overall": round(float(summary.home_stats.strength.overall), 2),
                "attack": round(float(summary.home_stats.strength.attack), 2),
                "midfield": round(float(summary.home_stats.strength.midfield), 2),
                "defense": round(float(summary.home_stats.strength.defense), 2),
                "goalkeeping": round(float(summary.home_stats.strength.goalkeeping), 2),
            },
        },
        "away": {
            "id": summary.away_stats.team_id,
            "name": summary.away_stats.team_name,
            "score": summary.away_score,
            "stats": {
                "shots": summary.away_stats.shots,
                "shots_on_target": summary.away_stats.shots_on_target,
                "possession": summary.away_stats.possession,
                "yellow_cards": summary.away_stats.yellow_cards,
                "red_cards": summary.away_stats.red_cards,
                "injuries": summary.away_stats.injuries,
            },
            "strength": {
                "overall": round(float(summary.away_stats.strength.overall), 2),
                "attack": round(float(summary.away_stats.strength.attack), 2),
                "midfield": round(float(summary.away_stats.strength.midfield), 2),
                "defense": round(float(summary.away_stats.strength.defense), 2),
                "goalkeeping": round(float(summary.away_stats.strength.goalkeeping), 2),
            },
        },
        "winner_side": winner_side,
        "winner": (
            {
                "id": summary.winner_team_id,
                "name": summary.winner_team_name,
            }
            if summary.winner_team_id and summary.winner_team_name
            else None
        ),
        "match_storyline": (
            f"{summary.winner_team_name} took control of {summary.stage or 'the tie'}."
            if summary.winner_team_name
            else f"{summary.home_stats.team_name} and {summary.away_stats.team_name} cancelled each other out."
        ),
        "key_moments": list(summary.key_highlights),
        "player_highlights": performance["players"][:5],
        "decided_by_penalties": summary.decided_by_penalties,
        "highlights": list(summary.key_highlights),
        "injuries": injuries,
        "discipline": discipline,
        "performance_outputs": performance,
        "growth_hook": {
            "destination": "thread_b_growth_engine",
            "match_id": summary.match_id,
            "competition_type": _enum_value(summary.competition_type),
            "players": performance["players"],
            "teams": performance["teams"],
            "mvp": performance["mvp"],
        },
    }


def run_match_simulation(
    payload: dict[str, Any],
    *,
    simulation_service: MatchSimulationService | None = None,
    team_factory: SyntheticSquadFactory | None = None,
) -> dict[str, Any]:
    service = simulation_service or MatchSimulationService()
    factory = team_factory or SyntheticSquadFactory()
    request = _match_request_from_payload(payload, team_factory=factory)
    if request is None:
        raise ValueError(
            "Simulation worker requires a backend-authored MatchSimulationRequest or MatchSimulationJob payload."
        )
    replay_payload = service.build_replay_payload(request)
    return _full_match_simulation(payload, replay_payload)


class SimulationWorker(BaseWorker):
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        broker: EventBroker | None = None,
        retry_policy: RetryPolicy | None = None,
        simulation_service: MatchSimulationService | None = None,
        team_factory: SyntheticSquadFactory | None = None,
    ) -> None:
        self.simulation_service = simulation_service or MatchSimulationService()
        self.team_factory = team_factory or SyntheticSquadFactory()
        super().__init__(
            worker_name="simulation-worker",
            consumes=("match.started", "competition_engine.queue.match_simulation.queued"),
            emits=("match.completed",),
            consumer_group="gtex-simulation-worker",
            settings=settings,
            broker=broker,
            retry_policy=retry_policy,
        )

    def handle_event(self, event: WorkerEvent) -> WorkerEvent:
        simulation = run_match_simulation(
            event.payload,
            simulation_service=self.simulation_service,
            team_factory=self.team_factory,
        )
        return self.emit_event(
            event_type="match.completed",
            key=simulation["match_id"],
            payload={
                "match_id": simulation["match_id"],
                "status": simulation["status"],
                "source_event": event.type,
                "started_at": event.timestamp,
                "queue": {
                    "worker": "simulation-worker",
                    "results_topic": "match.completed",
                    "source_event": event.type,
                },
                "growth_hook": simulation.get("growth_hook"),
                "simulation": simulation,
            },
        )


def main() -> None:
    run_worker(SimulationWorker())


if __name__ == "__main__":
    main()
