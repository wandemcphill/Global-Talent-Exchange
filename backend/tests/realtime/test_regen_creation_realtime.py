from __future__ import annotations

from app.core.events import DomainEvent
from app.realtime.service import RealtimeHub, wallet_topic


def test_regen_creation_order_events_dispatch_to_wallet_topic() -> None:
    hub = RealtimeHub()
    event = DomainEvent(
        name="regen.creation_order.generated",
        aggregate_id="order-1",
        aggregate_type="regen_creation_order",
        payload={
            "order_id": "order-1",
            "user_id": "user-1",
            "actor_user_id": "user-1",
            "club_id": "club-1",
            "request_type": "son",
            "status": "generated",
            "previous_status": "paid",
            "payment_method": "wallet",
            "payment_provider": "wallet",
            "payment_reference": "regen-wallet-order-1",
            "wallet_reservation": {"status": "settled"},
            "generated_player_id": "player-1",
            "generated_regen_profile_id": "regen-1",
            "amount_coin": "200.0000",
            "currency": "COIN",
            "audit_reference": "regen-creation-order:order-1:generated",
        },
    )

    dispatches = hub._map_domain_event(event)

    assert [dispatch.type for dispatch in dispatches] == [
        "regen_creation_order_update",
        "notification",
    ]
    assert dispatches[0].topics == (wallet_topic("user-1"),)
    assert dispatches[0].data["order_id"] == "order-1"
    assert dispatches[0].data["status"] == "generated"
    assert dispatches[0].data["generated_player_id"] == "player-1"
    assert dispatches[0].data["audit_reference"] == "regen-creation-order:order-1:generated"
    assert dispatches[1].topics == (wallet_topic("user-1"),)
    assert dispatches[1].data["template_key"] == "REGEN_CREATION_ORDER_GENERATED"
    assert dispatches[1].data["metadata"]["order_id"] == "order-1"


def test_regen_creation_order_events_require_user_and_order_scope() -> None:
    hub = RealtimeHub()

    assert (
        hub._map_domain_event(
            DomainEvent(
                name="regen.creation_order.generated",
                payload={"user_id": "user-1"},
            )
        )
        == []
    )
    assert (
        hub._map_domain_event(
            DomainEvent(
                name="regen.creation_order.generated",
                payload={"order_id": "order-1"},
            )
        )
        == []
    )
