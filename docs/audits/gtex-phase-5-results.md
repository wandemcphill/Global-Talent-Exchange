# GTEX P7-FE Slice 1 — Match Viewer P0 Results

**Status:** IMPLEMENTED and targeted-test verified

## Root cause

`/match-viewer/:matchKey` renders `MatchViewerRouteScreen`, which waits for
`liveMatchViewerQualifiedRouteProvider`. The provider calls
`ApiLiveMatchViewerRepository.resolveBootstrap`, which fetches
`/api/v2/match-viewer/:matchKey` and
`/api/v2/match-viewer/:matchKey/session`. Neither the route provider nor all
possible repository/transport implementations enforced a completion deadline.
Consequently, a future that never settled kept the route in the technical
`Verifying shipped capability` loading screen. Riverpod's default retry policy
could also retry a failed bootstrap automatically, returning the user to loading
without an explicit recovery action.

## Verified backend state model

`backend/app/routes/match_viewer.py` resolves authoritative viewer data in this
order: stored `CompetitionMatch.metadata_json.match_viewer`, replay-archive
record (`replay:<match_key>`), `FastMatchSession.viewer_payload_json`, then live
match hub state. The route returns 404 only when none exists. Existing fairness
and authorization behavior remains unchanged.

| Backend result | P7-FE presentation |
| --- | --- |
| Authoritative live/stored timeline or replay archive | Mount the existing 2D Match Viewer. |
| 404: no live session or replay | “No match available” with Match Center navigation. |
| Invalid/incomplete verified session | “Match data unavailable”; no partial or invented timeline. |
| Unauthorized | “Match access restricted” with Match Center navigation. |
| Network/service failure or 12-second bootstrap timeout | “Match viewer unavailable” with explicit “Try again”. |

## Implementation

- Added a 12-second route-level bootstrap timeout, including for custom
  repositories that do not implement transport timeouts.
- Disabled automatic retry only for this route provider; retry is deliberately
  user-driven through the visible recovery action.
- Replaced technical gate copy with product language and removed the indefinite
  route loader.
- Preserved the existing fixture-only demo fallback. Live mode never mounts it.
- Did not change the backend, Unity P6/P6V, or ingestion work.

## Verification

- `flutter test test/match/match_viewer_route_fallback_gate_test.dart test/match_live_match_viewer_route_support_transport_test.dart` — passed.
- Targeted backend match-viewer regression suite was run against the existing
  stored-timeline and replay-archive contract.
- No Playwright/browser runner or installed browser executable is present in
  this checkout, so browser screenshots and browser-driven validation remain
  **PARTIAL** and must be completed in P7-FEV. The widget tests cover the
  desktop-sized error surface and the timeout/retry transition.

## Remaining limitation

The 2D viewer can open a replay only where the backend has already materialized
an authoritative match-viewer timeline or replay-archive record. There is no
new replay-discovery endpoint in this slice, and no replay content was
fabricated.

---

# GTEX P7-FE Slice 2 — Mobile Lineup, Notification Navigation, and Browser Harness

**Status:** IMPLEMENTED; Flutter and Chromium runner verified. Authenticated
browser route verification remains environment-dependent.

## P1-01 — mobile lineup/substitute access

**Resolved in the active `/lineup` route.** The historical audit referenced an
older tactical-pitch/drag layout. Current main mounts `GtexLineupEditorScreen`,
which saves up to seven bench player IDs but rendered no substitute bench at
all. On a narrow screen, that made substitutes inaccessible from the active
editor rather than merely clipped.

The editor now has a reusable `GtexLineupSubstitutes` surface. It uses a
two-column, touch-safe grid below the starter list on mobile/tablet and a
side-by-side starter/bench composition at 900px and above. All substitutes are
present in the scrollable page, and a player can be selected then assigned by
tapping a starter position. This preserves the existing tap-to-assign editing
model; no coordinate-based drag behaviour exists in the active route to remove
or emulate.

## P1-02 — notification navigation

**Resolved for authoritative targets.** `NotificationEventMatrixService`
already writes canonical `metadata.deep_link_route` values into notification
records. The frontend had a second, broad keyword-routing layer and eventually
opened the wallet when it had no target. That could mark a notification read
while navigating to an unrelated fabricated surface.

