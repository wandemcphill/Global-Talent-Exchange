"""Unit tests for the reality-audit Render config parser itself.

These feed synthetic render.yaml fixtures directly to
``_render_config_failures`` (via a monkeypatched ``REPO_ROOT``) rather than
relying on the live repo's render.yaml, so both the pass path and the fail
path are pinned. This guards against the parser regressing back into
fragile string slicing that either false-positives on a correct render.yaml
or, worse, false-negatives on a genuinely wrong one because it grabbed the
first line matching a key name anywhere in the file instead of scoping the
lookup to the right service block.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

VALID_RENDER_YAML = """
services:
  - name: gtex-api
    type: web
    envVars:
      - key: GTE_KORAPAY_PUBLIC_KEY
        sync: false
      - key: GTE_KORAPAY_SECRET_KEY
        sync: false
      - key: GTE_KORAPAY_ENCRYPTION_KEY
        sync: false
      - key: GTE_KORAPAY_WEBHOOK_SECRET
        sync: false
      - key: TREASURY_BANK_NAME
        sync: false
      - key: TREASURY_ACCOUNT_NAME
        sync: false
      - key: TREASURY_ACCOUNT_NUMBER
        sync: false
      - key: GTE_KORAPAY_NOTIFICATION_URL
        value: https://gtex-api-opea.onrender.com/integrations/payments/korapay/webhook
      - key: GTE_ENABLE_PAYSTACK
        value: "false"
      # Deliberately reused key name on a DIFFERENT service below with a
      # wrong value, to prove lookups are scoped per-service.
      - key: GTE_API_BASE_URL
        value: https://not-the-real-api.example.com

  - name: gtex-web
    type: web
    envVars:
      - key: GTE_API_BASE_URL
        value: https://gtex-api-opea.onrender.com
      - key: GTE_BACKEND_MODE
        value: live
