from __future__ import annotations

from pathlib import Path

from backend.scripts.audit_player_share_release_gate import inspect_repository


def test_player_share_release_gate_is_green():
    report = inspect_repository()

    assert report["pass"] is True
    assert all(report["gates"].values())
    assert report["violations"] == []


def test_release_gate_targets_production_files():
    root = Path(__file__).resolve().parents[2]
    assert (root / "app" / "players" / "token_service.py").exists()
    assert (root / "app" / "players" / "router.py").exists()
    assert (root / "app" / "players" / "trade_boundary.py").exists()