`GtexNotificationNavigation` is now the single resolver. It accepts a local,
validated canonical route from backend metadata, or the exact legacy
`fixture_id` → `/matches/viewer/:fixtureId` convention. It does not infer a
route from copy, topic, resource labels, or generic IDs. The Open action is
disabled when no safe target exists; users can still explicitly mark that
notification read. Existing feature-gate and permission checks run before
navigation.

## Browser-validation harness

- Location: `qa/playwright/`
- Runner: Playwright with Chromium, Flutter Web web-server integration, mobile
  (`390x844`/Pixel 5), tablet (`768x1024`), and desktop (`1440x900`) projects.
- Evidence: Chromium was installed and the runner health test passed in all
  three projects. Console errors and failed requests are attached to configured
  browser tests; screenshots are written as Playwright result artifacts.
- Command: `cd qa/playwright; npm test`
- Local authenticated run: set `GTEX_E2E_API_BASE_URL`,
  `GTEX_E2E_EMAIL`, and `GTEX_E2E_PASSWORD` as documented in
  `qa/playwright/README.md`. Optional notification variables select existing,
  real seeded alerts for target and no-target checks.

## Verification

- `flutter test test/engagement_redesign/notifications_screen_v2_test.dart test/club/gtex_lineup_substitutes_test.dart` — passed (5 tests).
- `python -m pytest backend/tests/notifications/test_notification_event_matrix_service.py` — passed (3 tests).
- `flutter build web --dart-define=GTE_API_BASE_URL=http://127.0.0.1:8000 --dart-define=GTE_BACKEND_MODE=live` — passed.
- `npx playwright test` — Chromium health passed for mobile, tablet, and desktop;
  route checks skipped honestly because this checkout had no running local API
  or approved authenticated account supplied to the environment.

## Remaining browser limitation

No authenticated browser screenshots were captured in this execution: no local
GTEX API was listening on `127.0.0.1:8000`, and no approved credentials were
provided. The harness does not substitute fixture or fabricated app data for
those screenshots. P7-FEV can move from **BLOCKED** to **READY for
authenticated browser verification**, but is not complete until the configured
route checks and visual review run against a real seeded environment.

Unity P6/P6V and unrelated ingestion work were untouched.

---

# GTEX P7-FE Slice 3 — Design Lab and Command Center

**Status:** IMPLEMENTED; isolated Design Lab and production Home foundation
verified through focused Flutter tests. Authenticated Home browser review
remains environment-dependent.

## Design directions explored

1. **Matchday Pulse** — event-first: the immediate fixture, readiness, and
competition pressure lead.
2. **Club Atlas** — identity-first: club crest, legacy, academy, and prestige
lead.
3. **Ownership Ledger** — market-first: owned positions, value movement, bids,
and rank lead.

The selected production direction combines the hierarchy of Matchday Pulse
with the identity clarity of Club Atlas and selected ownership metrics. This
keeps GTEX football-first while preserving real market and collection signals.

## Implementation

- Added the isolated, unlinked Flutter route `/design-lab`, backed only by
  clearly labelled local fixture data in `frontend/lib/design_lab/`.
- Added `GtexCommandTokens`, `GtexCommandCenterMasthead`,
  `GtexCommandAction`, and `GtexCommandFocusTile` as exported `ui_gtex`
  primitives.
- Rebuilt the live Home masthead around the shared Command Center primitive.
  Its identity, wallet, player-market count, competition count, and task rhythm
  still come from the existing live profile, market, competition, and task
  providers. It does not fabricate a current fixture, club, reward, or market
  position.
- Added Playwright Design Lab coverage that captures all three directions at
  mobile, tablet, and desktop when the isolated fixture run is configured.

## Verification

- `flutter test test/design_lab/gtex_design_lab_screen_test.dart` — passed (3
  tests), including desktop exploration, 390px mobile readability, and
  requested-direction opening.
- `flutter build web --release --dart-define=GTE_API_BASE_URL=http://127.0.0.1:8000
  --dart-define=GTE_BACKEND_MODE=live` — passed.
- `npx playwright test --grep "design lab"` — passed in mobile, tablet, and
  desktop projects against the built release bundle. It captured each of the
  three directions at all three breakpoints (nine screenshots). The route uses
  no backend fixture injection; its visual fixture data is isolated in the
  Design Lab only.

## Remaining limitation

The Design Lab can be browser-validated without account data, but the live Home
continues to require an approved authenticated account and running GTEX API for
browser screenshots. P7-FEV remains **READY for authenticated browser
verification**, not complete. Unity P6/P6V and unrelated ingestion work were
untouched.
