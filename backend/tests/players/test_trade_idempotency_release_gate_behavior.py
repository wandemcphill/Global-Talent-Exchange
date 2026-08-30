from __future__ import annotations

from pathlib import Path


def test_trade_idempotency_release_gate_targets_behavioral_regression_suite() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    gate = repository_root / "scripts" / "audit_player_share_trade_idempotency.py"
    source = gate.read_text(encoding="utf-8")

    assert "test_trade_idempotency_conflicts.py" in source
    assert "subprocess.run" in source
    assert "pytest" in source
    assert "behavioral" in source


def test_strict_trade_idempotency_gate_executes_behavioral_checks() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    gate = repository_root / "scripts" / "audit_player_share_trade_idempotency.py"
    source = gate.read_text(encoding="utf-8")

    assert "report = audit(behavioral=args.behavioral or args.strict)" in source
    assert "report[\"pass\"] = bool(report[\"pass\"] and behavior[\"pass\"])" in source
