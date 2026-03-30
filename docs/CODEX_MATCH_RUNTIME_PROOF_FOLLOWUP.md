# CODEX Match Runtime Proof Follow-Up

Verified on March 30, 2026 against the local test/runtime surfaces in this repository.

## Goal

Follow up on the March 29, 2026 blocker in [`Docs/CODEX_RUNTIME_PROOF_REPORT.md`](C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\Docs\CODEX_RUNTIME_PROOF_REPORT.md):

- `/api/broadcast/home` needed repaired auth
- no verified current `matchKey` was available
- no fallback `competition_matches.metadata_json.match_viewer` rows existed
- native 3D had to remain blocked until real platform handlers exist

## What Changed

- `backend/app/routes/match_viewer.py` no longer depends only on persisted `metadata_json.match_viewer` or replay-archive rows.
- `backend/app/services/match_timeline_service.py` now synthesizes a valid `MatchViewStateView` from:
  - active `LiveMatchHub` streams
  - `InfiniteLeagueRuntime.live_stream(...)` payloads
- That means a current match published by broadcast discovery can now resolve:
  - `GET /api/match-viewer/{matchKey}`
  - `GET /api/match-viewer/{matchKey}/session`
- Native 3D behavior was not relaxed. The shipped native route remains a disclosed blocked surface.

## Local Proof

Backend proof:

- `python -m pytest backend/tests/test_match_viewer_route.py -q`
  - Result: `5 passed`
  - Includes live-hub fallback proof with no stored `match_viewer` metadata row.
- `python -m pytest backend/tests/broadcast_network/test_router.py::test_authenticated_broadcast_home_current_match_resolves_match_viewer_endpoints -q -s`
  - Result: `1 passed`
  - Proves the path:
    - real auth login in the test runtime
    - `GET /api/broadcast/home`
    - extract current `match_id`
    - `GET /api/match-viewer/{matchKey}`
    - `GET /api/match-viewer/{matchKey}/session`

Frontend proof:

- `flutter test test/match_3d_route_truth_test.dart`
  - Result: passed
  - Confirms Flutter 3D route uses Flutter fallback when no native bridge is mounted.
- `flutter test test/navigation_surface_truth_test.dart`
  - Result: passed
  - Confirms `/matches/native-3d` remains labeled and disclosed as coming soon / blocked.

## Real Runtime Verification Steps

After auth is repaired in the real shipped runtime, use a real user and verify this exact sequence:

1. Authenticate with the repaired runtime.
2. Call `GET /api/broadcast/home` with the real bearer token.
3. Read one current match key from:
   - `match_of_the_moment.match_id`, or
   - `featured_channel.current_program.match_id`, or
   - `channels[*].current_program.match_id`
4. Verify:
   - `GET /api/match-viewer/{matchKey}` returns `200`
   - `GET /api/match-viewer/{matchKey}/session` returns `200`
5. Open frontend routes with that same `matchKey`:
   - `/matches/viewer/{matchKey}` for 2D viewer
   - `/matches/broadcast/{matchKey}` for pseudo-3D / broadcast viewer
   - `/matches/3d/{matchKey}` for Flutter 3D viewer
6. Confirm `/matches/native-3d` is still blocked unless real platform handlers for `match_3d` and `match_3d/events` are actually mounted.

## Current Status By Requested Item

- `1. After auth is repaired, verify /api/broadcast/home for a real user`
  - Ready to execute.
  - Not completed in this follow-up because the external shipped runtime/auth environment used in the March 29, 2026 report is not configured in this workspace.
- `2. Ensure at least one current match produces /api/match-viewer/{matchKey} and /session`
  - Completed locally.
  - Current broadcast-discovery matches can now fall back to live-hub or infinite-league viewer synthesis.
- `3. Confirm runtime proof for 2D viewer / pseudo-3D viewer / Flutter 3D viewer`
  - Backend proof path is complete locally.
  - Frontend truth tests are green for Flutter 3D fallback and native-blocked disclosure.
  - Real shipped-runtime click-through with a real authenticated user is still pending step 1 above.
- `4. Keep native 3D blocked unless real platform handlers exist`
  - Still true.
  - No native 3D enablement was added in this change.

## Evidence and Notes

- Local auth-only repair evidence already exists in:
  - `.codex_tmp/auth_runtime_probe_after.json`
  - `.codex_tmp/auth_runtime_probe_after_steps.log`
- That artifact proves local register/login/me behavior on March 30, 2026, but it is not the same as re-running the March 29, 2026 external runtime proof.

## Residual Risk

- A broader existing broadcast-network test still fails outside this proof path:
  - `backend/tests/broadcast_network/test_router.py::test_broadcast_network_join_and_stream_channel`
  - Observed failure: the live channel can return a cached fallback slot with `current_program.match_id == null`
- That issue is separate from the match-viewer runtime-proof path added here, but it is worth fixing before relying on the live-channel join flow as proof evidence.
