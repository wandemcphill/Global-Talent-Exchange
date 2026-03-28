from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from threading import RLock
from typing import Any

from app.core.events import DomainEvent
from app.realtime.websocket_gateway import (
    MatchGatewayMetrics,
    MatchWebsocketGateway,
    WalletGatewayMetrics,
    WalletWebsocketGateway,
)


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
class RealtimeHub:
    total_events: int = 0
    channels: dict[str, int] = field(default_factory=dict)
    last_event_name: str | None = None
    last_event_at: datetime | None = None
    wallet_gateway: WalletWebsocketGateway = field(default_factory=WalletWebsocketGateway)
    match_gateway: MatchWebsocketGateway = field(default_factory=MatchWebsocketGateway)
    _lock: RLock = field(default_factory=RLock)

    def handle_event(self, event: DomainEvent) -> None:
        channel = event.name.split(".", maxsplit=1)[0]
        with self._lock:
            self.total_events += 1
            self.channels[channel] = self.channels.get(channel, 0) + 1
            self.last_event_name = event.name
            self.last_event_at = event.occurred_at
        self.wallet_gateway.handle_event(event)
        self.match_gateway.handle_event(event)

    def register_wallet_connection(self) -> None:
        self.wallet_gateway.register_connection()

    def unregister_wallet_connection(self) -> None:
        self.wallet_gateway.unregister_connection()

    def wallet_latest_cursor(self, user_id: str) -> int:
        return self.wallet_gateway.latest_cursor(user_id)

    def wallet_events_since(self, user_id: str, cursor: int) -> tuple[list[dict[str, Any]], int]:
        return self.wallet_gateway.events_since(user_id, cursor)

    def record_wallet_delivery(self, message_count: int = 1) -> None:
        self.wallet_gateway.record_delivery(message_count)

    def wallet_channel(self, user_id: str) -> str:
        return self.wallet_gateway.channel_for_user(user_id)

    def register_match_connection(self) -> None:
        self.match_gateway.register_connection()

    def unregister_match_connection(self) -> None:
        self.match_gateway.unregister_connection()

    def match_latest_cursor(self, match_id: str) -> int:
        return self.match_gateway.latest_cursor(match_id)

    def match_events_since(self, match_id: str, cursor: int) -> tuple[list[dict[str, Any]], int]:
        return self.match_gateway.events_since(match_id, cursor)

    def record_match_delivery(self, message_count: int = 1) -> None:
        self.match_gateway.record_delivery(message_count)

    def match_channel(self, match_id: str) -> str:
        return self.match_gateway.channel_for_match(match_id)

    def snapshot(self) -> RealtimeSnapshot:
        wallet_metrics: WalletGatewayMetrics = self.wallet_gateway.metrics()
        match_metrics: MatchGatewayMetrics = self.match_gateway.metrics()
        with self._lock:
            return RealtimeSnapshot(
                total_events=self.total_events,
                channels=dict(self.channels),
                last_event_name=self.last_event_name,
                last_event_at=self.last_event_at,
                active_wallet_connections=wallet_metrics.active_connections,
                tracked_wallet_streams=wallet_metrics.tracked_streams,
                active_match_connections=match_metrics.active_connections,
                tracked_match_streams=match_metrics.tracked_streams,
                delivered_messages=wallet_metrics.delivered_messages + match_metrics.delivered_messages,
            )
