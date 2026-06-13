# Phase S8 — Web Deployment Audit

Date: 2026-06-14

Scan over `frontend/lib`, build scripts, and env templates for `localhost`, `127.0.0.1`,
`onrender.com`, `GTE_API_BASE_URL`, `GTE_WS_BASE_URL`, `ws://`, `wss://`.

## Summary

`frontend/lib` localhost/127.0.0.1 occurrences: **55** — all in fixture constructors or host-classifier
logic, none are active production base URLs.

| File | Line | Production Safe? | Action |
|---|---|---|---|
| `frontend/lib/app/gte_app_config.dart` | 19,40,76,92 | ✅ | Reads `GTE_API_BASE_URL` via `String.fromEnvironment` — compile-time injected |
| `frontend/lib/app/gte_app_config.dart` | 71 | ✅ | Throws `StateError` if empty in live mode — no fallback |
| `frontend/lib/app/gte_bootstrap_failure_app.dart` | 62 | ✅ | `127.0.0.1` is text in a developer error hint, not an active URL |
| `frontend/lib/**/*fixture*`, `.fixture()` ctors | (×~50) | ✅ | Gated by `GteBackendMode.fixture`; unreachable in live builds |
| `frontend/lib/features/3d/services/match_3d_live_bootstrap_service.dart` | 135 | ✅ | Host **classifier** (`local` vs `custom`) reading the configured base URL — not a hardcoded endpoint |
| `frontend/lib/features/match_center/live_match_session_service.dart` | (scheme) | ✅ | WS scheme derived from base URL (`https→wss`, `http→ws`) |
| `frontend/lib/shared/providers/app_realtime_provider.dart` | (scheme) | ✅ | WS scheme derived from base URL |
| `frontend/lib/shared/providers/transfer_provider.dart` | (scheme) | ✅ | WS scheme derived from base URL |
| `frontend/lib/shared/realtime/gtex_realtime_providers.dart` | (scheme) | ✅ | WS scheme derived from base URL |
| `ops/cloudflare/build-frontend.sh` | 14 | ✅ | `: "${GTE_API_BASE_URL:?...}"` hard-fail; no localhost default |
| `ops/render/build-frontend.sh` | — | ✅ | Same hard-fail guard (historical Render static) |
| `.env.production.example` | — | ✅ | Template placeholders only, no real hosts |

## Key Findings

- **No `GTE_WS_BASE_URL` variable exists** — the WebSocket URL is always derived from the API base URL,
  so there is no second endpoint to drift.
- **No active localhost base URL** in any live code path. All `localhost`/`127.0.0.1` strings are either
  fixture-mode constructors (gated by `GteBackendMode.fixture`), a host classifier, or developer hint text.
- **No hardcoded `onrender.com`** in `frontend/lib`. The only `onrender.com` in the blueprint is the
  historical `gtex-web` static site, superseded by Cloudflare Pages (see `DATABASE_REFERENCE_AUDIT.md`).

## Verdict: WEB DEPLOYMENT PRODUCTION-SAFE

No localhost leakage in live paths. URL fully env-injected; WS derived. No stale endpoints.
