from __future__ import annotations

from dataclasses import dataclass, field
from threading import Event as ThreadEvent, Thread
import traceback
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.outbox import BrokerPublisher, flush_to_broker


@dataclass(slots=True)
class OutboxRelayService:
    session_factory: sessionmaker[Session]
    publisher: BrokerPublisher
    batch_size: int = 100
    poll_interval_ms: int = 1000
    _stop_event: ThreadEvent = field(default_factory=ThreadEvent)
    _thread: Thread | None = None

    def start(self) -> None:
        if self._thread is not None:
            return
        self._stop_event.clear()
        self._thread = Thread(
            target=self._run_loop,
            name="gtex-outbox-relay",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        self.publisher.close()

    def relay_once(self) -> int:
        return flush_to_broker(
            session_factory=self.session_factory,
            publisher=self.publisher,
            batch_size=self.batch_size,
        )

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.relay_once()
            except Exception:
                traceback.print_exc()
            self._stop_event.wait(max(self.poll_interval_ms, 100) / 1000)


__all__ = ["OutboxRelayService"]
