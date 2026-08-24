from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "audit_match_engine_competition_economy_release.py"
)


def _audit_module():
    spec = importlib.util.spec_from_file_location("group4_audit", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_match_engine_competition_economy_release_audit_passes() -> None:
    report = _audit_module().audit()
    assert report["pass"] is True
    assert report["violations"] == []
    assert report["read_only"] is True
