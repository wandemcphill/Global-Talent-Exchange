from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
import json
import logging
from typing import Any
from uuid import uuid4

from redis import Redis
from redis.exceptions import RedisError

from app.core.event_backbone import make_json_safe
from app.core.events import DomainEvent, EventPublisher
from app.match_engine.schemas import MatchEventView, MatchReplayPayloadView
from app.realtime.commentary_engine import CommentaryEngine, DEFAULT_STYLE

logger = logging.getLogger(__name__)


def match_event_channel(match_id: str) -> str:
    return f"match:{match_id}:events"


class MatchStreamService:
    def __init__(
        self,
        *,
        redis_url: str | None,
        event_publisher: EventPublisher | None = None,
        commentary_engine: CommentaryEngine | None = None,
        default_style: str = DEFAULT_STYLE,
    ) -> None:
        self._redis_url = redis_url
        self._event_publisher = event_publisher
        self._commentary_engine = commentary_engine or CommentaryEngine()
        self._default_style = self._commentary_engine.resolve_style(default_style)
        self._redis: Redis | None = None
        if redis_url:
            try:
                self._redis = Redis.from_url(redis_url, decode_responses=True)
            except RedisError:
                logger.exception("realtime.match_stream.redis_unavailable")
                self._redis = None

    @classmethod
    def from_settings(
        cls,
        settings: Any,
        *,
        event_publisher: EventPublisher | None = None,
    ) -> MatchStreamService:
        return cls(
            redis_url=getattr(settings, "redis_url", None),
            event_publisher=event_publisher,
        )

    def publish_event(
        self,
        match_id: str,
        event: Mapping[str, Any],
        *,
        style: str | None = None,
    ) -> dict[str, Any]:
        envelope = self.build_stream_message(match_id, event, style=style)
        if self._event_publisher is not None:
            self._event_publisher.publish(
                DomainEvent(
                    name="match.events",
                    payload=dict(envelope),
                    aggregate_id=match_id,
                    aggregate_type="match",
                    partition_key=match_id,
                    producer="match-stream-service",
                )
            )
            self._publish_feed_injection(match_id=match_id, envelope=envelope)
        if self._redis is None:
            return envelope
        try:
            self._redis.publish(
                match_event_channel(match_id),
                json.dumps(make_json_safe(envelope)),
            )
        except RedisError:
            logger.exception("realtime.match_stream.publish_failed channel=%s", match_event_channel(match_id))
        return envelope

    def publish_replay_timeline(
        self,
        *,
        match_id: str,
        replay_payload: MatchReplayPayloadView,
        home_team_name: str | None = None,
        away_team_name: str | None = None,
        style: str | None = None,
    ) -> list[dict[str, Any]]:
        published: list[dict[str, Any]] = []
        for event in replay_payload.timeline.events:
            published.append(
                self.publish_event(
                    match_id,
                    self._normalize_replay_event(
                        match_id=match_id,
                        event=event,
                        home_team_name=home_team_name,
                        away_team_name=away_team_name,
                    ),
                    style=style,
                )
            )
        return published

    def build_stream_message(
        self,
        match_id: str,
        event: Mapping[str, Any],
        *,
        style: str | None = None,
    ) -> dict[str, Any]:
        normalized = self._normalize_event(match_id=match_id, event=event)
        commentary_styles = self._commentary_engine.render_variations(normalized, match_id=match_id)
        selected_style = self._commentary_engine.resolve_style(style or self._default_style)
        authored_commentary = normalized["source_commentary"]
        commentary = authored_commentary
        return {
            "message_type": "match_event",
            "match_id": match_id,
            "channel": match_event_channel(match_id),
            "event_id": normalized["event_id"],
            "event_type": normalized["type"],
            "source_event_type": normalized["source_event_type"],
            "minute": normalized["minute"],
            "clock": normalized["clock"],
            "team_id": normalized["team_id"],
            "team": normalized["team"],
            "player_id": normalized["player_id"],
            "player": normalized["player"],
            "secondary_player_id": normalized["secondary_player_id"],
            "secondary_player": normalized["secondary_player"],
            "home_score": normalized["home_score"],
            "away_score": normalized["away_score"],
            "commentary": commentary,
            "commentary_style": selected_style,
            "commentary_styles": commentary_styles,
            "source_commentary": normalized["source_commentary"],
            "score_authoritative": normalized["score_authoritative"],
            "clock_authoritative": normalized["clock_authoritative"],
            "minute_authoritative": normalized["minute_authoritative"],
            "commentary_authoritative": normalized["commentary_authoritative"],
            "stats_authoritative": normalized["stats_authoritative"],
            "xg_authoritative": normalized["xg_authoritative"],
            "momentum_authoritative": normalized["momentum_authoritative"],
            "overlay_authoritative": normalized["overlay_authoritative"],
            "inspector_authoritative": normalized["inspector_authoritative"],
            "intelligence_authoritative": normalized["intelligence_authoritative"],
            "data_status": normalized["data_status"],
            "missing_data": normalized["missing_data"],
            "degraded": normalized["degraded"],
            "blocked": normalized["blocked"],
            "stats": normalized["stats"],
            "xg": normalized["xg"],
            "momentum": normalized["momentum"],
            "overlay_readiness": normalized["overlay_readiness"],
            "inspector_state": normalized["inspector_state"],
            "intelligence_state": normalized["intelligence_state"],
            "backend_authored": True,
            "metadata": normalized["metadata"],
            "published_at": datetime.now(UTC).isoformat(),
        }

    def close(self) -> None:
        if self._redis is None:
            return
        try:
            self._redis.close()
        except RedisError:
            logger.exception("realtime.match_stream.close_failed")

    def _publish_feed_injection(self, *, match_id: str, envelope: Mapping[str, Any]) -> None:
        if self._event_publisher is None or not self._is_feed_moment(envelope):
            return
        metadata = dict(envelope.get("metadata") or {})
        metadata["source"] = "moment"
        metadata["stream_channel"] = envelope.get("channel")
        self._event_publisher.publish(
            DomainEvent(
                name="feed.inject.moment",
                payload={
                    **dict(envelope),
                    "source": "moment",
                    "metadata": metadata,
                },
                aggregate_id=match_id,
                aggregate_type="match",
                partition_key=match_id,
                producer="match-stream-service",
            )
        )

    def _normalize_event(self, *, match_id: str, event: Mapping[str, Any]) -> dict[str, Any]:
        payload = make_json_safe(dict(event))
        event_type = self._map_event_type(payload.get("type") or payload.get("event_type"))
        minute = _optional_int(payload.get("minute"))
        clock = _optional_string(payload.get("clock") or payload.get("clock_label"))
        home_score = _optional_int(payload.get("home_score"))
        away_score = _optional_int(payload.get("away_score"))
        source_commentary = _optional_string(
            payload.get("source_commentary") or payload.get("commentary") or payload.get("description")
        )
        stats = _payload_mapping(payload, "stats")
        xg = _payload_mapping(payload, "xg")
        momentum = _payload_mapping(payload, "momentum")
        overlay_readiness = _payload_mapping(payload, "overlay_readiness", "overlayReadiness")
        inspector_state = _payload_mapping(payload, "inspector_state", "inspectorState")
        intelligence_state = _payload_mapping(payload, "intelligence_state", "intelligenceState")
        missing_data = _match_missing_data(
            payload,
            minute=minute,
            clock=clock,
            home_score=home_score,
            away_score=away_score,
            commentary=source_commentary,
            stats=stats,
            xg=xg,
            momentum=momentum,
            overlay_readiness=overlay_readiness,
            inspector_state=inspector_state,
            intelligence_state=intelligence_state,
        )
        return {
            "event_id": str(payload.get("event_id") or uuid4().hex),
            "match_id": match_id,
            "type": event_type,
            "source_event_type": str(payload.get("event_type") or payload.get("type") or event_type),
            "minute": minute,
            "clock": clock,
            "team_id": _optional_string(payload.get("team_id")),
            "team": _optional_string(payload.get("team") or payload.get("team_name") or payload.get("club_name")),
            "player_id": _optional_string(payload.get("player_id")),
            "player": _optional_string(payload.get("player") or payload.get("player_name")),
            "secondary_player_id": _optional_string(payload.get("secondary_player_id")),
            "secondary_player": _optional_string(
                payload.get("secondary_player") or payload.get("secondary_player_name")
            ),
            "home_team": _optional_string(payload.get("home_team")),
            "away_team": _optional_string(payload.get("away_team")),
            "home_score": home_score,
            "away_score": away_score,
            "source_commentary": source_commentary,
            "score_authoritative": home_score is not None and away_score is not None,
            "clock_authoritative": clock is not None,
            "minute_authoritative": minute is not None,
            "commentary_authoritative": source_commentary is not None,
            "stats_authoritative": stats is not None,
            "xg_authoritative": xg is not None,
            "momentum_authoritative": momentum is not None,
            "overlay_authoritative": overlay_readiness is not None,
            "inspector_authoritative": inspector_state is not None,
            "intelligence_authoritative": intelligence_state is not None,
            "data_status": _status_from_missing_data(missing_data),
            "missing_data": missing_data,
            "degraded": any(item.get("severity") in {"degraded", "syncing", "empty"} for item in missing_data),
            "blocked": any(item.get("severity") == "blocked" for item in missing_data),
            "stats": stats,
            "xg": xg,
            "momentum": momentum,
            "overlay_readiness": overlay_readiness,
            "inspector_state": inspector_state,
            "intelligence_state": intelligence_state,
            "metadata": dict(payload.get("metadata") or {}),
        }

    def _normalize_replay_event(
        self,
        *,
        match_id: str,
        event: MatchEventView,
        home_team_name: str | None,
        away_team_name: str | None,
    ) -> dict[str, Any]:
        return self._normalize_event(
            match_id=match_id,
            event={
                "event_id": event.event_id,
                "event_type": getattr(event.event_type, "value", event.event_type),
                "minute": event.minute,
                "clock": event.clock_label,
                "team_id": event.team_id,
                "team_name": event.team_name,
                "player_id": event.primary_player.player_id if event.primary_player is not None else None,
                "player_name": event.primary_player.player_name if event.primary_player is not None else None,
                "secondary_player_id": event.secondary_player.player_id if event.secondary_player is not None else None,
                "secondary_player_name": (
                    event.secondary_player.player_name if event.secondary_player is not None else None
                ),
                "home_team": home_team_name,
                "away_team": away_team_name,
                "home_score": event.home_score,
                "away_score": event.away_score,
                "source_commentary": event.commentary,
                "metadata": event.metadata,
            },
        )

    @staticmethod
    def _map_event_type(value: Any) -> str:
        candidate = str(value or "generic").strip().lower()
        mapping = {
            "goalkeeper_save": "save",
            "double_save": "save",
            "save": "save",
            "goal": "goal",
            "penalty_scored": "goal",
            "penalty_goal": "goal",
            "penalty_missed": "save",
            "penalty_miss": "miss",
            "missed_chance": "miss",
            "missed_big_chance": "miss",
            "woodwork": "miss",
            "foul": "foul",
            "tactical_foul": "foul",
            "yellow_card": "foul",
            "red_card": "foul",
            "pass": "pass",
        }
        return mapping.get(candidate, candidate)

    @staticmethod
    def _is_feed_moment(envelope: Mapping[str, Any]) -> bool:
        candidate = str(envelope.get("source_event_type") or envelope.get("event_type") or "").strip().lower()
        return candidate in {
            "goal",
            "penalty_goal",
            "penalty_scored",
            "red_card",
            "red_cards",
            "penalty_awarded",
            "penalty_missed",
            "penalty_miss",
        }


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    resolved = str(value).strip()
    return resolved or None


