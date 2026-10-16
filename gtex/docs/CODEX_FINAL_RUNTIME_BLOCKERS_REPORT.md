# CODEX Final Runtime Blockers Report

Date: 2026-03-30

Scope: fix only the four remaining runtime blockers, rerun proof for each item, and record exact evidence.

## 1. Home cold-block on first `/streamer-tournaments` call taking 106.6s

Status: `VERIFIED LIVE`

Root cause:
- `backend/app/modules.py` lazy hydration middleware did not bypass `/streamer-tournaments`.
- The first request to that route therefore triggered global lazy module hydration instead of loading only the streamer tournament surface.
- The streamer tournament module was also not in the eager set, so the first live hit paid the full cold-start cost.

Smallest safe fix:
- Added `"/streamer-tournaments"` to `LAZY_HYDRATION_BYPASS_PREFIXES` in `backend/app/modules.py`.
- Added `"streamer_tournament_engine"` to `EAGER_MODULE_NAMES` in `backend/app/modules.py`.

Runtime proof:
- Pre-fix probe timed out after `124070 ms` on the first `GET /streamer-tournaments`.
- Post-fix probe returned:

```json
{
  "first_status": 200,
  "first_ms": 92.51,
  "second_status": 200,
  "second_ms": 10.15,
  "modules_hydrated": false,
  "module_hydration_seconds": 0.0,
  "first_body_size": 18
}
```

Regression proof:
- `python -m pytest tests/app/test_module_registration.py -k streamer_tournaments_route_does_not_force_global_lazy_hydration -q`
- Result: `1 passed, 2 deselected, ... in 117.24s`

## 2. Tasks claim failing with `promo_pool_insufficient`

Status: `VERIFIED LIVE`

Root cause:
- `DailyChallengeService.claim()` called `RewardEngineService.settle_reward()` without passing the challenge reward ledger unit.
- `settle_reward()` defaulted to `LedgerUnit.COIN`.
- Daily challenges are configured with `reward_unit="credit"`, so claims incorrectly evaluated the coin promo pool and raised `promo_pool_insufficient` even when the credit promo pool had funds.

Smallest safe fix:
- `backend/app/reward_engine/service.py`
  - `settle_reward()` now accepts an explicit `ledger_unit`.
- `backend/app/daily_challenge_engine/service.py`
  - Mapped `challenge.reward_unit == "credit"` to `LedgerUnit.CREDIT` before settlement.

Runtime proof:
- Controlled runtime probe first reproduced the old failure path by intentionally settling against `coin`.
- The same seeded setup then claimed the daily challenge through the live HTTP route with a credit-funded promo pool.

```json
{
  "coin_probe": {
    "detail": "Promo pool balance is lower than the reward amount.",
    "reason": "promo_pool_insufficient"
  },
  "claim_status": 200,
  "claim_body": {
    "challenge_key": "daily-login",
    "reward_summary": "Claimed 25.0000 credit from daily-login."
  },
  "settlement_ledger_unit": "credit",
  "settlement_gross_amount": "25.0000"
}
```

Regression proof:
- `python -m pytest tests/admin_godmode/test_router_permissions.py tests/reward_engine/test_reward_engine_service.py -q`
- Result: `3 passed in 48.00s`

## 3. Clips returning `401 Missing identity context` after auth succeeds

Status: `VERIFIED LIVE`

Root cause:
- `frontend/lib/data/gte_authed_api.dart` only sent `X-User-Id`, `X-Session-Id`, and `X-Device-Id` when the stored `AuthSession` already contained user ID, session ID, and a non-empty device ID.
- When bearer auth succeeded but locally stored session metadata was incomplete or stale, clips/feed requests still went out without identity headers.
- The backend correctly rejected those requests in `require_identity` with `401 Missing identity context`.

Smallest safe fix:
- Kept the fix in the frontend transport layer only.
- `frontend/lib/data/gte_authed_api.dart`
  - decode JWT claims from the bearer token
  - recover `sub` as user ID and `sid` as session ID when `AuthSession` is incomplete
  - default `X-Device-Id` to `web-client`
  - send identity headers whenever resolved user ID and session ID are available

Runtime proof:
- Full app probe registered a user through `/auth/register`, then called `/feed/for-you` twice with the same bearer token.
- Authorization only still failed with the original backend error.
- Token-derived identity headers succeeded immediately.

