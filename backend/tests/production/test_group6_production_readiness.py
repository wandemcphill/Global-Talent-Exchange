from __future__ import annotations

import importlib.util
from pathlib import Path

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
