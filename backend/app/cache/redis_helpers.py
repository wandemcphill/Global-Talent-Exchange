from __future__ import annotations

from typing import Any

from app.core.cache import CacheBackend, JsonCacheNamespace, NullCacheBackend, RedisCacheBackend, build_cache_backend
from app.ingestion.cache_keys import (
    CACHE_TTLS,
    club_cache_keys,
    club_roster_snapshot_key,
    competition_cache_keys,
    competition_table_key,
    player_cache_keys,
    player_profile_summary_key,
    top_prospects_key,
    trending_players_key,
)
class HotReadCache:
    def __init__(self, backend: CacheBackend | None = None):
        self.cache = JsonCacheNamespace(backend)
        self.backend = self.cache.backend

    def get_top_prospects(self, scope: str = "global") -> dict[str, Any] | None:
        return self.cache.get_json(top_prospects_key(scope))

    def set_top_prospects(self, payload: dict[str, Any], scope: str = "global") -> None:
        self.cache.set_json(top_prospects_key(scope), payload, CACHE_TTLS["top_prospects"])

    def get_player_profile_summary(self, player_id: str) -> dict[str, Any] | None:
        return self.cache.get_json(player_profile_summary_key(player_id))

    def set_player_profile_summary(self, player_id: str, payload: dict[str, Any]) -> None:
        self.cache.set_json(player_profile_summary_key(player_id), payload, CACHE_TTLS["player_profile_summary"])

    def get_trending_players(self, scope: str = "global") -> dict[str, Any] | None:
        return self.cache.get_json(trending_players_key(scope))

    def set_trending_players(self, payload: dict[str, Any], scope: str = "global") -> None:
        self.cache.set_json(trending_players_key(scope), payload, CACHE_TTLS["trending_players"])

    def get_competition_table(self, competition_id: str, season_id: str | None = None) -> dict[str, Any] | None:
        return self.cache.get_json(competition_table_key(competition_id, season_id))

    def set_competition_table(self, competition_id: str, payload: dict[str, Any], season_id: str | None = None) -> None:
        self.cache.set_json(
            competition_table_key(competition_id, season_id),
            payload,
            CACHE_TTLS["competition_table"],
        )

    def get_club_roster_snapshot(self, club_id: str, season_id: str | None = None) -> dict[str, Any] | None:
        return self.cache.get_json(club_roster_snapshot_key(club_id, season_id))

    def set_club_roster_snapshot(self, club_id: str, payload: dict[str, Any], season_id: str | None = None) -> None:
        self.cache.set_json(
            club_roster_snapshot_key(club_id, season_id),
            payload,
            CACHE_TTLS["club_roster_snapshot"],
        )

    def invalidate(
        self,
        *,
        competition_ids: set[str] | None = None,
        club_ids: set[str] | None = None,
        player_ids: set[str] | None = None,
        season_id: str | None = None,
    ) -> None:
        keys: list[str] = []
        for competition_id in sorted(competition_ids or set()):
            keys.extend(competition_cache_keys(competition_id, season_id))
        for club_id in sorted(club_ids or set()):
            keys.extend(club_cache_keys(club_id, season_id))
        for player_id in sorted(player_ids or set()):
            keys.extend(player_cache_keys(player_id))
        self.backend.delete_many(keys)
