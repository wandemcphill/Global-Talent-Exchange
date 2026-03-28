from __future__ import annotations

from hashlib import sha256
from typing import Any

from app.core.config import Settings
from app.workers.base_worker import BaseWorker, EventBroker, RetryPolicy, WorkerEvent, run_worker


def _match_identity(payload: dict[str, Any]) -> str:
    for candidate_key in ("match_id", "id", "fixture_id"):
        candidate = str(payload.get(candidate_key) or "").strip()
        if candidate:
            return candidate
    serialized = repr(sorted(payload.items()))
    return sha256(serialized.encode("utf-8")).hexdigest()[:16]


def _team_view(payload: dict[str, Any], side: str) -> dict[str, Any]:
    side_payload = payload.get(side)
    if isinstance(side_payload, dict):
        source = side_payload
    else:
        source = payload
    team_id = source.get(f"{side}_team_id") or source.get("team_id")
    team_name = source.get(f"{side}_team") or source.get(f"{side}_team_name") or source.get("name") or side.title()
    return {
        "id": str(team_id).strip() if team_id is not None and str(team_id).strip() else None,
        "name": str(team_name).strip() or side.title(),
    }


def run_match_simulation(payload: dict[str, Any]) -> dict[str, Any]:
    match_id = _match_identity(payload)
    seed = sha256(match_id.encode("utf-8")).digest()
    home = _team_view(payload, "home")
    away = _team_view(payload, "away")
    home_score = seed[0] % 5
    away_score = seed[1] % 5
    if home_score == away_score and seed[2] % 2 == 1:
        home_score = min(5, home_score + 1)

    winner_side = "draw"
    winner = None
    if home_score > away_score:
        winner_side = "home"
        winner = home
    elif away_score > home_score:
        winner_side = "away"
        winner = away

    return {
        "match_id": match_id,
        "status": "completed",
        "engine": "mock-simulation-v1",
        "home": {**home, "score": home_score},
        "away": {**away, "score": away_score},
        "winner_side": winner_side,
        "winner": winner,
    }


class SimulationWorker(BaseWorker):
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        broker: EventBroker | None = None,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        super().__init__(
            worker_name="simulation-worker",
            consumes=("match.started",),
            emits=("match.completed",),
            consumer_group="gtex-simulation-worker",
            settings=settings,
            broker=broker,
            retry_policy=retry_policy,
        )

    def handle_event(self, event: WorkerEvent) -> WorkerEvent:
        simulation = run_match_simulation(event.payload)
        return self.emit_event(
            event_type="match.completed",
            key=simulation["match_id"],
            payload={
                "match_id": simulation["match_id"],
                "status": simulation["status"],
                "source_event": event.type,
                "started_at": event.timestamp,
                "simulation": simulation,
            },
        )


def main() -> None:
    run_worker(SimulationWorker())


if __name__ == "__main__":
    main()
