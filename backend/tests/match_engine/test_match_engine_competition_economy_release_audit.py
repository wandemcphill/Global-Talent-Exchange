from __future__ import annotations

from app.scripts_match_engine_audit_loader import load_match_engine_competition_economy_audit


def test_match_engine_competition_economy_release_audit_passes() -> None:
    report = load_match_engine_competition_economy_audit()
    assert report["pass"] is True
    assert report["violations"] == []
    assert report["read_only"] is True
