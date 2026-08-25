from __future__ import annotations

from backend.scripts.audit_group6_production_readiness import check


def test_group6_repository_readiness_has_no_static_violations() -> None:
    report = check()
    assert report["pass"] is True, report


def test_group6_runtime_inputs_are_explicitly_tracked() -> None:
    report = check()
    required = report["runtime_inputs_required"]
    assert "live KoraPay credentials and public callbacks" in required
    assert "5000+ real-player import and issuance cohort" in required
    assert "production Unity runner license" in required
