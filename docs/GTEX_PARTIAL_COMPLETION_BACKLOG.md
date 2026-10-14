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

### 2. AI Newsroom — Admin publish + schedule/reject — DONE
Live story-feed queue + `POST /api/admin/story-feed` publish; `GET /api/admin/story-feed` desk list; `POST .../schedule` and `POST .../reject` moderation; Admin Newsroom Schedule/Reject controls wired.

### 3. Advertising — Match overlay mount — DONE
`GtexFlashSplitAdOverlay` mounts in `GtexMatchViewerScreen` from live flash/split/pre-roll placements; premium ad-free skips overlay.

### 4. Manager — Personal manager office surface — DONE
`PersonalManagerApi` + office panel on Coach Exchange: me / create / appoint to operated club.

### 5. Admin Jackpot — Live runtime controls — DONE
`JackpotAdminApi` + `GtexJackpotAdminPanel` wired to runtime / balance / trigger / history; stub Create pool / Winner review CTAs replaced with real controls.

### 6. Admin Trust Ops — Live KYC queue + review — DONE
`GtexTrustOpsApiRepository` loads `GET /api/admin/treasury/kyc` into the KYC queue (operations-readiness stays the health rail); Approve/Reject call `POST .../kyc/{id}/review` with `verified` / `rejected`.

### 7. Admin Trust Ops — Live disputes queue + reply — DONE
Loads `GET /api/admin/treasury/disputes` into the disputes rail; Reply posts `POST .../disputes/{id}/messages` (admin reply → awaiting user). No resolve endpoint exists yet — orders / withdrawals remain deferred.

## Explicitly deferred (not half-done product claims)
- Match “Coming soon” 3D / spectate / broadcast routes (launch policy: 2D tactical / OriginalVisualRuntime path)
- Unity runner / Vercel infra failures
