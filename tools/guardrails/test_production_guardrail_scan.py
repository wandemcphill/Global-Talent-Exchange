from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("production_guardrail_scan.py")
SPEC = importlib.util.spec_from_file_location("production_guardrail_scan", MODULE_PATH)
assert SPEC is not None
production_guardrail_scan = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = production_guardrail_scan
SPEC.loader.exec_module(production_guardrail_scan)


def _rule(key: str):
    return next(rule for rule in production_guardrail_scan.RULES if rule.key == key)


def test_noncanonical_payment_rail_rule_rejects_unsupported_provider() -> None:
    rule = _rule("noncanonical-payment-rail")

    assert rule.pattern.search("provider: 'flutterwave'") is not None
    assert rule.pattern.search("payment gateway Stripe checkout") is not None
    assert rule.pattern.search("crypto payment rail") is not None
    assert rule.pattern.search("provider: 'korapay'") is None
    assert rule.pattern.search("method: 'Manual bank transfer'") is None
    assert rule.pattern.search("Do not present GTex as cryptocurrency") is None


def test_fake_authority_rule_rejects_fake_backend_owned_data() -> None:
    rule = _rule("fake-production-authority-data")

    assert rule.pattern.search("mock balance") is not None
    assert rule.pattern.search("scores fallback") is not None
    assert rule.pattern.search("backend supplied balance") is None
    assert rule.pattern.search("Awaiting result") is None


def test_fixture_mode_rule_rejects_production_activation() -> None:
    rule = _rule("fixture-mode-production-enabled")

    assert rule.pattern.search("enableCapitalFixtures: true") is not None
    assert rule.pattern.search("mode: GteBackendMode.fixture") is not None
    assert rule.pattern.search("allowFixtureMode ? GteBackendMode.fixture") is not None
    assert rule.pattern.search("mode == GteBackendMode.fixture") is None


def test_production_classification_marks_new_rules_as_violations() -> None:
    payment_rule = _rule("noncanonical-payment-rail")
    fixture_rule = _rule("fixture-mode-production-enabled")
    fake_rule = _rule("fake-production-authority-data")

    assert production_guardrail_scan._classify(
        "backend/app/wallets/providers/registry.py",
        "provider = 'paypal'",
        payment_rule,
    )[0] == "violation"
    assert production_guardrail_scan._classify(
        "frontend/lib/data/gte_mock_api.dart",
        "return GteMockApi(enableCapitalFixtures: true);",
        fixture_rule,
    )[0] == "fixed"
    assert production_guardrail_scan._classify(
        "frontend/lib/features/app_routes/gte_feature_route_builders.dart",
        "backendMode: GteBackendMode.fixture,",
        fixture_rule,
    )[0] == "violation"
    assert production_guardrail_scan._classify(
        "frontend/lib/features/compete/fixture_screen.dart",
        "final score = fake score;",
        fake_rule,
    )[0] == "violation"
    assert production_guardrail_scan._classify(
        "frontend/lib/features/app_routes/gte_feature_route_builders.dart",
        "Route-level fixture fallback is disabled.",
        fake_rule,
    )[0] == "fixed"
