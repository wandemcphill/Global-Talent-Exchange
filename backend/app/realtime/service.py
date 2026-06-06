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
from app.realtime.match_stream_service import match_event_channel

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


def admin_topic(user_id: str) -> str:
    return f"admin:{user_id}"


def match_topic(match_id: str) -> str:
    return match_event_channel(match_id)


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
            wallet_connections = sum(
                1 for item in connections if any(topic.startswith("wallet:") for topic in item.topics)
            )
            match_connections = sum(
                1
                for item in connections
                if any(topic.startswith("match:") or topic.startswith("commentary:") for topic in item.topics)
            )
            tracked_wallet_streams = len(
                {topic for item in connections for topic in item.topics if topic.startswith("wallet:")}
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
            if topic == "admin" and user_id is not None:
                resolved.append(admin_topic(user_id))
                continue
            if topic.startswith("admin:") and user_id is not None and topic == admin_topic(user_id):
                resolved.append(topic)
                continue
            if topic.startswith("admin:"):
                logger.warning("realtime.topic.denied topic=%s reason=admin_scope", topic)
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

        if event.name.startswith("regen.creation_order."):
            user_id = _optional_string(payload.get("user_id"))
            order_id = _optional_string(payload.get("order_id") or event.aggregate_id)
            if user_id is None or order_id is None:
                return []
            data = {
                "event_name": event.name,
                "order_id": order_id,
                "user_id": user_id,
                "actor_user_id": payload.get("actor_user_id"),
                "club_id": payload.get("club_id"),
                "request_type": payload.get("request_type"),
                "status": payload.get("status"),
                "previous_status": payload.get("previous_status"),
                "payment_method": payload.get("payment_method"),
                "payment_provider": payload.get("payment_provider"),
                "payment_reference": payload.get("payment_reference"),
                "wallet_reservation": payload.get("wallet_reservation"),
                "generated_player_id": payload.get("generated_player_id"),
                "generated_regen_profile_id": payload.get("generated_regen_profile_id"),
                "amount_coin": payload.get("amount_coin"),
                "currency": payload.get("currency"),
                "audit_reference": payload.get("audit_reference"),
            }
            dispatches = [
                RealtimeDispatch(
                    type="regen_creation_order_update",
                    topics=(wallet_topic(user_id),),
                    data=data,
                )
            ]
            action = event.name.rsplit(".", maxsplit=1)[-1]
            if action in {"generated", "cancelled"}:
                message = (
                    "Build-a-Son generation completed."
                    if action == "generated"
                    else "Build-a-Son wallet reservation was cancelled."
                )
                dispatches.append(
                    RealtimeDispatch(
                        type="notification",
                        topics=(wallet_topic(user_id),),
                        data={
                            "user_id": user_id,
                            "topic": "regen_creation",
                            "template_key": f"REGEN_CREATION_ORDER_{action.upper()}",
                            "resource_type": "regen_creation_order",
                            "resource_id": order_id,
                            "message": message,
                            "metadata": data,
                        },
                    )
                )
            return dispatches

        if event.name in {"admin.export.ready", "admin.export.blocked", "admin.export.failed"}:
            export_id = _optional_string(payload.get("export_id") or event.aggregate_id)
            admin_user_id = _optional_string(
                payload.get("admin_user_id") or payload.get("actor_user_id") or payload.get("requested_by_user_id")
            )
            if export_id is None or admin_user_id is None:
                return []
            artifact = payload.get("artifact")
            artifact_payload = (
                {key: value for key, value in artifact.items() if key != "content"}
                if isinstance(artifact, dict)
                else None
            )
            status = _optional_string(payload.get("status")) or event.name.rsplit(".", maxsplit=1)[-1]
            data = {
                "event_name": event.name,
                "export_id": export_id,
                "admin_user_id": admin_user_id,
                "status": status,
                "export_type": payload.get("export_type"),
                "format": payload.get("format"),
                "requested_at": payload.get("requested_at"),
                "completed_at": payload.get("completed_at"),
                "download_url": payload.get("download_url"),
                "blocked_reason": payload.get("blocked_reason"),
                "failure_reason": payload.get("failure_reason"),
                "audit_reference": payload.get("audit_reference"),
                "requested_audit_reference": payload.get("requested_audit_reference"),
                "artifact": artifact_payload,
                "backend_authored": True,
            }
            return [
                RealtimeDispatch(
                    type=f"admin_export_{status}",
                    topics=(admin_topic(admin_user_id),),
                    data=data,
                )
            ]

        if event.name == "JACKPOT_TRIGGERED":
            dispatches: list[RealtimeDispatch] = []
            for winner in payload.get("winners") or []:
                if not isinstance(winner, dict):
                    continue
                winner_user_id = _optional_string(winner.get("user_id"))
                if winner_user_id is None:
                    continue
                amount = winner.get("amount")
                dispatches.append(
                    RealtimeDispatch(
                        type="jackpot_triggered",
                        topics=(wallet_topic(winner_user_id),),
                        data={
                            "user_id": winner_user_id,
                            "round_id": payload.get("round_id") or event.aggregate_id,
                            "round_number": payload.get("round_number"),
                            "trigger_mode": payload.get("trigger_mode"),
                            "amount": amount,
                            "unit": "coin",
                        },
                    )
                )
                dispatches.append(
                    RealtimeDispatch(
                        type="notification",
                        topics=(wallet_topic(winner_user_id),),
                        data={
                            "user_id": winner_user_id,
                            "topic": "jackpot",
                            "template_key": "JACKPOT_DROPPED",
                            "resource_type": "jackpot_round",
                            "resource_id": payload.get("round_id") or event.aggregate_id,
                            "message": f"Jackpot dropped: {amount} GTEX Coin has been credited to your wallet.",
                            "metadata": {
                                "round_id": payload.get("round_id") or event.aggregate_id,
                                "round_number": payload.get("round_number"),
                                "trigger_mode": payload.get("trigger_mode"),
                                "amount": amount,
                            },
                        },
                    )
                )
            return dispatches

        if event.name in {"market.trade.executed", "TRADE_EXECUTED", "PLAYER_VALUE_UPDATED"}:
            player_id = _optional_string(payload.get("player_id") or payload.get("asset_id") or event.aggregate_id)
            if player_id is None:
                return []
            price = payload.get("current_price") or payload.get("updated_share_price_coin") or payload.get("price")
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
                payload.get("match_id") or payload.get("fixture_id") or payload.get("resource_id") or event.aggregate_id
            )
            if match_id is None:
                return []
            commentary = _optional_string(
                payload.get("commentary") or payload.get("description") or payload.get("source_commentary")
            )
            stats = _payload_mapping(payload, "stats")
            xg = _payload_mapping(payload, "xg")
            momentum = _payload_mapping(payload, "momentum")
            overlay_readiness = _payload_mapping(payload, "overlay_readiness", "overlayReadiness")
            inspector_state = _payload_mapping(payload, "inspector_state", "inspectorState")
            intelligence_state = _payload_mapping(payload, "intelligence_state", "intelligenceState")
            missing_data = _match_missing_data(
                payload,
                commentary=commentary,
                stats=stats,
                xg=xg,
                momentum=momentum,
                overlay_readiness=overlay_readiness,
                inspector_state=inspector_state,
                intelligence_state=intelligence_state,
            )
            data_status = _most_restrictive_status(
                payload.get("data_status"),
                _status_from_missing_data(missing_data),
            )
            blocked = bool(payload.get("blocked")) or any(item.get("severity") == "blocked" for item in missing_data)
            degraded = bool(payload.get("degraded")) or any(
                item.get("severity") in {"degraded", "syncing", "empty"} for item in missing_data
            )
            score_fields_present = _payload_has_value(payload, "home_score") and _payload_has_value(
                payload,
                "away_score",
            )
            clock_field_present = _payload_has_value(payload, "clock")
            minute_field_present = _payload_has_value(payload, "minute")
            commentary_present = commentary is not None
            score_authoritative = (
                bool(payload.get("score_authoritative", score_fields_present)) and score_fields_present
            )
            clock_authoritative = bool(payload.get("clock_authoritative", clock_field_present)) and clock_field_present
            minute_authoritative = (
                bool(payload.get("minute_authoritative", minute_field_present)) and minute_field_present
            )
            commentary_authoritative = (
                bool(payload.get("commentary_authoritative", commentary_present)) and commentary_present
            )
            score_payload = {
                "match_id": match_id,
                "channel": match_topic(match_id),
                "event_id": payload.get("event_id"),
                "minute": payload.get("minute"),
                "event_type": payload.get("event_type"),
                "source_event_type": payload.get("source_event_type"),
                "home_score": payload.get("home_score"),
                "away_score": payload.get("away_score"),
                "status": payload.get("status") or payload.get("result_status"),
                "clock": payload.get("clock"),
                "team_id": payload.get("team_id"),
                "team_name": payload.get("team") or payload.get("team_name"),
                "player_id": payload.get("player_id"),
                "player_name": payload.get("player") or payload.get("player_name"),
                "secondary_player_id": payload.get("secondary_player_id"),
                "secondary_player_name": payload.get("secondary_player") or payload.get("secondary_player_name"),
                "commentary": commentary,
                "description": commentary,
                "score_authoritative": score_authoritative,
                "clock_authoritative": clock_authoritative,
                "minute_authoritative": minute_authoritative,
                "commentary_authoritative": commentary_authoritative,
                "stats_authoritative": bool(payload.get("stats_authoritative", stats is not None)) and stats is not None,
                "xg_authoritative": bool(payload.get("xg_authoritative", xg is not None)) and xg is not None,
                "momentum_authoritative": (
                    bool(payload.get("momentum_authoritative", momentum is not None)) and momentum is not None
                ),
                "overlay_authoritative": (
                    bool(payload.get("overlay_authoritative", overlay_readiness is not None))
                    and overlay_readiness is not None
                ),
                "inspector_authoritative": (
                    bool(payload.get("inspector_authoritative", inspector_state is not None))
                    and inspector_state is not None
                ),
                "intelligence_authoritative": (
                    bool(payload.get("intelligence_authoritative", intelligence_state is not None))
                    and intelligence_state is not None
                ),
                "data_status": data_status,
                "missing_data": missing_data,
                "degraded": degraded,
                "blocked": blocked,
                "stats": stats,
                "xg": xg,
                "momentum": momentum,
                "overlay_readiness": overlay_readiness,
                "inspector_state": inspector_state,
                "intelligence_state": intelligence_state,
                "backend_authored": True,
            }
            dispatches = [
                RealtimeDispatch(
                    type="match_update",
                    topics=(match_topic(match_id),),
                    data=score_payload,
                ),
                RealtimeDispatch(
                    type="match_event",
                    topics=(match_topic(match_id),),
                    data=score_payload,
                ),
            ]
            if commentary:
                dispatches.append(
                    RealtimeDispatch(
                        type="commentary",
                        topics=(commentary_topic(match_id),),
                        data={
                            **score_payload,
                        },
                    )
                )
            return dispatches

        if event.name.startswith("competition.match."):
            match_id = _optional_string(
                payload.get("fixture_id") or payload.get("match_id") or payload.get("resource_id") or event.aggregate_id
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
                payload.get("competition_id") or payload.get("resource_id") or event.aggregate_id
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


def _payload_has_value(payload: dict[str, Any], key: str) -> bool:
    if key not in payload:
        return False
    value = payload.get(key)
    if value is None:
        return False
    if isinstance(value, str) and not value.strip():
        return False
    return True


def _payload_mapping(payload: dict[str, Any], key: str, *aliases: str) -> dict[str, Any] | None:
    metadata = payload.get("metadata")
    sources = [payload]
    if isinstance(metadata, dict):
        sources.append(metadata)
    for source in sources:
        for candidate_key in (key, *aliases):
            value = source.get(candidate_key)
            if isinstance(value, dict) and value:
                return dict(value)
    return None


def _append_missing_data_once(
    missing_data: list[dict[str, Any]],
    *,
    code: str,
    field: str,
    severity: str,
    message: str,
) -> None:
    if any(item.get("code") == code and item.get("field") == field for item in missing_data):
        return
    missing_data.append({"code": code, "field": field, "severity": severity, "message": message})


def _match_missing_data(
    payload: dict[str, Any],
    *,
    commentary: str | None,
    stats: dict[str, Any] | None,
    xg: dict[str, Any] | None,
    momentum: dict[str, Any] | None,
    overlay_readiness: dict[str, Any] | None,
    inspector_state: dict[str, Any] | None,
    intelligence_state: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    raw_missing_data = payload.get("missing_data")
    missing_data = (
        [dict(item) for item in raw_missing_data if isinstance(item, dict)]
        if isinstance(raw_missing_data, list)
        else []
    )
    if not (_payload_has_value(payload, "home_score") and _payload_has_value(payload, "away_score")):
        _append_missing_data_once(
            missing_data,
            code="missing_authoritative_score",
            field="score",
            severity="blocked",
            message="The realtime match event did not include an authoritative scoreline.",
        )
    if not _payload_has_value(payload, "minute"):
        _append_missing_data_once(
            missing_data,
            code="missing_authoritative_minute",
            field="minute",
            severity="blocked",
            message="The realtime match event did not include an authoritative match minute.",
        )
    if not _payload_has_value(payload, "clock"):
        _append_missing_data_once(
            missing_data,
            code="missing_authoritative_clock",
            field="clock",
            severity="degraded",
            message="The realtime match event did not include an authoritative match clock.",
        )
    if commentary is None:
        _append_missing_data_once(
            missing_data,
            code="missing_authoritative_commentary",
            field="commentary",
            severity="degraded",
            message="The realtime match event did not include authored commentary.",
        )
    if stats is None:
        _append_missing_data_once(
            missing_data,
            code="missing_authoritative_stats",
            field="stats",
            severity="degraded",
            message="The realtime match event did not include authoritative live stats.",
        )
    if xg is None:
        _append_missing_data_once(
            missing_data,
            code="missing_authoritative_xg",
            field="xg",
            severity="degraded",
            message="The realtime match event did not include authoritative xG.",
        )
    if momentum is None:
        _append_missing_data_once(
            missing_data,
            code="missing_authoritative_momentum",
            field="momentum",
            severity="degraded",
            message="The realtime match event did not include authoritative momentum.",
        )
    if overlay_readiness is None:
        _append_missing_data_once(
            missing_data,
            code="missing_overlay_readiness",
            field="overlay_readiness",
            severity="degraded",
            message="The realtime match event did not include overlay readiness.",
        )
    if inspector_state is None:
        _append_missing_data_once(
            missing_data,
            code="missing_inspector_state",
            field="inspector_state",
            severity="degraded",
            message="The realtime match event did not include inspector state.",
        )
    if intelligence_state is None:
        _append_missing_data_once(
            missing_data,
            code="missing_intelligence_state",
            field="intelligence_state",
            severity="degraded",
            message="The realtime match event did not include intelligence state.",
        )
    return missing_data


def _status_from_missing_data(missing_data: list[dict[str, Any]]) -> str:
    severities = {str(item.get("severity") or "").strip().lower() for item in missing_data}
    if "blocked" in severities:
        return "blocked"
    if "degraded" in severities:
        return "degraded"
    if "empty" in severities:
        return "empty"
    if "syncing" in severities:
        return "syncing"
    return "ready"


def _most_restrictive_status(*statuses: Any) -> str:
    order = {
        "ready": 0,
        "syncing": 1,
        "empty": 1,
        "degraded": 2,
        "blocked": 3,
    }
    resolved = [str(status or "").strip().lower() for status in statuses if str(status or "").strip().lower() in order]
    if not resolved:
        return "ready"
    return max(resolved, key=lambda status: order[status])


__all__ = [
    "RealtimeDispatch",
    "RealtimeHub",
    "RealtimeSnapshot",
    "admin_topic",
    "commentary_topic",
    "match_topic",
    "wallet_topic",
]
