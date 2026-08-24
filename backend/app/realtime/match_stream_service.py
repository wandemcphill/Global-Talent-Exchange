from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
import json
import logging
from typing import Any

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
        for sequence, event in enumerate(replay_payload.timeline.events, start=1):
            published.append(
                self.publish_event(
                    match_id,
                    self._normalize_replay_event(
                        match_id=match_id,
                        event=event,
                        home_team_name=home_team_name,
                        away_team_name=away_team_name,
                        sequence=sequence,
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
        return {
            "message_type": "match_event",
            "match_id": match_id,
            "channel": match_event_channel(match_id),
            "event_id": normalized["event_id"],
            "sequence": normalized["sequence"],
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
            "commentary": commentary_styles[selected_style],
            "commentary_style": selected_style,
            "commentary_styles": commentary_styles,
            "source_commentary": normalized["source_commentary"],
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
        minute = int(payload.get("minute") or 0)
        clock = str(payload.get("clock") or payload.get("clock_label") or f"{minute}'")
        source_event_type = str(payload.get("event_type") or payload.get("type") or event_type)
        return {
            "event_id": self._resolve_event_id(
                match_id=match_id,
                payload=payload,
                minute=minute,
                source_event_type=source_event_type,
            ),
            "sequence": self._resolve_sequence(payload),
            "match_id": match_id,
            "type": event_type,
            "source_event_type": source_event_type,
            "minute": minute,
            "clock": clock,
            "team_id": _optional_string(payload.get("team_id")),
            "team": _optional_string(payload.get("team") or payload.get("team_name") or payload.get("club_name")),
            "player_id": _optional_string(payload.get("player_id")),
            "player": _optional_string(payload.get("player") or payload.get("player_name")),
            "secondary_player_id": _optional_string(payload.get("secondary_player_id")),
            "secondary_player": _optional_string(payload.get("secondary_player") or payload.get("secondary_player_name")),
            "home_team": _optional_string(payload.get("home_team")),
            "away_team": _optional_string(payload.get("away_team")),
            "home_score": int(payload.get("home_score") or 0),
            "away_score": int(payload.get("away_score") or 0),
            "source_commentary": _optional_string(
                payload.get("source_commentary") or payload.get("commentary") or payload.get("description")
            ),
            "metadata": dict(payload.get("metadata") or {}),
        }

    def _normalize_replay_event(
        self,
        *,
        match_id: str,
        event: MatchEventView,
        home_team_name: str | None,
        away_team_name: str | None,
        sequence: int | None = None,
    ) -> dict[str, Any]:
        return self._normalize_event(
            match_id=match_id,
            event={
                "event_id": event.event_id,
                "sequence": sequence,
                "event_type": getattr(event.event_type, "value", event.event_type),
                "minute": event.minute,
                "clock": event.clock_label,
                "team_id": event.team_id,
                "team_name": event.team_name,
                "player_id": event.primary_player.player_id if event.primary_player is not None else None,
                "player_name": event.primary_player.player_name if event.primary_player is not None else None,
                "secondary_player_id": event.secondary_player.player_id if event.secondary_player is not None else None,
                "secondary_player_name": event.secondary_player.player_name if event.secondary_player is not None else None,
                "home_team": home_team_name,
                "away_team": away_team_name,
                "home_score": event.home_score,
                "away_score": event.away_score,
                "source_commentary": event.commentary,
                "metadata": event.metadata,
            },
        )

    @classmethod
    def _resolve_event_id(
        cls,
        *,
        match_id: str,
        payload: Mapping[str, Any],
        minute: int,
        source_event_type: str,
    ) -> str:
        """Return a stable key for the event.

        Previously a missing ``event_id`` fell back to ``uuid4()``, so the same event
        republished after a retry or reconnect arrived with a different identity and
        could not be de-duplicated by consumers. The fallback is now derived from the
        event's own content, which keeps it stable across redeliveries.
        """
        explicit = str(payload.get("event_id") or "").strip()
        if explicit:
            return explicit
        sequence = cls._resolve_sequence(payload)
        if sequence is not None:
            return f"{match_id}:{sequence:05d}"
        return f"{match_id}:{minute:03d}:{source_event_type}"

    @staticmethod
    def _resolve_sequence(payload: Mapping[str, Any]) -> int | None:
        raw = payload.get("sequence")
        if raw is None:
            return None
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None

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


__all__ = ["MatchStreamService", "match_event_channel"]
