from __future__ import annotations

from pathlib import Path

from scripts.audit_player_share_release import _boundary_check


ROOT = Path(__file__).resolve().parents[2]


def test_player_share_release_boundary_is_certified() -> None:
    report = _boundary_check()
    assert report["passed"], report["violations"]


def test_strict_issuer_is_present() -> None:
    path = ROOT / "scripts" / "issue_player_share_markets_strict.py"
    assert path.is_file()
    source = path.read_text(encoding="utf-8")
    assert "issue_market(" in source
    assert "ensure_market(" not in source


def test_release_audit_is_read_only() -> None:
    path = ROOT / "scripts" / "audit_player_share_release.py"
    source = path.read_text(encoding="utf-8")
    assert '"read_only": True' in source
    assert "session.commit" not in source
