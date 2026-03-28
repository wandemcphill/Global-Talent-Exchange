from __future__ import annotations

from typing import Any

from app.core.config import Settings
from app.workers.base_worker import BaseWorker, EventBroker, RetryPolicy, WorkerEvent, run_worker, utcnow_iso


def calculate_rewards(payload: dict[str, Any]) -> dict[str, Any]:
    match_id = str(payload.get("match_id") or "").strip() or "unknown-match"
    simulation = payload.get("simulation")
    rewards: list[dict[str, Any]] = []

    if isinstance(simulation, dict):
        home = simulation.get("home")
        away = simulation.get("away")
        winner_side = str(simulation.get("winner_side") or "draw").strip().lower()

        if isinstance(home, dict):
            rewards.append(
                {
                    "recipient_id": home.get("id") or f"{match_id}:home",
                    "recipient_name": home.get("name") or "Home",
                    "amount": 50 if winner_side == "draw" else 100 if winner_side == "home" else 25,
                    "currency": "points",
                    "reason": "match.completed",
                }
            )
        if isinstance(away, dict):
            rewards.append(
                {
                    "recipient_id": away.get("id") or f"{match_id}:away",
                    "recipient_name": away.get("name") or "Away",
                    "amount": 50 if winner_side == "draw" else 100 if winner_side == "away" else 25,
                    "currency": "points",
                    "reason": "match.completed",
                }
            )

    participants = payload.get("participants")
    if isinstance(participants, list) and participants:
        rewards = []
        winner_id = str(payload.get("winner_id") or "").strip() or None
        for participant in participants:
            if isinstance(participant, dict):
                recipient_id = str(
                    participant.get("user_id")
                    or participant.get("participant_id")
                    or participant.get("id")
                    or ""
                ).strip()
                recipient_name = str(participant.get("name") or participant.get("display_name") or recipient_id).strip()
            else:
                recipient_id = str(participant).strip()
                recipient_name = recipient_id
            if not recipient_id:
                continue
            rewards.append(
                {
                    "recipient_id": recipient_id,
                    "recipient_name": recipient_name or recipient_id,
                    "amount": 100 if winner_id and recipient_id == winner_id else 25,
                    "currency": "points",
                    "reason": "match.completed",
                }
            )

    return {
        "match_id": match_id,
        "distributed_at": utcnow_iso(),
        "rewards": rewards,
        "reward_count": len(rewards),
    }


class RewardWorker(BaseWorker):
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        broker: EventBroker | None = None,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        super().__init__(
            worker_name="reward-worker",
            consumes=("match.completed",),
            emits=("rewards.distributed",),
            consumer_group="gtex-reward-worker",
            settings=settings,
            broker=broker,
            retry_policy=retry_policy,
        )

    def handle_event(self, event: WorkerEvent) -> WorkerEvent:
        reward_summary = calculate_rewards(event.payload)
        return self.emit_event(
            event_type="rewards.distributed",
            key=reward_summary["match_id"],
            payload={
                "match_id": reward_summary["match_id"],
                "source_event": event.type,
                "rewards": reward_summary["rewards"],
                "reward_count": reward_summary["reward_count"],
                "distributed_at": reward_summary["distributed_at"],
            },
        )


def main() -> None:
    run_worker(RewardWorker())


if __name__ == "__main__":
    main()
