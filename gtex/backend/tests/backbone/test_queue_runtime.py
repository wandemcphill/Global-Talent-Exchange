from __future__ import annotations

from datetime import date

from app.backbone.kafka import KafkaMessage
from app.backbone.queue_runtime import SimulationQueueConsumerService
from app.common.enums.competition_type import CompetitionType
from app.common.enums.fixture_window import FixtureWindow
from app.competition_engine.queue_contracts import MatchSimulationJob


class FakeKafkaConsumer:
    def __init__(self, messages: list[KafkaMessage]) -> None:
        self._messages = messages
        self.commit_calls = 0
        self.closed = False

    def poll(self) -> list[KafkaMessage]:
        messages = list(self._messages)
        self._messages.clear()
        return messages

    def commit(self) -> None:
        self.commit_calls += 1

    def close(self) -> None:
        self.closed = True


class FakeWorker:
    def __init__(self) -> None:
        self.jobs: list[MatchSimulationJob] = []

    def execute_match_simulation(self, job: MatchSimulationJob) -> None:
        self.jobs.append(job)


def test_simulation_queue_consumer_dispatches_match_scheduled_jobs() -> None:
    job = MatchSimulationJob(
        fixture_id="fixture-900",
        competition_id="league-alpha",
        competition_type=CompetitionType.LEAGUE,
        match_date=date(2026, 3, 27),
        window=FixtureWindow.SENIOR_1,
        home_club_id="club-home",
        away_club_id="club-away",
    )
    consumer = FakeKafkaConsumer(
        [
            KafkaMessage(
                topic="gtex.match.scheduled",
                key="fixture-900",
                value={
                    "payload": {
                        "job_payload": job.model_dump(mode="json"),
                    }
                },
                headers={"event_type": "competition_engine.queue.match_simulation.queued"},
            )
        ]
    )
    worker = FakeWorker()
    runtime = SimulationQueueConsumerService(consumer=consumer, worker=worker)

    handled = runtime.poll_once()

    assert handled == 1
    assert consumer.commit_calls == 1
    assert len(worker.jobs) == 1
    assert worker.jobs[0].fixture_id == "fixture-900"
    assert worker.jobs[0].competition_id == "league-alpha"
