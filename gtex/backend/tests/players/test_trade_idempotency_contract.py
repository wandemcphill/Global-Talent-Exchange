from __future__ import annotations

import inspect

from app.players.token_schemas import PlayerSharePurchaseRequest, PlayerShareSaleRequest
from app.players.token_service import PlayerTokenMarketService
from app.players.trade_boundary import PlayerShareTradeBoundary


def _min_length(field):
    return next(item.min_length for item in field.metadata if hasattr(item, "min_length"))


def _max_length(field):
    return next(item.max_length for item in field.metadata if hasattr(item, "max_length"))


def test_trade_requests_expose_bounded_idempotency_keys():
    purchase = PlayerSharePurchaseRequest.model_fields["idempotency_key"]
    sale = PlayerShareSaleRequest.model_fields["idempotency_key"]

    assert purchase.default is None
    assert sale.default is None
    assert _min_length(purchase) == 8
    assert _max_length(purchase) == 128
    assert _min_length(sale) == 8
    assert _max_length(sale) == 128


def test_trade_service_and_boundary_accept_idempotency_keys():
    buy = inspect.signature(PlayerTokenMarketService.buy_shares)
    sell = inspect.signature(PlayerTokenMarketService.sell_shares)
    boundary_buy = inspect.signature(PlayerShareTradeBoundary.buy)
    boundary_sell = inspect.signature(PlayerShareTradeBoundary.sell)

    assert buy.parameters["idempotency_key"].default is None
    assert sell.parameters["idempotency_key"].default is None
    assert boundary_buy.parameters["idempotency_key"].default is None
    assert boundary_sell.parameters["idempotency_key"].default is None


def test_idempotency_reference_is_scoped_to_actor_and_key_only():
    # Deliberately NOT scoped to player/side/share_count: reusing the same raw key
    # for a different trade must land on the SAME lookup bucket, so
    # _replay_idempotent_trade's metadata comparison can detect and reject the
    # conflict instead of two independent references silently allowing it through
    # as two unrelated trades. See test_trade_idempotency_conflicts.py.
    build = PlayerTokenMarketService._idempotency_reference

    first = build(actor_id="user-a", key="same-key")
    same = build(actor_id="user-a", key="same-key")
    other_user = build(actor_id="user-b", key="same-key")

    assert first == same
    assert first != other_user
    assert first.startswith("trade-idempotency:")
    assert len(first) == len("trade-idempotency:") + 64
