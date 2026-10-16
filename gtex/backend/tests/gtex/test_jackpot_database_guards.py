from __future__ import annotations

from pathlib import Path


MIGRATION = Path(__file__).parents[2] / "migrations" / "versions" / "20260914_0123_jackpot_database_guards.py"


def test_jackpot_database_guard_migration_contains_settlement_invariants() -> None:
    text = MIGRATION.read_text()
    assert "uq_gtex_jackpot_open_pool" in text
    assert "uq_gtex_jackpot_payout_round_rank" in text
    assert "uq_gtex_jackpot_contribution_source" in text
    assert "uq_gtex_jackpot_payout_ledger_reference" in text
    assert "Cannot install Jackpot database guards" in text
