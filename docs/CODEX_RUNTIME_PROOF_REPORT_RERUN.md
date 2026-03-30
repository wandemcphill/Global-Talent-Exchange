# CODEX Runtime Proof Report Rerun

Verified on March 30, 2026 against the repaired shipped runtime at `http://127.0.0.1:8000` using the current shipped `gte_backend.db` and the active `backend.app.asgi:app` boot path. Proof-only admin role state was isolated with a copied config directory; the app code and shipped database under test were the live workspace runtime.

Note: items 12 and 21 in this file are the earlier `2026-03-30T08:04:07Z` pre-fix snapshot from `.codex_tmp/runtime_proof_rerun_results.json`. Their final reconciled state is recorded in [Docs/CODEX_RUNTIME_CONFLICT_PROOF_PASS.md](C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\Docs\CODEX_RUNTIME_CONFLICT_PROOF_PASS.md).

Primary evidence:

- Boot: `/health` `200`, `/ready` `200` with `database=ok` and `schema=ok`, `/version` `200`, `/diagnostics` `200`
- Raw probe artifact: `.codex_tmp/runtime_proof_rerun_results.json`
- Match route truth checks:
  - `flutter test test/match_3d_route_truth_test.dart` passed
  - `flutter test test/navigation_surface_truth_test.dart` passed

## Status

1. Login/signup: VERIFIED LIVE
2. Home: VERIFIED LIVE
3. World: VERIFIED LIVE
4. GTEX-hosted competitions: VERIFIED LIVE
5. Hosted competitions: VERIFIED LIVE
6. Streamer/e-game tournaments: VERIFIED LIVE
7. Player shares market: VERIFIED LIVE
8. Transfer listings market: VERIFIED LIVE
9. Real-player discovery: VERIFIED LIVE
10. Tradable real-player visibility: VERIFIED LIVE
11. Wallet/compliance: VERIFIED LIVE
12. Tasks list and claim persistence: VERIFIED BLOCKED
13. Clips: VERIFIED LIVE
14. Matches overview: VERIFIED LIVE
15. 2D viewer: VERIFIED LIVE
16. Pseudo-3D/broadcast viewer: VERIFIED LIVE
17. Flutter 3D viewer: VERIFIED LIVE
18. Native 3D blocked truth: VERIFIED BLOCKED
19. Profile admin visibility: VERIFIED LIVE
20. God Mode visibility/access: VERIFIED LIVE
21. Delegated admin limited-permission behavior in practice: VERIFIED BLOCKED
22. Federations hub/detail: NOT VERIFIABLE IN CURRENT ENVIRONMENT
23. National teams hub/detail: NOT VERIFIABLE IN CURRENT ENVIRONMENT
24. Transfer center hub/detail: NOT VERIFIABLE IN CURRENT ENVIRONMENT

## What Improved Since The Last Runtime Proof

- Auth is now live on the shipped runtime: `POST /auth/register` returned `201`, `POST /auth/login` returned `200`, and `GET /api/auth/me` returned `200`.
- Home and world are no longer blocked by auth/schema failures. `GET /api/competitions`, `GET /hosted-competitions`, `GET /streamer-tournaments`, `GET /regen-universe/tracking`, and the other world feeds all returned `200`.
- Streamer season and leaderboard paths are now live. `GET /leaderboard/global`, `GET /season/current`, and `GET /season/history` all returned `200`.
- Player-share and wallet/compliance repairs are live. `GET /players/{player_id}/shares/market`, `GET /players/{player_id}/shares/events`, `GET /api/wallets/summary`, `GET /api/wallets/overview`, and `GET /policies/me/compliance` all returned `200`.
- Clips are now live when the real auth identity headers are supplied, matching the shipped frontend client behavior. `/feed/for-you` and `/feed/following` both returned `200`.
- Matches overview now exposes a real current match from `/api/broadcast/home`, and the match-viewer contract resolved for `match_fix_63c641d28f27` with both `/api/match-viewer/{matchKey}` and `/api/match-viewer/{matchKey}/session` returning `200`.
- Admin and God Mode are now runtime-verifiable. The bootstrap super-admin login returned `200` and `/api/admin/god-mode/bootstrap` returned `200`.

## Still Failing

- Tasks claim persistence is still failing. `POST /daily-challenges/daily-login/claim` returned `500`, and the follow-up `/daily-challenges/me` payload still showed no claim persisted.
- Delegated admin behavior is still broken in practice. A scoped admin was created and could reach catalog status routes with `200`, but `/api/admin/god-mode/bootstrap` still returned `500`, and the login response still carried an incorrect empty permission list plus a bad `/admin/god-mode` landing route.
- Super-admin catalog/import endpoints still mismatch the visible session. The super-admin login payload advertised catalog permissions, but `/internal/ingestion/providers/football_data/health` and `/internal/ingestion/real-players/status` both returned `403`.
- Federations, national teams, and transfer center hub list routes are live but empty, so their detail routes could not be opened from live runtime data.

## Current Blocker Type

- 12. Tasks list and claim persistence: data
- 18. Native 3D blocked truth: code
- 21. Delegated admin limited-permission behavior in practice: code
- 22. Federations hub/detail: data
- 23. National teams hub/detail: data
- 24. Transfer center hub/detail: data

## Fresh Evidence Highlights

- Real-player discovery returned `total: 150`; sampled player `Harry Kane` had an active share market and issue event.
- Wallet/compliance returned live policy state for the newly registered user.
- Clips returned `200` with a user-scoped feed payload instead of the previous `Missing identity context` failure.
- `/api/broadcast/home` returned a live trending channel match, and the viewer/session endpoints for `match_fix_63c641d28f27` both returned `200`.
- Federations, national-team competitions, and transfer listings each returned `200` with empty arrays, which is why the hub/detail combined items remain not verifiable instead of blocked.
