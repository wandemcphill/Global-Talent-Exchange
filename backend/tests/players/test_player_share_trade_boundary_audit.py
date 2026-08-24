from __future__ import annotations

from scripts.audit_player_share_trade_boundary import inspect_trade_boundary


def test_trade_boundary_audit_detects_implicit_issuance() -> None:
    source = """\
class Example:
    def buy_shares(self):
        return self.ensure_market(player_id="p1")

    def sell_shares(self):
        return self.ensure_market(player_id="p1")
"""
    report = inspect_trade_boundary(source)
    assert report["pass"] is False
    assert {item["method"] for item in report["violations"]} == {"buy_shares", "sell_shares"}


def test_trade_boundary_audit_accepts_existing_market_lookup() -> None:
    source = """\
class Example:
    def buy_shares(self):
        return self.get_market(player_id="p1")

    def sell_shares(self):
        return self.get_market(player_id="p1")
"""
    report = inspect_trade_boundary(source)
    assert report["pass"] is True
    assert report["violations"] == []
