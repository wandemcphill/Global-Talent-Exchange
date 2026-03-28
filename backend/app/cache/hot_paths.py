from __future__ import annotations

from collections.abc import Sequence
import json
import logging
from typing import Any

from redis.exceptions import RedisError

from app.core.cache import CacheBackend, NullCacheBackend

logger = logging.getLogger(__name__)


class HotPathCache:
    def __init__(self, backend: CacheBackend | None = None) -> None:
        self.backend = backend or NullCacheBackend()

    def get_wallet_summary(self, *, user_id: str, currency: str) -> dict[str, Any] | None:
        return self._get_json(self.wallet_key(user_id, currency))

    def set_wallet_summary(
        self,
        *,
        user_id: str,
        currency: str,
        payload: dict[str, Any],
        ttl_seconds: int,
    ) -> None:
        self._set_json(self.wallet_key(user_id, currency), payload, ttl_seconds)

    def get_match_state(self, match_id: str) -> dict[str, Any] | None:
        return self._get_json(self.match_state_key(match_id))

    def set_match_state(self, match_id: str, payload: dict[str, Any], *, ttl_seconds: int) -> None:
        self._set_json(self.match_state_key(match_id), payload, ttl_seconds)
        if bool(payload.get("is_live")):
            self._set_add(self.active_matches_key(), match_id, ttl_seconds=ttl_seconds)
        else:
            self._set_remove(self.active_matches_key(), match_id)

    def clear_match_state(self, match_id: str) -> None:
        self.backend.delete_many([self.match_state_key(match_id)])
        self._set_remove(self.active_matches_key(), match_id)

    def append_match_events(
        self,
        match_id: str,
        events: Sequence[dict[str, Any]],
        *,
        ttl_seconds: int,
        max_length: int = 512,
    ) -> None:
        if not events:
            return
        key = self.match_events_key(match_id)
        client = self._client()
        if client is not None:
            serialized = [json.dumps(event, default=str) for event in events]
            try:
                client.rpush(key, *serialized)
                if max_length > 0:
                    client.ltrim(key, -max_length, -1)
                client.expire(key, ttl_seconds)
                return
            except RedisError:
                logger.warning("hot_path.match_events.redis_append_failed", extra={"match_id": match_id})
        existing = self._get_json(key)
        resolved: list[dict[str, Any]] = list(existing) if isinstance(existing, list) else []
        resolved.extend(dict(item) for item in events)
        if max_length > 0:
            resolved = resolved[-max_length:]
        self._set_json(key, resolved, ttl_seconds)

    def get_match_events(self, match_id: str, *, cursor: int = 0) -> list[dict[str, Any]]:
        key = self.match_events_key(match_id)
        client = self._client()
        if client is not None:
            try:
                raw_items = client.lrange(key, cursor, -1)
                events: list[dict[str, Any]] = []
                for item in raw_items:
                    try:
                        payload = json.loads(item)
                    except (TypeError, json.JSONDecodeError):
                        continue
                    if isinstance(payload, dict):
                        events.append(payload)
                return events
            except RedisError:
                logger.warning("hot_path.match_events.redis_read_failed", extra={"match_id": match_id})
        payload = self._get_json(key)
        if not isinstance(payload, list):
            return []
        return [dict(item) for item in payload[cursor:] if isinstance(item, dict)]

    def clear_match_events(self, match_id: str) -> None:
        self.backend.delete_many([self.match_events_key(match_id)])

    def publish_match_channel(self, match_id: str, payload: dict[str, Any]) -> None:
        client = self._client()
        if client is None:
            return
        try:
            client.publish(f"match:{match_id}", json.dumps(payload, default=str))
        except RedisError:
            logger.warning("hot_path.match_publish.failed", extra={"match_id": match_id})

    def list_active_matches(self) -> list[str]:
        key = self.active_matches_key()
        client = self._client()
        if client is not None:
            try:
                return sorted(str(item) for item in client.smembers(key))
            except RedisError:
                logger.warning("hot_path.active_matches.redis_read_failed")
        payload = self._get_json(key)
        if not isinstance(payload, list):
            return []
        return [str(item) for item in payload]

    def set_player_snapshot(self, player_id: str, payload: dict[str, Any], *, ttl_seconds: int) -> None:
        self._set_json(self.player_snapshot_key(player_id), payload, ttl_seconds)
        price = payload.get("market_price")
        if price is None:
            return
        self.backend.set(self.player_price_key(player_id), str(price), ttl_seconds)

    def get_player_snapshot(self, player_id: str) -> dict[str, Any] | None:
        return self._get_json(self.player_snapshot_key(player_id))

    def get_player_price(self, player_id: str) -> float | None:
        raw = self.backend.get(self.player_price_key(player_id))
        if raw is None:
            return None
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None

    def replace_global_leaderboard(
        self,
        entries: Sequence[tuple[str, float, dict[str, Any]]],
        *,
        ttl_seconds: int,
    ) -> None:
        client = self._client()
        if client is not None:
            try:
                client.delete(self.global_leaderboard_key())
                mapping = {member_id: score for member_id, score, _payload in entries}
                if mapping:
                    client.zadd(self.global_leaderboard_key(), mapping)
                    client.expire(self.global_leaderboard_key(), ttl_seconds)
                for member_id, _score, payload in entries:
                    self._set_json(self.global_leaderboard_entry_key(member_id), payload, ttl_seconds)
                return
            except RedisError:
                logger.warning("hot_path.global_leaderboard.redis_write_failed")
        payload = [item for _member_id, _score, item in entries]
        self._set_json(self.global_leaderboard_entries_key(), payload, ttl_seconds)

    def get_global_leaderboard(self, *, limit: int) -> list[dict[str, Any]]:
        if limit <= 0:
            return []
        client = self._client()
        if client is not None:
            try:
                member_ids = client.zrevrange(self.global_leaderboard_key(), 0, limit - 1)
                if not member_ids:
                    return []
                raw_entries = client.mget([self.global_leaderboard_entry_key(str(member_id)) for member_id in member_ids])
                entries: list[dict[str, Any]] = []
                for item in raw_entries:
                    if item is None:
                        continue
                    try:
                        payload = json.loads(item)
                    except (TypeError, json.JSONDecodeError):
                        continue
                    if isinstance(payload, dict):
                        entries.append(payload)
                return entries
            except RedisError:
                logger.warning("hot_path.global_leaderboard.redis_read_failed")
        payload = self._get_json(self.global_leaderboard_entries_key())
        if not isinstance(payload, list):
            return []
        return [dict(item) for item in payload[:limit] if isinstance(item, dict)]

    @staticmethod
    def wallet_key(user_id: str, currency: str) -> str:
        return f"wallet:{user_id}:{currency}"

    @staticmethod
    def match_state_key(match_id: str) -> str:
        return f"match:{match_id}:state"

    @staticmethod
    def match_events_key(match_id: str) -> str:
        return f"match:{match_id}:events"

    @staticmethod
    def active_matches_key() -> str:
        return "active_matches"

    @staticmethod
    def player_snapshot_key(player_id: str) -> str:
        return f"player:{player_id}:snapshot"

    @staticmethod
    def player_price_key(player_id: str) -> str:
        return f"player:{player_id}:price"

    @staticmethod
    def global_leaderboard_key() -> str:
        return "leaderboard:global"

    @staticmethod
    def global_leaderboard_entries_key() -> str:
        return "leaderboard:global:entries"

    @staticmethod
    def global_leaderboard_entry_key(member_id: str) -> str:
        return f"leaderboard:global:entry:{member_id}"

    def _client(self):
        return getattr(self.backend, "client", None)

    def _get_json(self, key: str) -> Any:
        raw = self.backend.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("hot_path.decode_failed", extra={"key": key})
            return None

    def _set_json(self, key: str, payload: Any, ttl_seconds: int) -> None:
        self.backend.set(key, json.dumps(payload, default=str), ttl_seconds)

    def _set_add(self, key: str, member: str, *, ttl_seconds: int) -> None:
        client = self._client()
        if client is not None:
            try:
                client.sadd(key, member)
                client.expire(key, ttl_seconds)
                return
            except RedisError:
                logger.warning("hot_path.set_add.redis_failed", extra={"key": key})
        payload = self._get_json(key)
        existing = [str(item) for item in payload] if isinstance(payload, list) else []
        if member not in existing:
            existing.append(member)
        self._set_json(key, sorted(existing), ttl_seconds)

    def _set_remove(self, key: str, member: str) -> None:
        client = self._client()
        if client is not None:
            try:
                client.srem(key, member)
                return
            except RedisError:
                logger.warning("hot_path.set_remove.redis_failed", extra={"key": key})
        payload = self._get_json(key)
        if not isinstance(payload, list):
            return
        remaining = [str(item) for item in payload if str(item) != member]
        self._set_json(key, remaining, 60)


__all__ = ["HotPathCache"]
