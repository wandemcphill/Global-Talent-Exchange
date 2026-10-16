from __future__ import annotations

from app.cache.redis_helpers import HotReadCache, NullCacheBackend, build_cache_backend


def test_cache_backend_falls_back_to_null_when_redis_unavailable() -> None:
    backend = build_cache_backend("redis://127.0.0.1:1/0")

    assert isinstance(backend, NullCacheBackend)


def test_hot_read_cache_works_with_null_backend() -> None:
    cache = HotReadCache(NullCacheBackend())

    cache.set_player_profile_summary("player-1", {"player_id": "player-1"})

    assert cache.get_player_profile_summary("player-1") is None
