from __future__ import annotations

import pytest

from app.core.database import create_database_engine, load_model_modules
from app.models.base import Base
from scripts.certify_player_share_economy import certify


@pytest.fixture()
def test_db_url(tmp_path):
    load_model_modules()
    db_file = tmp_path / "cert_test.db"
    db_url = f"sqlite:///{db_file}"
    engine = create_database_engine(db_url)
    Base.metadata.create_all(engine)
    engine.dispose()
    return db_url


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


def _passing_lifecycle_report():
    return {
        "gates": {
            "no_blocked_active_markets": True,
            "no_active_markets_missing_liquidity_account": True,
            "all_active_markets_explicitly_issued": True,
            "all_active_liquidity_balances_reconcile": True,
            "no_negative_active_liquidity": True,
            "all_active_liquidity_is_coin": True,
        },
        "read_only": True,
    }


def _passing_market_integrity_report():
    return {"pass": True, "read_only": True}


def _passing_event_reconciliation_report():
    return {
        "pass": True,
        "read_only": True,
        "gates": {
            "market_circulation_reconciles_to_event_deltas": True,
            "no_events_without_market": True,
        },
    }


def _passing_trade_idempotency_report():
    return {"pass": True, "read_only": True}


def _patch_common_gates(monkeypatch):
    monkeypatch.setattr(
        "scripts.certify_player_share_economy.audit_lifecycle",
        lambda **_: _passing_lifecycle_report(),
    )
    monkeypatch.setattr(
        "scripts.certify_player_share_economy.audit_holdings",
        lambda **_: _passing_holdings_report(),
    )
    monkeypatch.setattr(
        "scripts.certify_player_share_economy.audit_market_integrity",
        lambda **_: _passing_market_integrity_report(),
    )
    monkeypatch.setattr(
        "scripts.certify_player_share_economy.audit_event_reconciliation",
        lambda **_: _passing_event_reconciliation_report(),
    )
    monkeypatch.setattr(
        "scripts.certify_player_share_economy.audit_trade_idempotency",
        lambda **_: _passing_trade_idempotency_report(),
    )


def test_certification_executes_against_actual_database_schema(test_db_url):
    report = certify(database_url=test_db_url, batch_size=100)

    assert report["read_only"] is True
    assert report["pass"] is True
    assert all(report["gates"].values())


def test_certification_combines_all_economic_gates(monkeypatch, test_db_url):
    _patch_common_gates(monkeypatch)
    monkeypatch.setattr(
        "scripts.certify_player_share_economy.audit_trade_boundary",
        lambda: {"pass": True, "read_only": True},
    )
    monkeypatch.setattr(
        "scripts.certify_player_share_economy.audit_issuer_boundary",
        lambda: {"pass": True, "read_only": True},
    )

    report = certify(database_url=test_db_url, batch_size=100)

    assert report["read_only"] is True
    assert report["pass"] is True
    assert all(report["gates"].values())


def test_certification_fails_closed_when_trade_boundary_fails(monkeypatch, test_db_url):
    _patch_common_gates(monkeypatch)
    monkeypatch.setattr(
        "scripts.certify_player_share_economy.audit_trade_boundary",
        lambda: {"pass": False, "read_only": True},
    )
    monkeypatch.setattr(
        "scripts.certify_player_share_economy.audit_issuer_boundary",
        lambda: {"pass": True, "read_only": True},
    )

    report = certify(database_url=test_db_url, batch_size=100)

    assert report["pass"] is False
    assert report["gates"]["trade_boundary"] is False


def test_certification_fails_closed_when_issuer_boundary_fails(monkeypatch, test_db_url):
    _patch_common_gates(monkeypatch)
    monkeypatch.setattr(
        "scripts.certify_player_share_economy.audit_trade_boundary",
        lambda: {"pass": True, "read_only": True},
    )
    monkeypatch.setattr(
        "scripts.certify_player_share_economy.audit_issuer_boundary",
        lambda: {"pass": False, "read_only": True},
    )

    report = certify(database_url=test_db_url, batch_size=100)

    assert report["pass"] is False
    assert report["gates"]["issuer_boundary"] is False
