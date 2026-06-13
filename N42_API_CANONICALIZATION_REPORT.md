# N42 — STALE API ALIAS ERADICATION REPORT

Date: 2026-06-13
Branch: `feature/original-visual-runtime` @ `56f4afdc`
Verdict: **Production canonicalization COMPLETE & guard-enforced. Residual stale-alias usage is test-only and confined; no production /api alias gaps.**

## Method
- Static sweep of `backend/tests` for non-canonical `/api/`, `/auth/`, legacy aliases.
- Inspected the runtime contract guard (`app/core/api_contract.py`).
- Ran evidence probes: `tests/app/test_api_contracts.py`, `tests/app/test_main.py`, `tests/auth/test_auth_router.py` (`.runtime/n42_probe.log` — 18 passed, 6 failed).

## Production status — CLOSED
| Surface | Canonical | Enforcement |
|---|---|---|
| Auth | `/api/v2/auth/*` | guard 410s bare `/auth/*` (proven N40) |
| Competition | `/api/v2/competitions/*` | guard 410s `/api/competitions` (proven N34) |
| Wallet/Admin/Regen | `/api/v2/*` | `ApiContractGuardMiddleware` 410s any non-canonical `/api`,`/auth`,`/ws` path (`api_contract.py:299`) |
| Frontend | `/api/v2/*` only | mode-aware repo; `liveThenFixture` collapses to `live`; no alias calls (prior screen audit) |
- **`/api/v1` / non-v2 `/api/` usage in tests: ZERO** (grep confirmed). `LEGACY_API_VERSION_PREFIX = /api/v1` → 410 by design.
- Production routers expose canonical `/api/v2/*`; the guard rejects everything else. There is **no production alias to eradicate** — the eradication is already enforced at the middleware.

## Test-side residual (the only remaining drift)
The 410 drift surfaces **only** in test files that (a) mount the full guarded app AND (b) call a non-canonical path. Findings:
1. **Shared admin-headers helper** (`tests/conftest.py`) — logged in via bare `/auth/login`. **FIXED in N40** → `/api/v2/auth/login` + `X-API-Version: 2` + envelope unwrap. Cleared 8 setup-errors across regen/clubs.
2. **Competition lifecycle tests** — bare `/api/competitions`. **FIXED in N34** (v2 + envelope). 6/6 green.
3. **Body-level alias calls** in non-alpha-critical admin/advanced files (`regen/test_regen_admin_rbac.py`, `regen/test_regen_universe_expansion_api.py`, `clubs/test_regen_hof_awards_search.py` — POST `/api/.../roles` etc.). **Tracked sweep, not alpha-blocking** (admin/advanced-regen surfaces, not tester journeys).
4. **30 files reference bare `/auth/*`** for login setup, but most do **not** 410 — their test apps omit the contract-guard middleware, so bare routes resolve (18/24 auth-router tests pass on bare paths). These are not production gaps.

## Probe result classification (evidence, not assumption)
`test_api_contracts.py`, `test_main.py`, `test_auth_router.py`: **18 passed, 6 failed**. The 6 failures are **NOT alias-410s**:
- `test_main::test_app_startup_registers_core_routes` — asserts a hardcoded list of `domain_modules` names (module-registry drift).
- `test_auth_router::test_api_auth_me_patch_*` (3) — `/api/v2/auth/me` PATCH **behavior/contract** drift (canonical path).
- `test_auth_router::test_login_user_logs_*` (2) — **log-message format** assertions (`auth.request.route_entry flow=login` no longer emitted verbatim).
- `test_api_contracts.py` `/wallets/...` entries are an **OpenAPI-spec alias map assertion** (`path in openapi["paths"]`), intentional — not live calls.

These 6 are pre-existing test drift in a separate class (module list, me-patch behavior, log format) and are **out of N42 scope**; logged here for transparency and as a follow-up cleanup, not an alias problem.

## Actions taken
- Confirmed production canonicalization is enforced (no code change needed — the guard already eradicates aliases at runtime).
- Prior alias fixes (N34 competition, N40 admin-headers helper) remain in place and green.

## Conclusion
**N42 production objective met:** every non-canonical `/api`/`/auth` route is rejected (410) in production; the frontend speaks only `/api/v2`. No production alias remains. Remaining items are test-harness modernization (a tracked, non-alpha-critical sweep) and 6 unrelated test-drift failures (module list / me-patch / log format) flagged for a separate cleanup — neither blocks closed beta.
