# GTEX Full App Verification Report

Date: 2026-03-29

## Scope

Verified the shipped Flutter runtime rooted at:

- `frontend/lib/main.dart`
- `frontend/lib/navigation/app_router.dart`

The sweep focused on route truthfulness, action persistence, auth/session/role drift, silent fallback, market and competition domain separation, match-viewer labeling, and admin/delegated-admin safety.

## Executive Summary

The active shell is materially more honest after this pass.

Highest-value repairs completed:

- Fixed session permission drift so hydrated `/api/auth/me` claims now survive `AuthSession.mergeProfile(...)`.
- Changed God Mode eligibility from “any admin” to “audit-permitted admin only”.
- Added an explicit blocked gate for guest access to `/clips` so the live feed is no longer mounted without a valid auth/identity context.
- Rewired GTEX competition joins on the active shell to the authenticated client path and added session/payload mismatch enforcement when auth is present.
- Permission-gated admin import, batch resume, share issuance, GTEX publish, and GTEX launch on both the frontend affordance layer and the backend mutation layer used by the active shell.

What is now clearly live in the shipped app:

- Home summary, profile summary, market segmentation, world read surfaces, daily challenges, GTEX/hosted/streamer competition discovery/detail, 2D viewer, Broadcast+, Flutter 3D/native-bridge 3D routing, streamer tournament engine route bridge, login/signup, and admin surfaces for sessions that actually hold the required permissions.

What remains intentionally blocked:

- Guest `/clips`
- World federation join from the summary tab
- Native 3D direct route

What remains intentionally demo:

- Match simulation

## Top Hidden Issues Found

1. `frontend/lib/shared/models/auth_session.dart`
   `mergeProfile(...)` overwrote hydrated permissions with stale session permissions, which made scoped-admin gating drift from backend truth.
2. `frontend/lib/shared/models/auth_session.dart`
   `canAccessGodMode` returned true for any authenticated admin, even when the backend bootstrap required `view_audit_log`.
3. `frontend/lib/navigation/app_router.dart`
   `/clips` mounted the live feed for guests and let backend auth failures surface as generic load errors instead of an honest blocked state.
4. `frontend/lib/features/profile/profile_admin_screen.dart`
   Import and share-issuance actions were visible to any admin role, regardless of delegated permission scope.
5. `backend/app/ingestion/router.py`
   Active-shell import/status/batch routes only checked `get_current_admin`, so scoped admins inherited catalog operations they did not actually have.
6. `backend/app/players/router.py`
   Share issuance used broad admin auth without `manage_manager_supply`, allowing delegated-admin escalation on a monetized surface.
7. `frontend/lib/features/competitions/live_competitions_hub_screen.dart`
   GTEX join used `CompetitionApi.joinCompetition(...)`, not the authenticated mutation path the shipped runtime uses elsewhere.
8. `frontend/lib/features/competitions/live_competitions_hub_screen.dart`
   GTEX publish/launch actions were enabled for any admin session instead of `manage_competitions`.
9. `backend/app/segments/competitions/segment_competitions.py`
   Authenticated competition joins could drift from the real session identity because the payload user id was trusted directly.
10. `frontend/test/transfer_market/transfer_market_screen_test.dart` and `frontend/test/active_shell_live_migration_smoke_test.dart`
    Verification coverage had drifted behind the active shell and was asserting old UI contracts instead of the current runtime, which masked the real route/action truth until updated.

## Biggest Remaining Risks

- GTEX competition publish/launch/join still accept legacy anonymous calls when no bearer token is supplied. The shipped Flutter shell no longer depends on that path, but the backend contract should still be tightened in a follow-up.
- Profile social follow/community mutations are not exposed on the active shell yet. The shipped profile route is now read-only/live rather than fake-persistent, but the capability itself remains incomplete.
- World federation membership creation is still intentionally blocked from the summary tab pending a real live action flow.

## Route And Action Evidence

- Route classifications: see `docs/CODEX_ROUTE_MATRIX.md`
- Mutation persistence and gating: see `docs/CODEX_ACTION_INTEGRITY_MATRIX.md`
- Fallback/mock/demo inventory: see `docs/CODEX_FALLBACK_AND_MOCK_AUDIT.md`

## Tests Run

Frontend:

```bash
flutter test test/active_session_provider_test.dart test/active_shell_route_mount_test.dart test/profile_admin_visibility_test.dart test/active_shell_live_migration_smoke_test.dart test/transfer_market/transfer_market_screen_test.dart test/tasks/tasks_provider_test.dart test/match_3d_route_truth_test.dart
```

Result: passed, 18 tests.

Backend:

```bash
python -m pytest tests/admin_access/test_admin_access_role_scoping.py tests/admin_access/test_active_shell_permission_guards.py tests/competitions/test_active_shell_competition_auth_guards.py
```

Result: passed, 10 tests.

Additional commands executed during verification:

```bash
python -m py_compile backend/app/players/router.py backend/app/ingestion/router.py backend/app/segments/competitions/segment_competitions.py
```

Result: passed.

## Honest Final State

Within the shipped Flutter runtime, the app is now honest in the areas repaired here:

- guest-only and permission-only blocks are explicit instead of implicit
- core admin actions no longer over-promise capabilities that the session cannot complete
- GTEX competitions, hosted competitions, and streamer tournaments remain separate families
- market surfaces no longer blur player shares, transfer listings, and wallet/compliance into one fake desk
- native 3D is not claimed when only Flutter 3D is available

The active app can now be described as honest with one important caveat: a legacy anonymous GTEX competition mutation path remains on the backend for non-active clients and should be retired in a follow-up hardening pass.
