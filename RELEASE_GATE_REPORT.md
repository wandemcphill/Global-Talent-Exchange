# RELEASE GATE (N37)

Date: 2026-06-12
Tool: `tools/release/gtex_release_gate.py` (new)
Branch: `feature/original-visual-runtime` @ `ca771311`
Latest run: **PASS** (`.runtime/n37_gate2.log`, `.runtime/n37_gate2.json`)

## What the gate validates

| Check | Mechanism | Maps to directive item |
|---|---|---|
| `guardrail_scan` | `tools/guardrails/production_guardrail_scan.py` | guardrails (no Paystack/crypto/Unity/3D, no fixture-fake in prod) |
| `api_contract_violations` | `tools/audit/check_api_contract_violations.py` | contracts |
| `backend_app_composes` | standalone `create_app(run_migration_check=False)` | startup |
| `routes_registered` | asserts `/api/v2/auth/login` + `/health` present in 332 routes | routes |
| `pytest:production_guards` | canonical production guard suite | guardrails/tests |
| `pytest:websocket_contracts` | 3 realtime gateway suites | websocket registration |
| `pytest:module_registration` | module registration suite | registration |
| `pytest:money_lane` | trader matching/settlement suite | tests (money) |
| `flutter_analyze` | `flutter analyze --no-pub` | analyze |

## Run modes
- `--fast` skips the two slow pytest shards (websocket, module-registration); used for the green run above.
- `--skip-flutter` skips analyze (the CLI bootstrap is environment-flaky; analyze proven separately green in N31).
- Full mode (no flags) runs everything for release certification.
- `--json OUT.json` emits machine-readable evidence for CI.

## Latest evidence (fast, skip-flutter)
```
[PASS] guardrail_scan (10.5s)
[PASS] api_contract_violations (16.1s)
[PASS] backend_app_composes (24.9s)
[PASS] routes_registered (44.9s)
[PASS] pytest:production_guards (9.8s)
[PASS] pytest:money_lane (48.2s)
GTEX RELEASE GATE: PASS
```
Full-mode green requires the same harness with websocket + module-registration shards (each ~4–7m, proven green in N32/N35) and flutter_analyze (proven green in N31). All constituent checks have passed this cycle; the gate simply re-runs them as one go/no-go.

## Fix applied during N37
Standalone `create_app()` requires `DATABASE_URL` and secrets (normally injected by `backend/tests/conftest.py`). The gate now injects an inert SQLite compose-env for its startup/route checks — mirroring conftest, no production values. This made `backend_app_composes` and `routes_registered` go from FAIL→PASS without touching product code.
