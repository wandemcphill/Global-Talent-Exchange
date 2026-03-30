from __future__ import annotations

from redis.exceptions import ConnectionError

from app.backbone.redis_fanout import HybridEventPublisher


def test_hybrid_event_publisher_listener_exits_cleanly_when_subscribe_fails() -> None:
    class _PubSub:
        def subscribe(self, _channel: str) -> None:
            raise ConnectionError("redis unavailable")

        def close(self) -> None:
            return None

    class _Redis:
        def pubsub(self, *, ignore_subscribe_messages: bool) -> _PubSub:
            assert ignore_subscribe_messages is True
            return _PubSub()

    publisher = HybridEventPublisher(redis_url=None)
    publisher._redis = _Redis()

    publisher._run_listener()
