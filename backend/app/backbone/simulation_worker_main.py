from __future__ import annotations

from threading import Event as ThreadEvent

from app.backbone.kafka import KafkaJsonConsumer
from app.backbone.queue_runtime import SimulationQueueConsumerService
from app.competition_engine.match_dispatcher import MatchDispatcher
from app.competition_engine.queue_contracts import DurableQueuePublisher
from app.core.config import get_settings
from app.core.container import build_application_context
from app.match_engine.services.execution_runtime import LocalMatchExecutionWorker
from app.match_engine.services.team_factory import SyntheticSquadFactory
from app.replay_archive.persistence import DatabaseReplayArchiveRepository
from app.replay_archive.policy import SpectatorVisibilityPolicyService
from app.replay_archive.service import ReplayArchiveService


def main() -> None:
    settings = get_settings()
    if not settings.kafka_simulation_consumer_enabled:
        raise RuntimeError("Simulation worker is disabled. Set GTE_KAFKA_SIMULATION_CONSUMER_ENABLED=true.")
    context = build_application_context(settings=settings)
    queue_publisher = DurableQueuePublisher(
        session_factory=context.database.session_factory,
        event_publisher=context.event_publisher,
    )
    dispatcher = MatchDispatcher(queue_publisher=queue_publisher)
    worker = LocalMatchExecutionWorker(
        dispatcher=dispatcher,
        event_publisher=context.event_publisher,
        session_factory=context.database.session_factory,
        team_factory=SyntheticSquadFactory(session_factory=context.database.session_factory),
    )
    replay_archive = ReplayArchiveService(
        spectator_policy=SpectatorVisibilityPolicyService(),
        repository=DatabaseReplayArchiveRepository(session_factory=context.database.session_factory),
    )
    context.event_publisher.subscribe(replay_archive.handle_event)
    consumer = KafkaJsonConsumer(
        brokers=settings.kafka_brokers,
        group_id=f"{settings.kafka_queue_consumer_group}-simulation",
        client_id=f"{settings.kafka_client_id}-simulation",
        topics=KafkaJsonConsumer.topic_names(
            prefix=settings.kafka_topic_prefix,
            topics=("match.scheduled",),
        ),
    )
    runtime = SimulationQueueConsumerService(consumer=consumer, worker=worker)
    runtime.start()
    try:
        ThreadEvent().wait()
    finally:
        runtime.stop()
        outbox_relay = getattr(context, "outbox_relay", None)
        if outbox_relay is not None:
            outbox_relay.stop()
        if hasattr(context.event_publisher, "close"):
            context.event_publisher.close()


if __name__ == "__main__":
    main()
