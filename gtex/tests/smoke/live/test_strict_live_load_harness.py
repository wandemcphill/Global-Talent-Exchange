from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import ModuleType


def _load_harness() -> ModuleType:
    repo_root = Path(__file__).resolve().parents[3]
    harness_path = repo_root / "tools" / "load" / "strict_live_runtime_load.py"
    spec = importlib.util.spec_from_file_location("strict_live_runtime_load", harness_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_strict_live_load_harness_rejects_synthetic_payloads() -> None:
    harness = _load_harness()

    reason = harness._walk_forbidden_payload(
        {
            "runtime_source": "persisted_backend_authority",
            "items": [{"source": "fixture_repository"}],
        }
    )

    assert reason == "synthetic_source:$.items[0].source"


def test_strict_live_load_harness_summarizes_failures() -> None:
    harness = _load_harness()

    summary = harness.summarize_results(
        [
            harness.ProbeResult(endpoint="/api/session/bootstrap", status_code=200, duration_ms=10, ok=True),
            harness.ProbeResult(
                endpoint="/api/session/bootstrap",
                status_code=200,
                duration_ms=20,
                ok=False,
                reason="synthetic_source:$.source",
            ),
        ],
        duration_seconds=0.05,
    )

    assert summary["strict_live"] is True
    assert summary["failed"] == 1
    assert summary["endpoints"]["/api/session/bootstrap"]["avg_ms"] == 15.0
    assert summary["endpoints"]["/api/session/bootstrap"]["failures"] == {
        "synthetic_source:$.source": 1,
    }
