from __future__ import annotations

from scripts.audit_player_share_trade_idempotency import (
    inspect_router,
    inspect_trade_idempotency,
)


def test_trade_methods_are_flagged_when_missing_idempotency_contract() -> None:
    report = inspect_trade_idempotency(
        """
class Service:
    def buy_shares(self):
        return 'trade:random'
    def sell_shares(self):
        return 'trade:random'
"""
    )
    assert report["pass"] is False
    methods = {item["method"] for item in report["violations"] if "method" in item}
    assert methods == {"buy_shares", "sell_shares"}


def test_trade_methods_pass_when_reference_is_caller_keyed() -> None:
    report = inspect_trade_idempotency(
        """
class Service:
    def _run_trade_with_boundary(self):
        return None
    def _idempotency_reference(self):
        return 'trade:deterministic'
    def _replay_idempotent_trade(self):
        return None
    def _bind_trade_idempotency(self):
        return None
    def buy_shares(self, idempotency_key=None):
        return self._run_trade_with_boundary()
    def sell_shares(self, idempotency_key=None):
        return self._run_trade_with_boundary()
    def consume_player_share_idempotency_key(self):
        return None
"""
    )
    assert report["pass"] is True
    assert report["violations"] == []


def test_router_without_optional_key_forwarding_is_a_warning_not_a_release_failure() -> None:
    report = inspect_router(
        """
def buy_player_shares():
    return service.buy_shares(actor=actor, player_id='p1', share_count=1)

def sell_player_shares():
    return service.sell_shares(actor=actor, player_id='p1', share_count=1)
"""
    )
    assert report["pass"] is True
    assert report["violations"] == []
    assert {item["endpoint"] for item in report["warnings"]} == {
        "buy_player_shares",
        "sell_player_shares",
    }
