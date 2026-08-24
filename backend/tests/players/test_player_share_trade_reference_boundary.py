from __future__ import annotations

from app.players.token_service import PlayerTokenMarketService
from app.scripts.audit_player_share_trade_boundary import inspect_trade_boundary
from app.scripts.audit_player_share_trade_idempotency import inspect_trade_idempotency


def test_trade_methods_have_no_implicit_market_issuance() -> None:
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[2]
        / "app"
        / "players"
        / "token_service.py"
    ).read_text(encoding="utf-8")
    assert inspect_trade_boundary(source)["pass"] is True


def test_trade_methods_have_no_fresh_uuid_reference() -> None:
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[2]
        / "app"
        / "players"
        / "token_service.py"
    ).read_text(encoding="utf-8")
    assert inspect_trade_idempotency(source)["pass"] is True


def test_trade_reference_is_deterministic_and_market_scoped() -> None:
    first = PlayerTokenMarketService._trade_reference(
        market_id="market-1",
        actor_id="user-1",
        side="buy",
        circulating_shares=25,
        share_count=5,
    )
    second = PlayerTokenMarketService._trade_reference(
        market_id="market-1",
        actor_id="user-1",
        side="buy",
        circulating_shares=25,
        share_count=5,
    )

    assert first == second
    assert first == "market:market-1:actor:user-1:side:buy:before:25:shares:5"
    assert "uuid" not in first.lower()
