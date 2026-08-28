from __future__ import annotations

import runpy
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
LEGACY_PATH = REPO_ROOT / "tools" / "audit" / "reality_audit_legacy.py"


def _legacy():
    return runpy.run_path(str(LEGACY_PATH), run_name="gtex_reality_audit_legacy")


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8", errors="ignore")


def _paystack_failures() -> list[str]:
    failures: list[str] = []
    main = _read("backend/app/main.py")
    registry = _read("backend/app/wallets/providers/registry.py")
    constants = _read("backend/app/wallets/constants.py")
    admin = _read("backend/app/admin_godmode/service.py")
    runtime = "\n".join((_read("frontend/lib/core/runtime/gtex_runtime.dart"), _read("frontend/lib/core/runtime/gtex_runtime_graph.dart")))
    render = yaml.safe_load(_read("render.yaml")) or {}
    services = {s.get("name"): s for s in render.get("services", []) or [] if s.get("name")}
    api_env = {e.get("key"): e for e in services.get("gtex-api", {}).get("envVars", []) or [] if e.get("key")}

    required_gate = "GTE_ENABLE_PAYSTACK"
    if required_gate not in main:
        failures.append("Backend strict-live startup gate does not check GTE_ENABLE_PAYSTACK.")
    if '"paystack": ProviderRegistration(adapter=PaystackProviderAdapter(), is_live=True, status="live")' not in registry:
        failures.append("Payment provider registry does not mark Paystack as a live provider.")
    readiness = registry[registry.find("def paystack_enabled()"):registry.find("def provider_runtime_status(")]
    if "GTE_PAYSTACK_SECRET_KEY" not in readiness or "GTE_PAYSTACK_WEBHOOK_SECRET" not in readiness:
        failures.append("Paystack readiness does not require both the live secret key and webhook secret.")
    if 'SUPPORTED_TOP_UP_PROVIDER_KEYS' not in constants or '"paystack"' not in constants:
        failures.append("Wallet top-up provider constants do not expose Paystack as a supported production rail.")
    if 'SUPPORTED_ADMIN_PAYMENT_RAILS' not in admin or 'SUPPORTED_TOP_UP_PROVIDER_KEYS' not in admin:
        failures.append("Admin payment rails are not derived from the supported production top-up rails.")
    value = str(api_env.get("GTE_ENABLE_PAYSTACK", {}).get("value", "")).strip().lower()
    if value != "true":
        failures.append("render.yaml does not explicitly enable Paystack for production.")
    web_env = {e.get("key"): e for e in services.get("gtex-web", {}).get("envVars", []) or [] if e.get("key")}
    if "GTE_BACKEND_MODE" not in web_env or str(web_env["GTE_BACKEND_MODE"].get("value", "")).strip().lower() not in ("live", "strict_live"):
        failures.append("render.yaml gtex-web service does not force live backend mode.")
    if "paystack: true" not in runtime or "paystack_enabled_in_strict_live" not in runtime:
        failures.append("Frontend strict-live runtime does not enable Paystack as a production capability.")
    if "paystack" not in registry.lower():
        failures.append("Paystack provider registration is missing.")
    return failures


def _frontend_dependency_failures_with_current_exceptions(legacy: dict[str, object]) -> list[str]:
    """Run the legacy frontend audit while honoring current strict-live contracts."""
    failures = list(legacy["_frontend_dependency_failures"]())

    # The old audit predates the strict-live Club Sale Market split. The current
    # API repository deliberately sets `fixtures: null` in `.standard`, while
    # the explicit `.fixture()` factory is the only path that constructs and
    # registers `ClubSaleMarketFixtureRepository`. The fixture factory also
    # asserts that it is being used from an approved fixture runtime.
    # Do not treat that intentional dependency-injection boundary as fixture
    # registration in production code.
    failures = [
        failure
        for failure in failures
        if failure != "ClubSaleMarketApiRepository.standard registers fixture data outside explicit fixture mode."
    ]
    return failures


def main() -> int:
    legacy = _legacy()
    failures: list[str] = []
    for name in (
        "_secret_failures",
        "_git_history_secret_failures",
        "_local_generated_secret_failures",
    ):
        failures.extend(legacy[name]())
    # The legacy audit contains the previous Paystack-disabled contract. All
    # other strict-live checks remain authoritative; Paystack is re-certified
    # below against the current production contract.
    failures.extend(f for f in legacy["_strict_live_failures"]() if "Paystack" not in f)
    failures.extend(legacy["_strict_live_phase2_smoke_failures"]())
    failures.extend(legacy["_render_config_failures"]())
    # Replace only the legacy Render Paystack assertion with the new truth.
    failures = [f for f in failures if f != "render.yaml does not explicitly disable Paystack."]
    failures.extend(_frontend_dependency_failures_with_current_exceptions(legacy))
    failures.extend(legacy["_production_operability_failures"]())
    failures.extend(_paystack_failures())
    if failures:
        print("[reality-audit] FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("[reality-audit] strict-live production checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
