from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
import logging
from threading import RLock
from typing import Any
from uuid import uuid4

from fastapi import WebSocket

from app.core.events import DomainEvent

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class RealtimeDispatch:
    type: str
    data: dict[str, Any]
    topics: tuple[str, ...]


@dataclass(slots=True)
class RealtimeSnapshot:
    total_events: int
    channels: dict[str, int]
    last_event_name: str | None
    last_event_at: datetime | None
    active_wallet_connections: int
    tracked_wallet_streams: int
    active_match_connections: int
    tracked_match_streams: int
    delivered_messages: int


@dataclass(slots=True)
class _RealtimeConnection:
    client_id: str
    websocket: WebSocket
    user_id: str | None
    topics: dict[str, None] = field(default_factory=dict)

    def subscribes_to(self, topic: str) -> bool:
        return topic in self.topics


def wallet_topic(user_id: str) -> str:
    return f"wallet:{user_id}"


def match_topic(match_id: str) -> str:
    return f"match:{match_id}"


def commentary_topic(match_id: str) -> str:
    return f"commentary:{match_id}"


class RealtimeHub:
    def __init__(self) -> None:
        self.total_events = 0
        self.channels: dict[str, int] = {}
        self.last_event_name: str | None = None
        self.last_event_at: datetime | None = None
        self._delivered_messages = 0
        self._connections: dict[str, _RealtimeConnection] = {}
        self._loop: asyncio.AbstractEventLoop | None = None
        self._sync_lock = RLock()
        self._connection_lock = asyncio.Lock()

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    async def shutdown(self) -> None:
        async with self._connection_lock:
            connections = list(self._connections.values())
            self._connections.clear()
        for connection in connections:
            try:
                await connection.websocket.close()
            except Exception:
                logger.debug("realtime.websocket.close_failed", exc_info=True)

    def handle_event(self, event: DomainEvent) -> None:
        channel = event.name.split(".", maxsplit=1)[0].lower()
        with self._sync_lock:
            self.total_events += 1
            self.channels[channel] = self.channels.get(channel, 0) + 1
            self.last_event_name = event.name
            self.last_event_at = event.occurred_at

        dispatches = self._map_domain_event(event)
        if not dispatches:
            return

        loop = self._loop
        if loop is None or loop.is_closed():
            logger.debug("realtime.dispatch.skipped reason=no_running_loop event=%s", event.name)
            return

        future = asyncio.run_coroutine_threadsafe(self._broadcast(dispatches), loop)
        future.add_done_callback(self._log_dispatch_failure)

    async def connect(
        self,
        websocket: WebSocket,
        *,
        user_id: str | None,
        topics: tuple[str, ...] = (),
    ) -> str:
        if self._loop is None or self._loop.is_closed():
            self._loop = asyncio.get_running_loop()
        await websocket.accept()
        client_id = uuid4().hex
        resolved_topics = self._resolve_topics(topics, user_id=user_id)
        async with self._connection_lock:
            self._connections[client_id] = _RealtimeConnection(
                client_id=client_id,
                websocket=websocket,
                user_id=user_id,
                topics=dict.fromkeys(resolved_topics),
            )
        return client_id

    async def disconnect(self, client_id: str) -> None:
        async with self._connection_lock:
            self._connections.pop(client_id, None)

    async def subscribe(
        self,
        client_id: str,
        *,
        topics: tuple[str, ...],
    ) -> tuple[str, ...]:
        async with self._connection_lock:
            connection = self._connections.get(client_id)
            if connection is None:
                return ()
            resolved = self._resolve_topics(topics, user_id=connection.user_id)
            for topic in resolved:
                connection.topics[topic] = None
            return tuple(connection.topics)

    async def unsubscribe(
        self,
        client_id: str,
        *,
        topics: tuple[str, ...],
    ) -> tuple[str, ...]:
        async with self._connection_lock:
            connection = self._connections.get(client_id)
            if connection is None:
                return ()
            resolved = self._resolve_topics(topics, user_id=connection.user_id)
            for topic in resolved:
                connection.topics.pop(topic, None)
            return tuple(connection.topics)

    def wallet_channel(self, user_id: str) -> str:
        return wallet_topic(user_id)

    def match_channel(self, match_id: str) -> str:
        return match_topic(match_id)

    def commentary_channel(self, match_id: str) -> str:
        return commentary_topic(match_id)

    def snapshot(self) -> RealtimeSnapshot:
        with self._sync_lock:
            try:
                connections = list(self._connections.values())
            except RuntimeError:
                connections = []
            wallet_connections = sum(1 for item in connections if any(topic.startswith("wallet:") for topic in item.topics))
            match_connections = sum(
                1 for item in connections if any(topic.startswith("match:") or topic.startswith("commentary:") for topic in item.topics)
            )
            tracked_wallet_streams = len(
                {
                    topic
                    for item in connections
                    for topic in item.topics
                    if topic.startswith("wallet:")
                }
            )
            tracked_match_streams = len(
                {
                    topic
                    for item in connections
                    for topic in item.topics
                    if topic.startswith("match:") or topic.startswith("commentary:")
                }
            )
            return RealtimeSnapshot(
                total_events=self.total_events,
                channels=dict(self.channels),
                last_event_name=self.last_event_name,
                last_event_at=self.last_event_at,
                active_wallet_connections=wallet_connections,
                tracked_wallet_streams=tracked_wallet_streams,
                active_match_connections=match_connections,
                tracked_match_streams=tracked_match_streams,
                delivered_messages=self._delivered_messages,
            )

    def _resolve_topics(self, topics: tuple[str, ...], *, user_id: str | None) -> tuple[str, ...]:
        resolved: list[str] = []
        for raw_topic in topics:
            topic = str(raw_topic or "").strip()
            if not topic:
                continue
            if topic == "wallet" and user_id is not None:
                resolved.append(wallet_topic(user_id))
                continue
            if topic.startswith("wallet:") and user_id is not None and topic == wallet_topic(user_id):
                resolved.append(topic)
                continue
            if topic.startswith("wallet:"):
                logger.warning("realtime.topic.denied topic=%s reason=wallet_scope", topic)
                continue
            resolved.append(topic)
        return tuple(dict.fromkeys(resolved))

    async def _broadcast(self, dispatches: list[RealtimeDispatch]) -> None:
        async with self._connection_lock:
            connections = list(self._connections.values())

        if not connections:
            return

        stale_client_ids: set[str] = set()
        delivered = 0
        for connection in connections:
            pending_payloads = [
                {"type": dispatch.type, "data": dict(dispatch.data)}
                for dispatch in dispatches
                if any(connection.subscribes_to(topic) for topic in dispatch.topics)
            ]
            if not pending_payloads:
                continue
            try:
                for payload in pending_payloads:
                    await connection.websocket.send_json(payload)
                    delivered += 1
            except Exception:
                stale_client_ids.add(connection.client_id)
                logger.warning(
                    "realtime.websocket.delivery_failed client_id=%s topic_count=%s",
                    connection.client_id,
                    len(connection.topics),
                    exc_info=True,
                )

        if stale_client_ids:
            async with self._connection_lock:
                for client_id in stale_client_ids:
                    self._connections.pop(client_id, None)

        if delivered > 0:
            with self._sync_lock:
                self._delivered_messages += delivered

    def _map_domain_event(self, event: DomainEvent) -> list[RealtimeDispatch]:
        payload = dict(event.payload or {})
        if event.name == "wallet.balance.updated":
            owner_user_id = _optional_string(payload.get("owner_user_id"))
            if owner_user_id is None:
                return []
            return [
                RealtimeDispatch(
                    type="wallet_update",
                    topics=(wallet_topic(owner_user_id),),
                    data={
                        "user_id": owner_user_id,
                        "transaction_id": payload.get("transaction_id"),
                        "account_id": payload.get("account_id"),
                        "account_code": payload.get("account_code"),
                        "balance": payload.get("balance"),
                        "unit": payload.get("unit"),
                    },
                )
            ]

        if event.name in {"market.trade.executed", "TRADE_EXECUTED", "PLAYER_VALUE_UPDATED"}:
            player_id = _optional_string(
                payload.get("player_id")
                or payload.get("asset_id")
                or event.aggregate_id
            )
            if player_id is None:
                return []
            price = (
                payload.get("current_price")
                or payload.get("updated_share_price_coin")
                or payload.get("price")
            )
            return [
                RealtimeDispatch(
                    type="market_price_update",
                    topics=("market",),
                    data={
                        "player_id": player_id,
                        "market_id": payload.get("market_id") or event.aggregate_id,
                        "trade_id": payload.get("trade_id") or payload.get("transaction_id"),
                        "side": payload.get("side"),
                        "price": price,
                        "previous_price": payload.get("previous_price") or payload.get("previous_share_price_coin"),
                        "shares": payload.get("shares") or payload.get("share_delta"),
                        "circulating_shares": payload.get("circulating_shares"),
                        "available_shares": payload.get("available_shares"),
                        "total_shares": payload.get("total_shares"),
                    },
                )
            ]

        if event.name == "match.events":
            match_id = _optional_string(
                payload.get("match_id")
                or payload.get("fixture_id")
                or payload.get("resource_id")
                or event.aggregate_id
            )
            if match_id is None:
                return []
            score_payload = {
                "match_id": match_id,
                "event_id": payload.get("event_id"),
                "minute": payload.get("minute"),
                "event_type": payload.get("event_type"),
                "source_event_type": payload.get("source_event_type"),
                "home_score": payload.get("home_score"),
                "away_score": payload.get("away_score"),
                "status": "live",
                "clock": payload.get("clock"),
                "team_id": payload.get("team_id"),
                "team_name": payload.get("team") or payload.get("team_name"),
            }
            dispatches = [
                RealtimeDispatch(
                    type="match_update",
                    topics=(match_topic(match_id),),
                    data=score_payload,
                )
            ]
            commentary = _optional_string(
                payload.get("commentary")
                or payload.get("description")
                or payload.get("source_commentary")
            )
            if commentary:
                dispatches.append(
                    RealtimeDispatch(
                        type="commentary",
                        topics=(commentary_topic(match_id),),
                        data={
                            **score_payload,
                            "commentary": commentary,
                            "player_id": payload.get("player_id"),
                            "player_name": payload.get("player") or payload.get("player_name"),
                            "secondary_player_id": payload.get("secondary_player_id"),
                            "secondary_player_name": payload.get("secondary_player") or payload.get("secondary_player_name"),
                        },
                    )
                )
            return dispatches

        if event.name.startswith("competition.match."):
            match_id = _optional_string(
                payload.get("fixture_id")
                or payload.get("match_id")
                or payload.get("resource_id")
                or event.aggregate_id
            )
            competition_id = _optional_string(payload.get("competition_id"))
            dispatches: list[RealtimeDispatch] = []
            if match_id is not None:
                dispatches.append(
                    RealtimeDispatch(
                        type="match_update",
                        topics=(match_topic(match_id),),
                        data={
                            "match_id": match_id,
                            "competition_id": competition_id,
                            "status": payload.get("result_status") or payload.get("status") or payload.get("live"),
                            "event_name": event.name,
                            "home_score": payload.get("home_score"),
                            "away_score": payload.get("away_score"),
                            "minute": payload.get("minute"),
                        },
                    )
                )
            if competition_id is not None:
                dispatches.append(
                    RealtimeDispatch(
                        type="competition_update",
                        topics=("competition",),
                        data={
                            "competition_id": competition_id,
                            "match_id": match_id,
                            "event_name": event.name,
                            "status": payload.get("status") or payload.get("result_status"),
                        },
                    )
                )
            return dispatches

        if event.name.startswith("competition.") or event.name in {"competition_created", "competition_updated"}:
            competition_id = _optional_string(
                payload.get("competition_id")
                or payload.get("resource_id")
                or event.aggregate_id
            )
            if competition_id is None:
                return []
            return [
                RealtimeDispatch(
                    type="competition_update",
                    topics=("competition",),
                    data={
                        "competition_id": competition_id,
                        "event_name": event.name,
                        "status": payload.get("status"),
                        "stage": payload.get("stage"),
                        "participant_count": payload.get("participant_count"),
                        "match_id": payload.get("match_id"),
                    },
                )
            ]

        return []

    @staticmethod
    def _log_dispatch_failure(future: Any) -> None:
        try:
            future.result()
        except Exception:
            logger.exception("realtime.dispatch.failed")


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    resolved = str(value).strip()
    return resolved or None


__all__ = [
    "RealtimeDispatch",
    "RealtimeHub",
    "RealtimeSnapshot",
    "commentary_topic",
    "match_topic",
    "wallet_topic",
]
