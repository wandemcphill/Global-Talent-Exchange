from __future__ import annotations

from app.core.container import Container


def test_container_shutdown_closes_database_runtime() -> None:
    class _FakeDatabase:
        def __init__(self) -> None:
            self.close_calls = 0

        def close(self) -> None:
            self.close_calls += 1

    class _FakeEventPublisher:
        def __init__(self) -> None:
            self.close_calls = 0

        def close(self) -> None:
            self.close_calls += 1

    class _FakeOutboxRelay:
        def __init__(self) -> None:
            self.stop_calls = 0

        def stop(self) -> None:
            self.stop_calls += 1

    container = Container.__new__(Container)
    container.database = _FakeDatabase()
    container.event_publisher = _FakeEventPublisher()
    container.outbox_relay = _FakeOutboxRelay()
    container._initialized = True

    container.shutdown()

    assert container.database.close_calls == 1
    assert container.event_publisher.close_calls == 1
    assert container.outbox_relay.stop_calls == 1
    assert container.initialized is False
