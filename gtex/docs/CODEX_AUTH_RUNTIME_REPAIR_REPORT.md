# CODEX Auth Runtime Repair Report

Verified on March 30, 2026.

## Root Cause

The auth timeout was not inside password verification, token signing, or DB commit.

The exact hang point was the first auth request entering `LazyModuleMiddleware.dispatch` and calling `ensure_modules_loaded(request.app)` before the auth router ran. On the March 29, 2026 proof run, the server log recorded:

- `app.modules.hydrate.slow duration_seconds=26.735`

That global lazy hydration step loaded the full non-core module set on the first `/auth/register` request, which exceeded the probe's `~20s` timeout. Because `/auth/login` immediately followed while the same hydration work was still in-flight or just finishing, it timed out for the same reason. That is why the original proof showed:

- `POST /auth/register` -> timeout at `20011ms`
- `POST /auth/login` -> timeout at `20007ms`
- no completed uvicorn access log entries for either request

The proof evidence is in:

- `Docs/CODEX_RUNTIME_PROOF_REPORT.md`
- `.codex_tmp/runtime_proof_server.log`

## Active Auth Path

### Before Fix

1. Request entered `backend/app/modules.py::LazyModuleMiddleware.dispatch`
2. Non-core path triggered `ensure_modules_loaded(request.app)`
3. Global lazy route hydration loaded the remaining app modules
4. Client timed out before `backend/app/auth/router.py::{register_user,login_user}` could complete

### After Fix

1. Request enters `LazyModuleMiddleware.dispatch`
2. `/auth/*` and `/api/auth/*` bypass lazy hydration and log request entry
3. `backend/app/auth/router.py::{register_user,login_user}` logs route entry
4. `AnalyticsService.track_event(...)`
5. `AuthService.register_user(...)` or `AuthService.authenticate_user(...)`
6. Password hash/verify timing is recorded
7. `AuthService.issue_access_token_with_session(...)` records access-context bind, session id creation, and token signing
8. DB commit or rollback timing is recorded
9. Response is built and `/api/auth/me` works with the issued bearer token

## Files Changed

- `backend/app/modules.py`
- `backend/app/auth/router.py`
- `backend/app/auth/service.py`
- `backend/tests/auth/test_auth_router.py`
- `backend/tests/app/test_auth_lazy_module_bypass.py`

## Fix Summary

- Eager-loaded the `auth` module instead of leaving it behind the first-request lazy hydration gate.
- Added an auth-only lazy-hydration bypass for `/auth/*` and `/api/auth/*`.
- Added request-entry logging at middleware level and route-entry logging inside the auth router.
- Expanded per-request auth telemetry to cover:
  - user lookup/create
  - password hash/verify
  - access-context bind
  - session id creation
  - access token creation
  - DB commit
  - DB rollback
  - response assembly

This is an auth-scoped repair. It does not redesign the auth flow or change unrelated route behavior.

## Before / After Timings

### Before

Source: March 29, 2026 proof report artifacts.

| Probe | Result |
|---|---|
| `POST /auth/register` | timeout at `20011ms` |
| `POST /auth/login` | timeout at `20007ms` |
| `/api/auth/me after login` | not reachable because login never completed |

### After

Source: March 30, 2026 patched runtime probe artifacts.

Primary probe artifact:

- `.codex_tmp/auth_runtime_probe_after.json`

Results:

| Probe | Status | Time |
|---|---:|---:|
| `POST /auth/register` | `201` | `1813.44ms` |
| `POST /auth/login` | `200` | `1873.83ms` |
| `GET /api/auth/me` after login | `200` | `156.13ms` |

Follow-up replay with step logs:

- `.codex_tmp/auth_runtime_probe_after_steps.log`

Replay timings:

| Probe | Status | Time |
|---|---:|---:|
| `POST /auth/register` | `201` | `2304.93ms` |
| `POST /auth/login` | `200` | `1284.35ms` |
| `GET /api/auth/me` after login | `200` | `82.57ms` |

## Probe Results

### `POST /auth/register`

- Returned `201 Created`
- Issued a bearer access token and session id
- Instrumentation log confirmed:
  - `auth.request.entry ... lazy_hydration_bypassed=true`
  - `auth.request.route_entry flow=register`
  - `auth.request.completed flow=register status_code=201`

Representative timed steps from the follow-up replay:

- `db.lookup_user_by_email_ms`: `3.81`
- `db.lookup_user_by_username_ms`: `10.58`
- `auth.hash_password_ms`: `890.72`
- `auth.bind_access_context_ms`: `7.99`
- `auth.create_session_id_ms`: `0.03`
- `auth.create_access_token_ms`: `0.23`
- `db.commit_ms`: `8.66`

### `POST /auth/login`

- Returned `200 OK`
- Issued a fresh bearer access token and session id
- Instrumentation log confirmed:
  - `auth.request.entry ... lazy_hydration_bypassed=true`
  - `auth.request.route_entry flow=login`
  - `auth.request.completed flow=login status_code=200`

Representative timed steps from the follow-up replay:

- `db.lookup_user_by_email_ms`: `3.96`
- `auth.verify_password_ms`: `1030.13`
- `auth.bind_access_context_ms`: `47.81`
- `auth.create_session_id_ms`: `0.05`
- `auth.create_access_token_ms`: `0.17`
- `db.commit_ms`: `11.34`

### `GET /api/auth/me` After Login

- Returned `200 OK`
- Loaded the authenticated profile using the bearer token from `/auth/login`
- Middleware log confirmed:
  - `auth.request.entry method=GET path=/api/auth/me modules_hydrated=False lazy_hydration_bypassed=true`

## Targeted Backend Tests

Executed on March 30, 2026:

```powershell
python -m pytest `
  backend/tests/auth/test_auth_router.py::test_register_login_and_me_flow `
  backend/tests/auth/test_auth_router.py::test_duplicate_registration_returns_conflict `
  backend/tests/auth/test_auth_router.py::test_login_with_invalid_credentials_returns_unauthorized `
  backend/tests/auth/test_auth_router.py::test_register_user_logs_completion `
  backend/tests/auth/test_auth_router.py::test_login_user_logs_completion `
  backend/tests/auth/test_auth_router.py::test_login_user_logs_failure_with_rollback `
  backend/tests/app/test_auth_lazy_module_bypass.py `
  backend/tests/auth/test_auth_service.py -q
```

Result:

- `15 passed in 54.11s`

What these tests cover:

- register success
- register duplicate failure
- login success
- login invalid-credentials failure
- completion logging
- rollback logging
- auth-path lazy-hydration bypass
- non-auth paths still hydrate normally

## Notes

- The March 30, 2026 rerun used a local sqlite runtime harness because the original external `DATABASE_URL` from the March 29, 2026 proof environment was not present in the current shell.
- The repaired behavior directly addresses the auth hang reported in the proof report: auth requests now bypass the global first-request module hydration path and complete successfully.