```json
{
  "register_status": 201,
  "registered_user_id": "ff188fd7-6a69-4ba0-a6ca-cf13da61c414",
  "auth_response_session_id": "5cd6cfdb-94ea-4466-878e-bacc2786c688",
  "token_sub": "ff188fd7-6a69-4ba0-a6ca-cf13da61c414",
  "token_sid": "5cd6cfdb-94ea-4466-878e-bacc2786c688",
  "auth_only_status": 401,
  "auth_only_body": {
    "detail": "Missing identity context"
  },
  "derived_identity_status": 200,
  "derived_identity_feed_source": "for_you",
  "derived_identity_feed_key": "user:ff188fd7-6a69-4ba0-a6ca-cf13da61c414:feed",
  "derived_identity_items_count": 0
}
```

Frontend regression proof:
- `flutter test test/gte_authed_api_test.dart`
- Result:

```text
00:00 +0: authenticated requests include bearer and identity headers
00:00 +1: authenticated requests recover identity headers from token claims when the stored session is incomplete
00:00 +2: All tests passed!
```

## 4. Admin permission mismatches

### 4a. Super-admin catalog endpoints incorrectly `403`

Status: `VERIFIED LIVE`

Root cause:
- `AdminGodModeService.resolve_profile()` returned only default God Mode permissions for super-admin actors.
- The extra platform permissions required by the catalog/ingestion surfaces, including `manage_manager_catalog`, were not included in that resolved profile.
- `backend/app/auth/service.py` also had a duplicated super-admin fallback permission set that needed to stay aligned.

Smallest safe fix:
- Defined `SUPER_ADMIN_EXTRA_PERMISSIONS` in `backend/app/admin_godmode/service.py`.
- Merged those permissions into the super-admin branch of `resolve_profile()`.
- Reused the same constant in `backend/app/auth/service.py` for the auth fallback path.

Runtime proof:
- Super-admin probe hit a catalog-protected ingestion route with an invalid provider ID.
- The request passed permission enforcement and failed only on provider validation, which is the expected downstream behavior.

```json
{
  "status": 400,
  "body": {
    "detail": "\"Unknown ingestion provider 'not-a-real-provider'. Available: football_data, mock.\""
  }
}
```

Regression proof:
- `python -m pytest tests/admin_access/test_admin_access_role_scoping.py -q`
- Result: `3 passed in 50.37s`

### 4b. Scoped-admin God Mode incorrectly `500` instead of clean `403`

Status: `VERIFIED LIVE`

Root cause:
- `backend/app/admin_godmode/router.py` `read_bootstrap()` called `service.load_bootstrap()` without catching `PermissionDeniedError`.
- Scoped admins missing required God Mode permissions therefore surfaced as unhandled server errors instead of an authorization response.

Smallest safe fix:
- Added a `PermissionDeniedError` catch in `read_bootstrap()` and mapped it to HTTP `403`.

Runtime proof:
- Scoped-admin bootstrap probe returned a clean permission denial.

```json
{
  "status": 403,
  "body": {
    "detail": "Permission view_audit_log is required for this action."
  }
}
```

Regression proof:
- `python -m pytest tests/admin_godmode/test_router_permissions.py tests/reward_engine/test_reward_engine_service.py -q`
- Result: `3 passed in 48.00s`

## Files Changed

- `backend/app/modules.py`
- `backend/app/reward_engine/service.py`
- `backend/app/daily_challenge_engine/service.py`
- `backend/app/admin_godmode/service.py`
- `backend/app/admin_godmode/router.py`
- `backend/app/auth/service.py`
- `backend/tests/app/test_module_registration.py`
- `backend/tests/reward_engine/test_reward_engine_service.py`
- `backend/tests/admin_access/test_admin_access_role_scoping.py`
- `backend/tests/admin_godmode/test_router_permissions.py`
- `frontend/lib/data/gte_authed_api.dart`
- `frontend/test/gte_authed_api_test.dart`

## Final Outcome

All four remaining blockers are resolved at the smallest safe layer found during debugging, and every requested item reran with post-fix proof. Final state:

- Home cold-block: `VERIFIED LIVE`
- Tasks claim: `VERIFIED LIVE`
- Clips identity context: `VERIFIED LIVE`
- Super-admin catalog permissions: `VERIFIED LIVE`
- Scoped-admin God Mode permission handling: `VERIFIED LIVE`
