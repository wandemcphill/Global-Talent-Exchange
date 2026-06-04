from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.core.events import DomainEvent
from app.integrations import ai_brain_client as ai_brain_module
from app.integrations.ai_brain_client import AiBrainConfig, AiBrainEventBridge, domain_event_to_ai_payload


def test_domain_event_maps_to_canonical_ai_brain_payload() -> None:
    event = DomainEvent(
        name="market.order.created",
        payload={"actor_id": "club-1", "actor_type": "club", "player_id": "player-9"},
        event_id="evt-gtex-1",
        occurred_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        aggregate_id="order-1",
        aggregate_type="order",
        producer="gtex-test",
        headers={"x-trace-id": "trace-gtex-1"},
    )

    payload = domain_event_to_ai_payload(event)

    assert payload is not None
    assert payload["app"] == "gtex"
    assert payload["actor_id"] == "club-1"
    assert payload["actor_type"] == "club"
    assert payload["event"] == "market_order_created"
    assert payload["entity_type"] == "order"
    assert payload["entity_id"] == "order-1"
    assert payload["idempotency_key"] == "gtex:event:evt-gtex-1"
    assert payload["metadata"]["trace_id"] == "trace-gtex-1"
    assert payload["metadata"]["player_id"] == "player-9"
    assert payload["metadata"]["order_id"] == "order-1"


def test_domain_event_enriches_market_projection_metadata() -> None:
    event = DomainEvent(
        name="market.offer.accepted",
        payload={
            "offer_id": "offer-1",
            "asset_id": "player-9",
            "seller_user_id": "club-seller",
            "buyer_user_id": "club-buyer",
            "listing_id": "listing-1",
            "cash_amount": 45000,
            "status": "accepted",
        },
        event_id="evt-gtex-2",
        occurred_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        producer="gtex-test",
    )

    payload = domain_event_to_ai_payload(event)

    assert payload is not None
    assert payload["actor_id"] == "club-buyer"
    assert payload["entity_type"] == "offer"
    assert payload["entity_id"] == "offer-1"
    metadata = payload["metadata"]
    assert metadata["player_id"] == "player-9"
    assert metadata["buyer_id"] == "club-buyer"
    assert metadata["seller_id"] == "club-seller"
    assert metadata["listing_id"] == "listing-1"
    assert metadata["cash_amount"] == 45000


def test_domain_event_enriches_player_payment_and_club_relationships() -> None:
    event = DomainEvent(
        name="payment.settled",
        payload={
            "payer_user_id": "fan-1",
            "player_id": "player-10",
            "club_id": "club-10",
            "payment_id": "payment-10",
            "provider_event_id": "evt-pay-10",
            "amount_minor": 125000,
            "currency": "NGN",
            "card_id": "card-10",
            "from_club_id": "club-seller",
            "to_club_id": "club-buyer",
        },
        event_id="evt-gtex-3",
        occurred_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        aggregate_id="payment-10",
        aggregate_type="payment",
        producer="gtex-test",
    )

    payload = domain_event_to_ai_payload(event)

    assert payload is not None
    assert payload["actor_id"] == "fan-1"
    assert payload["entity_type"] == "payment"
    assert payload["entity_id"] == "payment-10"
    metadata = payload["metadata"]
    assert metadata["player_id"] == "player-10"
    assert metadata["club_id"] == "club-10"
    assert metadata["payment_id"] == "payment-10"
    assert metadata["provider_event_id"] == "evt-pay-10"
    assert metadata["amount_minor"] == 125000
    assert metadata["currency"] == "NGN"
    assert metadata["card_id"] == "card-10"
    assert metadata["seller_id"] == "club-seller"
    assert metadata["buyer_id"] == "club-buyer"


def test_disabled_ai_brain_bridge_is_best_effort() -> None:
    bridge = AiBrainEventBridge(
        AiBrainConfig(enabled=False, base_url="", api_key="", timeout_seconds=0.05)
    )
    event = DomainEvent(name="player.viewed", payload={"fan_id": "fan-1"})

    assert bridge.emit_event(event) is False


def test_read_side_trust_and_semantic_search_calls_ai_brain(monkeypatch) -> None:
    calls: list[tuple[str, str, bytes | None]] = []

    class FakeResponse:
        status = 200

        def __init__(self, payload: dict[str, Any]) -> None:
            self.payload = payload

        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *_: object) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(self.payload).encode("utf-8")

    def fake_urlopen(req: Any, timeout: float) -> FakeResponse:
        calls.append((req.full_url, req.get_method(), req.data))
        if req.get_method() == "GET":
            return FakeResponse({"trust_score": 88, "recommended_action": "allow"})
        return FakeResponse({"results": [{"entity_id": "player-1", "score": 0.91}]})

    monkeypatch.setattr(ai_brain_module.request, "urlopen", fake_urlopen)
    bridge = AiBrainEventBridge(
        AiBrainConfig(
            enabled=True,
            base_url="http://brain.local",
            api_key="secret",
            timeout_seconds=0.05,
        )
    )

    trust = bridge.get_trust_score("club-1", trace_id="trace-1")
    search = bridge.semantic_search(
        "pacey winger",
        [{"entity_id": "player-1", "text": "Left winger with pace"}],
        user_id="club-1",
        trace_id="trace-2",
    )

    assert trust == {"trust_score": 88, "recommended_action": "allow"}
    assert search == {"results": [{"entity_id": "player-1", "score": 0.91}]}
    assert calls[0][0] == "http://brain.local/ai/trust/score?app=gtex&user_id=club-1"
    assert calls[0][1] == "GET"
    assert calls[1][0] == "http://brain.local/ai/search/semantic"
    assert calls[1][1] == "POST"
    assert calls[1][2] is not None
    assert json.loads(calls[1][2])["app"] == "gtex"
