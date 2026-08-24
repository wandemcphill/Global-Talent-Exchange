from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_group4_contract_documents_authoritative_settlement_and_ledger_path() -> None:
    contract = (
        ROOT.parent / "docs" / "PHASE_A_GROUP_4_MATCH_ENGINE_CLOSURE.md"
    ).read_text(encoding="utf-8")
    assert "CompetitionMatchService.complete_match" in contract
    assert "MatchEconomyEngine" in contract
    assert "wallet ledger" in contract
    assert "stats_applied" in contract