"""


def _load_reality_audit() -> ModuleType:
    repo_root = Path(__file__).resolve().parents[3]
    audit_path = repo_root / "tools" / "audit" / "reality_audit.py"
    spec = importlib.util.spec_from_file_location("gtex_reality_audit_parser_test", audit_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def audit() -> ModuleType:
    return _load_reality_audit()


def _with_render_yaml(audit: ModuleType, tmp_path: Path, content: str):
    (tmp_path / "render.yaml").write_text(content, encoding="utf-8")
    original_root = audit.REPO_ROOT
    audit.REPO_ROOT = tmp_path
    return original_root


def test_valid_render_yaml_passes_even_with_key_name_reused_on_other_service(audit: ModuleType, tmp_path: Path) -> None:
    original_root = _with_render_yaml(audit, tmp_path, VALID_RENDER_YAML)
    try:
        assert audit._render_config_failures() == []
    finally:
        audit.REPO_ROOT = original_root


def test_wrong_gtex_web_api_base_url_fails_even_when_gtex_api_happens_to_have_correct_value(
    audit: ModuleType, tmp_path: Path
) -> None:
    """A same-named key holding the RIGHT value on the WRONG service must
    not mask a genuinely broken gtex-web configuration. A parser that
    searches the whole file for the first match of the key name (instead of
    scoping to the gtex-web service) would false-negative here."""
    broken = VALID_RENDER_YAML.replace(
        "https://not-the-real-api.example.com",
        "https://gtex-api-opea.onrender.com",
    ).replace(
        "        value: https://gtex-api-opea.onrender.com\n      - key: GTE_BACKEND_MODE",
        "        value: https://staging-decoy.example.com\n      - key: GTE_BACKEND_MODE",
    )
    original_root = _with_render_yaml(audit, tmp_path, broken)
    try:
        failures = audit._render_config_failures()
        assert any("does not point at the live API base URL" in failure for failure in failures)
    finally:
        audit.REPO_ROOT = original_root


def test_missing_korapay_notification_url_fails(audit: ModuleType, tmp_path: Path) -> None:
    broken = VALID_RENDER_YAML.replace(
        "      - key: GTE_KORAPAY_NOTIFICATION_URL\n"
        "        value: https://gtex-api-opea.onrender.com/integrations/payments/korapay/webhook\n",
        "",
    )
    original_root = _with_render_yaml(audit, tmp_path, broken)
    try:
        failures = audit._render_config_failures()
        assert any("missing the production KoraPay notification URL" in failure for failure in failures)
    finally:
        audit.REPO_ROOT = original_root


def test_paystack_not_disabled_fails(audit: ModuleType, tmp_path: Path) -> None:
    broken = VALID_RENDER_YAML.replace(
        '      - key: GTE_ENABLE_PAYSTACK\n        value: "false"\n',
        '      - key: GTE_ENABLE_PAYSTACK\n        value: "true"\n',
    )
    original_root = _with_render_yaml(audit, tmp_path, broken)
    try:
        failures = audit._render_config_failures()
        assert any("does not explicitly disable Paystack" in failure for failure in failures)
    finally:
        audit.REPO_ROOT = original_root


def test_backend_mode_not_live_fails(audit: ModuleType, tmp_path: Path) -> None:
    broken = VALID_RENDER_YAML.replace(
        "      - key: GTE_BACKEND_MODE\n        value: live\n",
        "      - key: GTE_BACKEND_MODE\n        value: mock\n",
    )
    original_root = _with_render_yaml(audit, tmp_path, broken)
    try:
        failures = audit._render_config_failures()
        assert any("does not force live backend mode" in failure for failure in failures)
    finally:
        audit.REPO_ROOT = original_root


def test_secret_env_missing_sync_false_fails(audit: ModuleType, tmp_path: Path) -> None:
    broken = VALID_RENDER_YAML.replace(
        "      - key: GTE_KORAPAY_SECRET_KEY\n        sync: false\n",
        "      - key: GTE_KORAPAY_SECRET_KEY\n",
    )
    original_root = _with_render_yaml(audit, tmp_path, broken)
    try:
        failures = audit._render_config_failures()
        assert any("GTE_KORAPAY_SECRET_KEY" in failure and "sync: false" in failure for failure in failures)
    finally:
        audit.REPO_ROOT = original_root


def test_secret_env_hardcoded_value_fails(audit: ModuleType, tmp_path: Path) -> None:
    broken = VALID_RENDER_YAML.replace(
        "      - key: GTE_KORAPAY_SECRET_KEY\n        sync: false\n",
        "      - key: GTE_KORAPAY_SECRET_KEY\n        sync: false\n        value: sk_live_hardcoded\n",
    )
    original_root = _with_render_yaml(audit, tmp_path, broken)
    try:
        failures = audit._render_config_failures()
        assert any("GTE_KORAPAY_SECRET_KEY" in failure and "hard-code" in failure for failure in failures)
    finally:
        audit.REPO_ROOT = original_root


def test_missing_gtex_api_service_fails(audit: ModuleType, tmp_path: Path) -> None:
    only_web = """
services:
  - name: gtex-web
    type: web
    envVars:
      - key: GTE_API_BASE_URL
        value: https://gtex-api-opea.onrender.com
      - key: GTE_BACKEND_MODE
        value: live
"""
    original_root = _with_render_yaml(audit, tmp_path, only_web)
    try:
        failures = audit._render_config_failures()
        assert any("missing the gtex-api service" in failure for failure in failures)
    finally:
        audit.REPO_ROOT = original_root


def test_invalid_yaml_reports_failure_instead_of_raising(audit: ModuleType, tmp_path: Path) -> None:
    original_root = _with_render_yaml(audit, tmp_path, "services: [unterminated")
    try:
        failures = audit._render_config_failures()
        assert failures
        assert any("not valid YAML" in failure for failure in failures)
    finally:
        audit.REPO_ROOT = original_root
