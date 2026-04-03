from __future__ import annotations

from app.market.repositories import InMemoryMarketRepository, RedisMarketRepository, build_market_repository


def test_redis_market_repository_initializes_client(monkeypatch) -> None:
    sentinel_client = object()
    calls: list[tuple[str, bool]] = []

    def fake_from_url(redis_url: str, *, decode_responses: bool):
        calls.append((redis_url, decode_responses))
        return sentinel_client

    monkeypatch.setattr("app.market.repositories.Redis.from_url", fake_from_url)

    repository = RedisMarketRepository("redis://example.com:6379/0")

    assert repository.client is sentinel_client
    assert calls == [("redis://example.com:6379/0", True)]


def test_build_market_repository_falls_back_to_memory_when_redis_ping_fails(monkeypatch) -> None:
    monkeypatch.setattr("app.market.repositories.Redis.from_url", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(RedisMarketRepository, "ping", lambda self: False)

    repository = build_market_repository("redis://example.com:6379/0")

    assert isinstance(repository, InMemoryMarketRepository)
