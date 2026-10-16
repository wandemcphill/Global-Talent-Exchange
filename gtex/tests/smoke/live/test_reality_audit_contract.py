from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


def _load_reality_audit() -> ModuleType:
    repo_root = Path(__file__).resolve().parents[3]
    audit_path = repo_root / "tools" / "audit" / "reality_audit.py"
    spec = importlib.util.spec_from_file_location("gtex_reality_audit", audit_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_strict_live_runtime_contract_has_no_fixture_or_mock_production_paths() -> None:
    audit = _load_reality_audit()

    assert audit._strict_live_failures() == []


def test_strict_live_phase2_smoke_contract_is_registered() -> None:
    audit = _load_reality_audit()

    assert audit._strict_live_phase2_smoke_failures() == []


def test_render_payment_contract_disables_paystack_and_keeps_korapay_env_only() -> None:
    audit = _load_reality_audit()

    assert audit._render_config_failures() == []


def test_reality_audit_secret_scanner_flags_committed_live_payment_keys(tmp_path: Path) -> None:
    audit = _load_reality_audit()
    secret_file = tmp_path / "backend" / "app" / "settings.py"
    secret_file.parent.mkdir(parents=True)
    live_secret_value = "sk_" + "live_" + "FAKEPAYMENTKEY123456789"
    secret_file.write_text(
        ("GTE_KORAPAY_" + "SECRET_KEY = '" + live_secret_value + "'\n"),
        encoding="utf-8",
    )

    original_root = audit.REPO_ROOT
    audit.REPO_ROOT = tmp_path
    try:
        assert audit._python_secret_scan([secret_file]) == ["backend/app/settings.py:1"]
    finally:
        audit.REPO_ROOT = original_root
