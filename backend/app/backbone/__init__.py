from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "ApiQueueConsumerService",
    "HybridEventPublisher",
    "KafkaJsonConsumer",
    "KafkaJsonProducer",
    "KafkaMessage",
    "OutboxRelayService",
    "OutboxTopicRouter",
    "ProjectionWorkerService",
    "SimulationQueueConsumerService",
]

_EXPORTS: dict[str, tuple[str, str]] = {
    "ApiQueueConsumerService": ("app.backbone.queue_runtime", "ApiQueueConsumerService"),
    "HybridEventPublisher": ("app.backbone.redis_fanout", "HybridEventPublisher"),
    "KafkaJsonConsumer": ("app.backbone.kafka", "KafkaJsonConsumer"),
    "KafkaJsonProducer": ("app.backbone.kafka", "KafkaJsonProducer"),
    "KafkaMessage": ("app.backbone.kafka", "KafkaMessage"),
    "OutboxRelayService": ("app.backbone.outbox_relay", "OutboxRelayService"),
    "OutboxTopicRouter": ("app.backbone.routing", "OutboxTopicRouter"),
    "ProjectionWorkerService": ("app.backbone.projection_runtime", "ProjectionWorkerService"),
    "SimulationQueueConsumerService": ("app.backbone.queue_runtime", "SimulationQueueConsumerService"),
}


def __getattr__(name: str) -> Any:
    try:
        module_path, attribute = _EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc
    module = import_module(module_path)
    value = getattr(module, attribute)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
