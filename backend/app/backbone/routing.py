from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OutboxTopicRouter:
    topic_prefix: str = "gtex"

    def topic_for(self, event_type: str) -> str:
        topic = _EVENT_TOPIC_MAP.get(event_type, event_type)
        prefix = self.topic_prefix.strip(".")
        clean = topic.strip(".")
        return f"{prefix}.{clean}" if prefix else clean


_EVENT_TOPIC_MAP = {
    "orchestrator.command.match.start": "orchestrator.match.start",
    "orchestrator.command.match.complete": "orchestrator.match.complete",
    "orchestrator.command.match.rewards": "orchestrator.match.rewards",
    "competition_engine.queue.match_simulation.queued": "match.scheduled",
    "competition_engine.queue.notification.queued": "competition.notification.requested",
    "competition_engine.queue.bracket_advancement.queued": "competition.advancement.requested",
    "competition_engine.queue.payout_settlement.queued": "competition.settlement.requested",
    "match.result": "match.result",
    "match.replay.ready": "match.replay.ready",
    "match.completed": "match.completed",
    "match.failed": "match.failed",
    "wallet.transaction.appended": "transactions.wallet",
    "wallet.payment.created": "transactions.payment.created",
    "wallet.payment.verified": "transactions.payment.verified",
    "wallet.withdrawal.requested": "transactions.withdrawal.requested",
    "wallet.conversion.completed": "transactions.wallet.conversion",
    "risk.fraud.detected": "risk.fraud.detected",
}


__all__ = ["OutboxTopicRouter"]
