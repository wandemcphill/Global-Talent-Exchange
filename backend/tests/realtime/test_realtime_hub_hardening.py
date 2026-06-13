"""N44 realtime hardening: topic-scope auth, duplicate subscriptions, stale
listeners, disconnect/rejoin, and collision isolation on RealtimeHub."""

from __future__ import annotations

import asyncio

from app.realtime.service import RealtimeHub, admin_topic, wallet_topic


class _FakeWebSocket:
    def __init__(self, *, fail: bool = False) -> None:
        self.accepted = False
        self.closed = False
        self.fail = fail
        self.sent: list[dict] = []

    async def accept(self) -> None:
        self.accepted = True

    async def send_json(self, payload: dict) -> None:
        if self.fail:
            raise RuntimeError("socket broken")
        self.sent.append(payload)

    async def close(self) -> None:
        self.closed = True


def _run(coro):
    return asyncio.run(coro)


def test_wallet_topic_scope_denies_cross_user_subscription() -> None:
    async def scenario() -> None:
        hub = RealtimeHub()
        ws = _FakeWebSocket()
        client_id = await hub.connect(ws, user_id="user-a", topics=())
        # Attempt to subscribe to another user's wallet + admin topics.
        topics = await hub.subscribe(
            client_id,
            topics=(wallet_topic("user-b"), admin_topic("user-b"), "wallet", "admin"),
        )
        # Only the caller's OWN resolved wallet/admin topics are accepted.
        assert wallet_topic("user-b") not in topics
        assert admin_topic("user-b") not in topics
        assert wallet_topic("user-a") in topics
        assert admin_topic("user-a") in topics

    _run(scenario())


def test_duplicate_subscriptions_are_idempotent() -> None:
    async def scenario() -> None:
        hub = RealtimeHub()
        ws = _FakeWebSocket()
        client_id = await hub.connect(ws, user_id="user-a", topics=())
        first = await hub.subscribe(client_id, topics=("market", "market", "market"))
        second = await hub.subscribe(client_id, topics=("market",))
        assert first.count("market") == 1
        assert second.count("market") == 1

    _run(scenario())


def test_broadcast_delivers_once_per_connection_no_duplication() -> None:
    async def scenario() -> None:
        hub = RealtimeHub()
        hub.bind_loop(asyncio.get_running_loop())
        ws = _FakeWebSocket()
        client_id = await hub.connect(ws, user_id="user-a", topics=("market",))
        # Same client subscribed twice to the same topic must not double-deliver.
        await hub.subscribe(client_id, topics=("market", "market"))
        from app.realtime.service import RealtimeDispatch

        await hub._broadcast([RealtimeDispatch(type="market_price_update", data={"x": 1}, topics=("market",))])
        assert len(ws.sent) == 1

    _run(scenario())


def test_stale_listener_is_evicted_on_send_failure() -> None:
    async def scenario() -> None:
        hub = RealtimeHub()
        hub.bind_loop(asyncio.get_running_loop())
        good = _FakeWebSocket()
        bad = _FakeWebSocket(fail=True)
        good_id = await hub.connect(good, user_id="user-a", topics=("market",))
        bad_id = await hub.connect(bad, user_id="user-b", topics=("market",))
        from app.realtime.service import RealtimeDispatch

        await hub._broadcast([RealtimeDispatch(type="market_price_update", data={"x": 1}, topics=("market",))])
        snapshot = hub.snapshot()
        # Broken socket evicted; healthy one retained.
        assert good_id in hub._connections
        assert bad_id not in hub._connections
        assert len(good.sent) == 1
        assert snapshot.delivered_messages == 1

    _run(scenario())


def test_disconnect_then_rejoin_issues_fresh_client_and_no_leak() -> None:
    async def scenario() -> None:
        hub = RealtimeHub()
        ws1 = _FakeWebSocket()
        first_id = await hub.connect(ws1, user_id="user-a", topics=("wallet",))
        await hub.disconnect(first_id)
        assert first_id not in hub._connections
        # Rejoin gets a distinct client id; no residual connection leak.
        ws2 = _FakeWebSocket()
        second_id = await hub.connect(ws2, user_id="user-a", topics=("wallet",))
        assert second_id != first_id
        assert len(hub._connections) == 1
        # Subscribing on the stale id is a no-op (returns empty), no resurrection.
        assert await hub.subscribe(first_id, topics=("market",)) == ()
        assert len(hub._connections) == 1

    _run(scenario())


def test_client_id_collision_isolation_across_concurrent_connects() -> None:
    async def scenario() -> None:
        hub = RealtimeHub()
        sockets = [_FakeWebSocket() for _ in range(25)]
        ids = await asyncio.gather(
            *(hub.connect(ws, user_id=f"user-{i}", topics=("market",)) for i, ws in enumerate(sockets))
        )
        # No two concurrent connections collide on client_id; all tracked.
        assert len(set(ids)) == len(ids) == 25
        assert len(hub._connections) == 25

    _run(scenario())
