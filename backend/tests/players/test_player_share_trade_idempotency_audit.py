from __future__ import annotations

from scripts.audit_player_share_trade_idempotency import inspect_trade_idempotency


def test_trade_methods_are_flagged_when_using_random_uuid() -> None:
    report = inspect_trade_idempotency(
        """
from app.models.base import generate_uuid
class Service:
    def buy_shares(self):
        return f'trade:{generate_uuid()}'
    def sell_shares(self):
        return f'trade:{generate_uuid()}'
"""
    )
    assert report["pass"] is False
    assert {item["method"] for item in report["violations"]} == {"buy_shares", "sell_shares"}


def test_trade_methods_pass_when_reference_is_caller_keyed() -> None:
    report = inspect_trade_idempotency(
        """
class Service:
    def buy_shares(self, idempotency_key):
        return f'trade:{idempotency_key}'
    def sell_shares(self, idempotency_key):
        return f'trade:{idempotency_key}'
"""
    )
    assert report["pass"] is True
    assert report["violations"] == []
