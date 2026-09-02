from __future__ import annotations

import ast
from pathlib import Path

from app.players.token_service import PlayerTokenMarketService

TOKEN_SERVICE = Path(__file__).resolve().parents[2] / "app" / "players" / "token_service.py"


def _trade_method_names(source: str) -> dict[str, ast.FunctionDef]:
    tree = ast.parse(source)
    return {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name in {"buy_shares", "sell_shares"}
    }


def test_trade_methods_have_no_implicit_market_issuance() -> None:
    methods = _trade_method_names(TOKEN_SERVICE.read_text(encoding="utf-8"))
    assert set(methods) == {"buy_shares", "sell_shares"}
    for method in methods.values():
        assert not any(
            isinstance(node, ast.Attribute) and node.attr == "ensure_market"
            for node in ast.walk(method)
        )


def test_trade_methods_have_no_fresh_uuid_reference() -> None:
    methods = _trade_method_names(TOKEN_SERVICE.read_text(encoding="utf-8"))
    for method in methods.values():
        assert not any(
            isinstance(node, ast.Name) and node.id == "generate_uuid"
            for node in ast.walk(method)
        )


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
