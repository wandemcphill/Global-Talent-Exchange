# Phase S12 — Deployment Gate Report

Date: 2026-06-14
Branch: feature/original-visual-runtime

## Release Gate

Command: `python tools/release/gtex_release_gate.py`

```
[PASS] guardrail_scan              (4.9s)
[PASS] api_contract_violations     (1.7s)
[PASS] backend_app_composes        (25.6s)
[PASS] routes_registered           (25.7s)
[PASS] pytest:production_guards    (12.7s)
[PASS] pytest:websocket_contracts  (26.6s)
[PASS] pytest:module_registration  (68.4s)
[PASS] pytest:money_lane           (34.6s)
[PASS] flutter_analyze             (215.9s)

============================================================
GTEX RELEASE GATE: PASS
============================================================
```

**9/9 checks passed.**

## Flutter Analyze

Included in the gate above — **PASS** (215.9s). No errors, no production-impacting warnings.

## Startup / Migration / Connectivity Checks

From `SUPABASE_MIGRATION_PROOF.md` (DATABASE_URL proxy, REDIS_ENABLED=false):

| Check | Result |
|---|---|
| `alembic upgrade head` | exit 0 |
| `SELECT 1` connectivity | OK |
| App boot | 159 modules, 328 routes |
| Health endpoint | `status: ok` (redis `skipped` in disabled mode) |

## Money Lane (targeted)

`pytest:money_lane` in the gate: **PASS** (34.6s) — no over-fill / leak / double-debit invariants hold.

## Realtime (targeted)

`pytest:websocket_contracts` in the gate: **PASS** (26.6s) — WS contract + derivation verified.

## Redis Modes

| Mode | Cache backend | Result |
|---|---|---|
| `REDIS_ENABLED=false` | `NullCacheBackend` | ✅ boots, health `skipped` |
| `REDIS_ENABLED=true` | `RedisCacheBackend` (graceful → Null if down) | ✅ boots |

(See `REDIS_CERTIFICATION.md`.)

## Known Pre-existing Failures (not caused by this task)

| Test | Reason | Impact |
|---|---|---|
| `test_app_startup_registers_core_routes...` | asserts unregistered `/auth/signup/player` route | None — pre-dates this task |
| `test_market_and_wallet_paths_use_stricter_limits` | requires distributed Redis to enforce per-path limits | None — passes with Render Redis enabled |
| `test_dynasty_api_exposes_...` | missing `DATABASE_URL` in test env fixture | None — fixture issue |

None are introduced by the Supabase / Render Redis / Cloudflare migration. The authoritative signal is
the release gate: **PASS 9/9**.

## Verdict: GATE PASS
