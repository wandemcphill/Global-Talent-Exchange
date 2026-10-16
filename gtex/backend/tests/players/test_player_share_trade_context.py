from __future__ import annotations

from app.players.token_schemas import PlayerSharePurchaseRequest, PlayerShareSaleRequest
from app.players.trade_context import consume_player_share_idempotency_key


def test_purchase_request_captures_idempotency_key_in_request_context() -> None:
    payload = PlayerSharePurchaseRequest(share_count=3, idempotency_key="buy-order-123456")

    assert payload.idempotency_key == "buy-order-123456"
    assert consume_player_share_idempotency_key() == "buy-order-123456"
    assert consume_player_share_idempotency_key() is None


def test_sale_request_captures_idempotency_key_in_request_context() -> None:
    payload = PlayerShareSaleRequest(share_count=2, idempotency_key="sell-order-123456")

    assert payload.idempotency_key == "sell-order-123456"
    assert consume_player_share_idempotency_key() == "sell-order-123456"
    assert consume_player_share_idempotency_key() is None
