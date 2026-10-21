from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "audit_group6_production_readiness.py"
)
SPEC = importlib.util.spec_from_file_location("audit_group6_production_readiness", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_group6_repository_readiness_has_no_static_violations() -> None:
    report = MODULE.check()
    assert report["pass"] is True, report


def test_group6_runtime_inputs_are_explicitly_tracked() -> None:
    report = MODULE.check()
    required = report["runtime_inputs_required"]
    assert "live KoraPay credentials and public callbacks" in required
    assert "5000+ real-player import and issuance cohort" in required
    assert "production Unity runner license" in required


def test_p6_current_engine_hardening_gates_are_verified() -> None:
    report = MODULE.check()
    p6_gates = report["evidence"]["p6_current_engine_hardening"]
    expected_gates = (
        "p6_01_unity_windows_ci_gate",
        "p6_02_current_engine_ownership",
        "p6_03_full_session_playback_validation",
        "p6_04_release_path_no_debug_overlay",
        "p6_05_staging_soak_run",
        "p6_06_hosted_live_verification",
        "p6_07_live_observability",
        "p6_08_rollback_operator_workflow",
        "p6_09_render_content_signoff",
        "p6_10_runtime_resilience_verification",
        "p6_11_final_gate_review",
    )
    for gate in expected_gates:
        assert p6_gates.get(gate) is True, f"Expected {gate} to be True in {p6_gates}"


def test_p6_unblock_checklist_and_gap_backlog_record_final_gate_review() -> None:
    checklist = (ROOT / "docs" / "GTEX_P6_UNBLOCK_CHECKLIST.md").read_text(encoding="utf-8")
    p6_01_doc = (ROOT / "docs" / "GTEX_P6_01_UNITY_WINDOWS_CI_GATE.md").read_text(encoding="utf-8")
    p6_09_doc = (ROOT / "docs" / "GTEX_P6_09_RENDER_CONTENT_SIGNOFF.md").read_text(encoding="utf-8")
    backlog = (ROOT / "docs" / "reports" / "GTEX_P6_PRODUCTION_GAP_BACKLOG.md").read_text(encoding="utf-8")
    group6_status = (ROOT / "docs" / "reports" / "GTEX_GROUP6_STATUS.md").read_text(encoding="utf-8")

    assert "Current status: `PASSED`" in p6_01_doc
    assert "Current status: `PASSED`" in p6_09_doc
    assert "## Final Gate Review Note (`P6-11`)" in checklist
    assert "## P6-11 Repo-Side Verification & Final Gate Review Note" in backlog
    assert "P6 final gate review (`P6-11`)" in group6_status

    for item_id in (f"P6-{index:02d}" for index in range(1, 12)):
        matching_rows = [
            line for line in checklist.splitlines() if line.startswith(f"| {item_id} |")
        ]
        assert len(matching_rows) == 1, f"Missing row for {item_id}"
        assert matching_rows[0].endswith("| `PASSED` |"), f"Row {item_id} is not PASSED: {matching_rows[0]}"
