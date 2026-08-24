from __future__ import annotations

from scripts.certify_player_share_economy import certify


def _passing_holdings_report():
    return {
        "gates": {
            "no_negative_holdings": True,
            "no_negative_average_costs": True,
            "no_negative_dividend_balances": True,
            "holdings_do_not_exceed_circulation": True,
            "holdings_do_not_exceed_total_supply": True,
        },
        "read_only": True,
    }


def test_certification_combines_trade_lifecycle_and_holdings_gates(monkeypatch):
    monkeypatch.setattr(
        "scripts.certify_player_share_economy.audit_lifecycle",
        lambda **_: {
            "gates": {
                "no_blocked_active_markets": True,
                "no_active_markets_missing_liquidity_account": True,
                "all_active_markets_explicitly_issued": True,
                "all_active_liquidity_balances_reconcile": True,
                "no_negative_active_liquidity": True,
                "all_active_liquidity_is_coin": True,
            },
            "read_only": True,
        },
    )
    monkeypatch.setattr(
        "scripts.certify_player_share_economy.audit_holdings",
        lambda **_: _passing_holdings_report(),
    )
    monkeypatch.setattr(
        "scripts.certify_player_share_economy.audit_trade_boundary",
        lambda: {"pass": True, "read_only": True},
    )

    report = certify(database_url=None, batch_size=100)

    assert report["read_only"] is True
    assert report["pass"] is True
    assert all(report["gates"].values())


def test_certification_fails_closed_when_trade_boundary_fails(monkeypatch):
    monkeypatch.setattr(
        "scripts.certify_player_share_economy.audit_lifecycle",
        lambda **_: {"gates": {"all_active_markets_explicitly_issued": True}},
    )
    monkeypatch.setattr(
        "scripts.certify_player_share_economy.audit_holdings",
        lambda **_: _passing_holdings_report(),
    )
    monkeypatch.setattr(
        "scripts.certify_player_share_economy.audit_trade_boundary",
        lambda: {"pass": False, "read_only": True},
    )

    report = certify(database_url=None, batch_size=100)

    assert report["pass"] is False
    assert report["gates"]["trade_boundary"] is False
