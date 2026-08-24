from __future__ import annotations

import inspect

from app.players.token_schemas import PlayerSharePurchaseRequest, PlayerShareSaleRequest
from app.players.token_service import PlayerTokenMarketService
from app.players.trade_boundary import PlayerShareTradeBoundary


def test_trade_requests_expose_bounded_idempotency_keys():
    purchase = PlayerSharePurchaseRequest.model_fields["idempotency_key"]
    sale = PlayerShareSaleRequest.model_fields["idempotency_key"]

    assert purchase.default is None
    assert sale.default is None
    assert purchase.metadata[0].min_length == 8
    assert purchase.metadata[0].max_length == 128
    assert sale.metadata[0].min_length == 8
    assert sale.metadata[0].max_length == 128


def test_trade_service_and_boundary_accept_idempotency_keys():
    buy = inspect.signature(PlayerTokenMarketService.buy_shares)
    sell = inspect.signature(PlayerTokenMarketService.sell_shares)
    boundary_buy = inspect.signature(PlayerShareTradeBoundary.buy)
    boundary_sell = inspect.signature(PlayerShareTradeBoundary.sell)

    assert buy.parameters["idempotency_key"].default is None
    assert sell.parameters["idempotency_key"].default is None
    assert boundary_buy.parameters["idempotency_key"].default is None
    assert boundary_sell.parameters["idempotency_key"].default is None


def test_idempotency_reference_is_scoped_to_actor_player_side_and_key():
    build = PlayerTokenMarketService._idempotency_reference

    first = build(actor_id="user-a", player_id="player-1", side="buy", key="same-key")
    same = build(actor_id="user-a", player_id="player-1", side="buy", key="same-key")
    other_user = build(actor_id="user-b", player_id="player-1", side="buy", key="same-key")
    other_side = build(actor_id="user-a", player_id="player-1", side="sell", key="same-key")

    assert first == same
    assert first != other_user
    assert first != other_side
    assert first.startswith("trade-idempotency:")
    assert len(first) == len("trade-idempotency:") + 64
