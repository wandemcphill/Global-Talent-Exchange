from __future__ import annotations

from pathlib import Path

from scripts.audit_wallet_payments_treasury_release import audit


ROOT = Path(__file__).resolve().parents[2]


def test_wallet_payments_treasury_release_gate_passes() -> None:
    report = audit()
    assert report["pass"] is True, report
    assert report["violations"] == []
    assert report["read_only"] is True


def test_live_money_movement_surfaces_are_present() -> None:
    expected = [
        ROOT / "app" / "wallets" / "service.py",
        ROOT / "app" / "wallets" / "rail_service.py",
        ROOT / "app" / "services" / "payment_gateway_service.py",
        ROOT / "app" / "treasury" / "service.py",
        ROOT / "app" / "admin_finance" / "service.py",
        ROOT / "app" / "admin_finance" / "router.py",
    ]
    assert all(path.exists() for path in expected)
