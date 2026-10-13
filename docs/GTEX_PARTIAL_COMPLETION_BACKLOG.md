# GTEX Partial-Surface Completion Backlog

Ordered completion plan for product areas that are live but not finished.
Trading (System A) and Coin Trader UX are treated as complete and are out of scope here.

## Rules
- Prefer wiring existing backend contracts over inventing new APIs
- Fail closed when live endpoints are missing (empty / unavailable), never ship demo queues in production
- Keep fixture/demo paths behind `allowFixtureData` only
- Ship each item as a reviewable slice with tests

## Priority order

### 1. Regen — Admin Create-a-Son queue — DONE
Wired live `listCreationOrders` / pay / generate; demo queue only via fixture repository.

### 2. AI Newsroom — Admin publish path — DONE (schedule/reject still locked)
Live story-feed queue + `POST /api/admin/story-feed` publish; mounted in Admin Command Center newsroom module. Schedule/reject stay disabled until moderation endpoints exist.

### 3. Advertising — Match overlay mount — DONE
`GtexFlashSplitAdOverlay` mounts in `GtexMatchViewerScreen` from live flash/split/pre-roll placements; premium ad-free skips overlay.

### 4. Manager — Personal manager office surface — DONE
`PersonalManagerApi` + office panel on Coach Exchange: me / create / appoint to operated club.

## Explicitly deferred (not half-done product claims)
- Match “Coming soon” 3D / spectate / broadcast routes (launch policy: 2D tactical / OriginalVisualRuntime path)
- Unity runner / Vercel infra failures
