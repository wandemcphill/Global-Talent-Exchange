from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

from app.portfolio.realized_accounting import calculate_user_realized_pl


def _event(*, event_id: str, player_id: str, event_type: str, delta: int, price: str, gross: str, fee: str):
    return SimpleNamespace(
        id=event_id,
        player_id=player_id,
        user_id="user-1",
        event_type=event_type,
        share_delta=delta,
        price_per_share_coin=Decimal(price),
        gross_amount_coin=Decimal(gross),
        created_at=None,
        metadata_json={"transaction_id": f"tx-{event_id}", "fee_amount_coin": fee},
    )


def _session(events):
    session = Mock()
    session.scalars.return_value.all.return_value = events
    return session


def _user():
    return SimpleNamespace(id="user-1")


def test_weighted_average_cost_buy_buy_partial_sell():
    events = [
        _event(event_id="b1", player_id="p1", event_type="buy", delta=2, price="10.0000", gross="20.0000", fee="2.0000"),
        _event(event_id="b2", player_id="p1", event_type="buy", delta=2, price="20.0000", gross="40.0000", fee="4.0000"),
        _event(event_id="s1", player_id="p1", event_type="sell", delta=-2, price="30.0000", gross="60.0000", fee="6.0000"),
    ]

    result = calculate_user_realized_pl(_session(events), _user())

    assert result.available is True
    assert result.total == Decimal("16.0000")
    assert len(result.rows) == 1
    assert result.rows[0].cost_basis == Decimal("33.0000")
    assert result.rows[0].realized_pl == Decimal("21.0000")


def test_full_sell_leaves_zero_cost_basis_and_accumulates_profit():
    events = [
        _event(event_id="b1", player_id="p1", event_type="buy", delta=5, price="4.0000", gross="20.0000", fee="2.0000"),
        _event(event_id="s1", player_id="p1", event_type="sell", delta=-5, price="8.0000", gross="40.0000", fee="4.0000"),
    ]

    result = calculate_user_realized_pl(_session(events), _user())

    assert result.available is True
    assert result.total == Decimal("14.0000")
    assert result.rows[0].cost_basis == Decimal("22.0000")
    assert result.rows[0].realized_pl == Decimal("14.0000")


def test_historical_event_without_settlement_metadata_is_unavailable_not_zero():
    event = _event(event_id="legacy", player_id="p1", event_type="sell", delta=-1, price="10.0000", gross="10.0000", fee="0.0000")
    event.metadata_json = {}

    result = calculate_user_realized_pl(_session([event]), _user())

    assert result.available is False
    assert result.total == Decimal("0.0000")
    assert result.rows == []
    assert result.unavailable_reason is not None


def test_sale_without_preceding_cost_basis_is_unavailable():
    events = [
        _event(event_id="s1", player_id="p1", event_type="sell", delta=-1, price="10.0000", gross="10.0000", fee="0.0000"),
    ]

    result = calculate_user_realized_pl(_session(events), _user())

    assert result.available is False
    assert result.rows == []
    assert "cost basis" in (result.unavailable_reason or "").lower()
