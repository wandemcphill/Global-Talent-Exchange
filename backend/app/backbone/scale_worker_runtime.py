from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Event as ThreadEvent, Thread
from time import perf_counter
import traceback
from typing import Any, Callable

from fastapi import FastAPI
from sqlalchemy.orm import Session, sessionmaker

from app.ads_engine.service import SponsoredClipService
from app.backbone.kafka import KafkaJsonConsumer
from app.core.events import DomainEvent
from app.services.creator_clip_earnings_projection_service import CreatorClipEarningsProjectionService
from app.viral.distribution import ensure_viral_dispatch_pool_store, inject_into_distribution_pool
from app.viral.ingestion_runtime import _dispatch_clip_id, _dispatch_initial_score, _normalize_dispatch_payload
from app.viral.personalized_feed_service import build_personalized_feed_service


TopicHandler = Callable[[Session, dict[str, Any]], None]


@dataclass(slots=True)
class ScaleTopicConsumerService:
    consumer: KafkaJsonConsumer
    session_factory: sessionmaker[Session]
    handler: TopicHandler
    _stop_event: ThreadEvent = field(default_factory=ThreadEvent)
    _thread: Thread | None = None

    def start(self) -> None:
        if self._thread is not None:
            return
        self._stop_event.clear()
        self._thread = Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        self.consumer.close()

    def poll_once(self) -> int:
        handled = 0
        for message in self.consumer.poll():
            envelope = dict(message.value or {})
            started_at = perf_counter()
            with self.session_factory() as session:
                try:
                    self.handler(session, envelope)
                    session.commit()
                    self.consumer.commit()
                    handled += 1
                except Exception:
                    session.rollback()
                    raise
                finally:
                    _ = perf_counter() - started_at
        return handled

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.poll_once()
            except Exception:
                traceback.print_exc()
                self._stop_event.wait(1.0)


def build_worker_app(*, settings: Any, session_factory: sessionmaker[Session], read_session_factory: sessionmaker[Session]) -> FastAPI:
    app = FastAPI()
    app.state.settings = settings
    app.state.session_factory = session_factory
    app.state.read_session_factory = read_session_factory
    return app


def feed_refresh_handler(*, app: FastAPI) -> TopicHandler:
    def handle(session: Session, envelope: dict[str, Any]) -> None:
        payload = dict(envelope.get("payload") or {})
        user_id = str(payload.get("user_id") or "").strip()
        if not user_id:
            return
        limit = max(int(payload.get("limit") or 20), 1)
        session_id = str(payload.get("session_id") or "").strip() or None
        service = build_personalized_feed_service(app=app, session=session)
        service.get_for_you(user_id=user_id, limit=limit, refresh=True, session_id=session_id)
        if bool(payload.get("refresh_following", True)):
            service.get_following(user_id=user_id, limit=limit, refresh=True, session_id=session_id)

    return handle


def viral_dispatch_handler(*, app: FastAPI) -> TopicHandler:
    def handle(session: Session, envelope: dict[str, Any]) -> None:
        del session
        payload = dict(envelope.get("payload") or {})
        clip_id = _dispatch_clip_id(payload)
        if clip_id is None:
            return
        occurred_at_raw = envelope.get("timestamp")
        occurred_at = datetime.now(UTC)
        if isinstance(occurred_at_raw, str) and occurred_at_raw.strip():
            try:
                parsed = datetime.fromisoformat(occurred_at_raw)
                occurred_at = parsed.astimezone(UTC) if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)
            except ValueError:
                occurred_at = datetime.now(UTC)
        event = DomainEvent(
            name=str(envelope.get("event_type") or "viral.clip.dispatch.requested"),
            payload=payload,
            event_id=str(envelope.get("event_id") or ""),
            occurred_at=occurred_at,
            aggregate_id=str(envelope.get("aggregate_id") or "") or None,
            aggregate_type=str(envelope.get("aggregate_type") or "") or None,
            producer=str(envelope.get("producer") or "") or None,
            partition_key=str(envelope.get("partition_key") or "") or None,
            headers=dict(envelope.get("headers") or {}),
        )
        inject_into_distribution_pool(
            clip_id=clip_id,
            score=_dispatch_initial_score(payload),
            payload=_normalize_dispatch_payload(
                event=event,
                clip_id=clip_id,
                payload=payload,
                initial_score=_dispatch_initial_score(payload),
            ),
            store=ensure_viral_dispatch_pool_store(app, settings=getattr(app.state, "settings", None)),
        )

    return handle


def ads_refresh_handler(*, app: FastAPI) -> TopicHandler:
    def handle(session: Session, envelope: dict[str, Any]) -> None:
        payload = dict(envelope.get("payload") or {})
        ad_id = str(payload.get("ad_id") or "").strip()
        if not ad_id:
            return
        SponsoredClipService(session=session, app=app).sync_cached_ad(ad_id)

    return handle


def creator_earnings_handler() -> TopicHandler:
    def handle(session: Session, envelope: dict[str, Any]) -> None:
        payload = dict(envelope.get("payload") or {})
        creator_user_id = str(payload.get("creator_user_id") or "").strip()
        if not creator_user_id:
            return
        CreatorClipEarningsProjectionService(session).refresh(creator_user_id=creator_user_id)

    return handle


__all__ = [
    "ScaleTopicConsumerService",
    "ads_refresh_handler",
    "build_worker_app",
    "creator_earnings_handler",
    "feed_refresh_handler",
    "viral_dispatch_handler",
]