def _optional_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, str) and not value.strip():
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_mapping(value: Any) -> dict[str, Any] | None:
    if isinstance(value, Mapping) and value:
        return dict(value)
    return None


def _payload_mapping(payload: Mapping[str, Any], key: str, *aliases: str) -> dict[str, Any] | None:
    metadata = payload.get("metadata")
    sources = [payload]
    if isinstance(metadata, Mapping):
        sources.append(metadata)
    for source in sources:
        for candidate_key in (key, *aliases):
            resolved = _optional_mapping(source.get(candidate_key))
            if resolved is not None:
                return resolved
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
    minute: int | None,
    clock: str | None,
    home_score: int | None,
    away_score: int | None,
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
    if home_score is None or away_score is None:
        _append_missing_data_once(
            missing_data,
            code="missing_authoritative_score",
            field="score",
            severity="blocked",
            message="The backend match stream event did not include an authoritative scoreline.",
        )
    if minute is None:
        _append_missing_data_once(
            missing_data,
            code="missing_authoritative_minute",
            field="minute",
            severity="blocked",
            message="The backend match stream event did not include an authoritative match minute.",
        )
    if clock is None:
        _append_missing_data_once(
            missing_data,
            code="missing_authoritative_clock",
            field="clock",
            severity="degraded",
            message="The backend match stream event did not include an authoritative match clock.",
        )
    if commentary is None:
        _append_missing_data_once(
            missing_data,
            code="missing_authoritative_commentary",
            field="commentary",
            severity="degraded",
            message="The backend match stream event did not include authored commentary.",
        )
    if stats is None:
        _append_missing_data_once(
            missing_data,
            code="missing_authoritative_stats",
            field="stats",
            severity="degraded",
            message="The backend match stream event did not include authoritative live stats.",
        )
    if xg is None:
        _append_missing_data_once(
            missing_data,
            code="missing_authoritative_xg",
            field="xg",
            severity="degraded",
            message="The backend match stream event did not include authoritative xG.",
        )
    if momentum is None:
        _append_missing_data_once(
            missing_data,
            code="missing_authoritative_momentum",
            field="momentum",
            severity="degraded",
            message="The backend match stream event did not include authoritative momentum.",
        )
    if overlay_readiness is None:
        _append_missing_data_once(
            missing_data,
            code="missing_overlay_readiness",
            field="overlay_readiness",
            severity="degraded",
            message="The backend match stream event did not include overlay readiness.",
        )
    if inspector_state is None:
        _append_missing_data_once(
            missing_data,
            code="missing_inspector_state",
            field="inspector_state",
            severity="degraded",
            message="The backend match stream event did not include inspector state.",
        )
    if intelligence_state is None:
        _append_missing_data_once(
            missing_data,
            code="missing_intelligence_state",
            field="intelligence_state",
            severity="degraded",
            message="The backend match stream event did not include intelligence state.",
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


__all__ = ["MatchStreamService", "match_event_channel"]
