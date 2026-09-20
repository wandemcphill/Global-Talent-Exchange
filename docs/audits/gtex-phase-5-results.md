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
