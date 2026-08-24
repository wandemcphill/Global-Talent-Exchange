from __future__ import annotations

from scripts.audit_admin_control_plane_release import audit


def test_admin_control_plane_release_gate_passes() -> None:
    report = audit()
    assert report["read_only"] is True
    assert report["pass"] is True, report
    assert report["violations"] == []


def test_admin_control_plane_audit_requires_capability_and_audit_sinks() -> None:
    report = audit()
    assert report["contract"]
    assert "every high-risk admin mutation" in str(report["contract"])
