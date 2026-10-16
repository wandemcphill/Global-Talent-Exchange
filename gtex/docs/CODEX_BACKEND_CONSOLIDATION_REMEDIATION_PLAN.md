# CODEX Backend Consolidation Remediation Plan

## Purpose

This plan turns the backend runtime audit into executable work:

- fix real frontend/backend contract drift
- choose a canonical public API policy
- isolate expansion domains from the required product backend
- stop local reduced-profile runs from being mistaken for full-platform health

Companion audit:

- [Docs/CODEX_BACKEND_RUNTIME_AUDIT_REPORT.md](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/Docs/CODEX_BACKEND_RUNTIME_AUDIT_REPORT.md>)

Raw runtime diff:

- [.codex_tmp/backend_route_audit_runtime.json](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/.codex_tmp/backend_route_audit_runtime.json>)

## Target End State

The backend should behave as a clearly defined platform with:

- one canonical public namespace for product APIs
- explicit compatibility aliases, not accidental duplicates
- a documented required product backend set
- a documented expansion/admin-only backend set
- a local runner profile that is clearly labeled as reduced or full
- route-contract tests that fail when frontend-visible endpoints drift

## Canonical API Policy

### Public API policy

Use this as the canonical policy going forward:

- canonical product API: `/api/...`
- compatibility alias: `/api/v1/...`
- direct non-`/api` routes allowed only when they are intentionally not part of the product API surface

### Deprecation policy

- do not add new direct routes when an `/api/...` route already exists
- keep `/api/v1/...` as compatibility until frontend and external clients are fully normalized
- mark direct legacy route families as deprecated in docs once frontend is no longer using them

### Frontend policy

- all frontend network-layer calls should target `/api/...` unless the route is explicitly documented otherwise
- app navigation paths must not be mixed into API support checks
- support/probe code must only test mounted API contracts, not internal or imagined collection roots

## Immediate Fixes

These were the highest-value, lowest-risk fixes. The notification and namespace drift fixes below are now complete in the current checkout:

- `notifications` and `notifications_admin` are mounted as API-only routes in `backend/app/modules.py`
- shipped frontend notification calls now use canonical `/api/notifications/...`
- `community_engine` is mounted as API-only, with shipped frontend callers on `/api/community/...`
- shipped creator clip-earnings calls now use `/api/media-engine/...` first and only fall back to bare `/media-engine/...` on a real `404`

### Fix 1: Freeze creator/media ownership split before deeper consolidation

Problem:

- the creator product is already split across three backend owners
- `/api/creators/...` is not the same contract family as `/api/creator/...`
- `media_engine` mixes authenticated API routes with intentionally public `/media-engine/downloads/...` URLs
- collapsing these into one namespace blindly will either break frontend routes or break public asset links

Owning files:

- [backend/app/segments/creators/segment_creators.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/backend/app/segments/creators/segment_creators.py:41>)
- [backend/app/creator/router.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/backend/app/creator/router.py:104>)
- [backend/app/media_engine/router.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/backend/app/media_engine/router.py:71>)
- [frontend/lib/data/creator_api.dart](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/frontend/lib/data/creator_api.dart:135>)
- [frontend/lib/data/creator_application_api.dart](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/frontend/lib/data/creator_application_api.dart:66>)
- [frontend/lib/features/creator_share_market/data/creator_share_market_repository.dart](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/frontend/lib/features/creator_share_market/data/creator_share_market_repository.dart:54>)
- [frontend/lib/features/creator_stadium_monetization/data/creator_stadium_monetization_repository.dart](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/frontend/lib/features/creator_stadium_monetization/data/creator_stadium_monetization_repository.dart:102>)

Implementation:

1. Treat these as separate contracts until an explicit merge plan exists:
   - `/api/creators/...` for creator identity, profile, finance, and copilot
   - `/api/creator/...` and `/api/admin/creator/...` for onboarding, verification, and share-market operations
   - `/api/media-engine/...` and `/api/admin/media-engine/...` for creator monetization and creator-league admin APIs
   - `/media-engine/downloads/...` and `/community/creator/...` as public non-API surfaces
2. Keep route-contract tests that assert all four surfaces mount and remain distinct.
3. Do **not** mark `media_engine` as `api_only` while download/share URLs still intentionally resolve under bare `/media-engine/...`.

Acceptance criteria:

- creator frontend repositories target the correct owner namespace instead of depending on accidental aliases
- public media download URLs remain stable
- route-contract tests fail if `/api/creators`, `/api/creator`, or `/api/v1/media-engine` drift

#### Current creator/media ownership matrix

| Product slice | Current backend owner | Current public contract | Current shipped/frontend callers | Stabilization rule |
|---|---|---|---|---|
| Creator identity and profile | `backend/app/segments/creators/segment_creators.py` | `/api/creators/...` plus the specific legacy aliases `/creators/me/insights` and `/creators/me/copilot/analyze` | `frontend/lib/data/creator_api.dart` | Keep `/api/creators/...` as the canonical creator identity/profile namespace. Do not assume generic bare `/creators/...` parity. |
| Creator onboarding and share-market ops | `backend/app/creator/router.py` | `/api/creator/...`, `/api/admin/creator/...` | `frontend/lib/data/creator_application_api.dart`, `frontend/lib/features/creator_share_market/data/creator_share_market_repository.dart` | Treat as a separate creator-ops family. Do not silently merge into `/api/creators/...`. |
| Creator monetization and creator league admin | `backend/app/media_engine/router.py` | `/api/media-engine/...`, `/api/admin/media-engine/...` through the API contract layer | `frontend/lib/data/creator_api.dart`, `frontend/lib/features/creator_stadium_monetization/data/creator_stadium_monetization_repository.dart` | Keep API routes explicit and versioned. Do not collapse into `api_only` while public media URLs still depend on bare mounts. |
| Public creator web profile | creator profile web surface | `/community/creator/{handle}` | generated by `frontend/lib/data/creator_api.dart` | Keep outside the authenticated API contract. This is a web/public surface, not an API family. |
| Public media downloads and share exports | media/public asset surface | `/media-engine/downloads/{token}` and related bare media URLs | generated from media/highlight flows and backend responses | Keep outside API-only routing until a separate public-asset router exists. |

#### Long-term options

Option A: formalize the split and stop trying to flatten it

- Keep `/api/creators`, `/api/creator`, and `/api/media-engine` as distinct product families.
- Document each family as permanent and add ownership labels in backend module/docs.
- Prefer this if the business domains really are separate teams/workflows.

Option B: rename into clearer product-facing families with compatibility aliases

- Example target families:
  - `creator-profile` for today’s `/api/creators/...`
  - `creator-ops` for today’s `/api/creator/...`
  - `creator-monetization` for today’s `/api/media-engine/...`
- Add explicit compatibility aliases from the old families.
- Migrate frontend callers one family at a time.
- Only remove old families after route-contract tests and public links are stable.

Recommended decision:

- take Option A unless there is a real product need to rename the surface for external consumers or team ownership.
- If Option B is chosen, do not rename the public `/community/creator/...` or `/media-engine/downloads/...` links in the same phase as the authenticated API migration.

### Fix 2: Resolve the treasury vs dispute ownership collision explicitly

Problem:

- `treasury` already owns `/api/disputes`
- `dispute_engine` still owns `/disputes` and `/admin/disputes`
- promoting `dispute_engine` to `/api/disputes` causes a real router collision rather than simple alias drift

Owning files:

- [backend/app/modules.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/backend/app/modules.py:648>)
- [frontend/lib/data/dispute_engine_api.dart](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/frontend/lib/data/dispute_engine_api.dart:46>)

Implementation:

1. Pick one owner for product dispute APIs:
   - either move product dispute workflows under treasury and retire `dispute_engine` public routes
   - or rename `dispute_engine` into a distinct `/api/...` family that does not collide with treasury
2. Until that decision is made, keep `dispute_engine` on legacy mounts and document it as intentional.

Acceptance criteria:

- there is only one product owner for `/api/disputes`-like routes
- no future `api_only` promotion reintroduces the collision

Acceptance criteria:

- creator clip earnings load from a real route
- no frontend code references the retired pre-normalization media clip-earnings namespace
- canonical creator clip earnings calls target `/api/media-engine/me/clip-earnings`, with bare `/media-engine/me/clip-earnings` used only as an explicit legacy fallback

### Fix 3: Normalize wallet endpoint usage

Problem:

- frontend mixes `/api/wallets/...` with singular `/api/wallet/...`
- backend exposes singular public wallet routes under `/wallet`
- plural protected wallet routes are under `/wallets`, then aliased to `/api/wallets`

Owning files:

- [frontend/lib/data/gte_api_repository.dart](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/frontend/lib/data/gte_api_repository.dart:857>)
- [frontend/lib/data/gte_api_repository.dart](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/frontend/lib/data/gte_api_repository.dart:899>)
- [frontend/lib/data/gte_api_repository.dart](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/frontend/lib/data/gte_api_repository.dart:919>)
- [frontend/lib/data/gte_api_repository.dart](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/frontend/lib/data/gte_api_repository.dart:934>)
- [backend/app/wallets/router.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/backend/app/wallets/router.py:94>)
- [backend/app/wallets/router.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/backend/app/wallets/router.py:95>)

Implementation:

Preferred option:

1. Move all frontend wallet calls to the plural API family where applicable:
   - `/api/wallets/summary`
   - `/api/wallets/overview`
   - `/api/wallets/ledger`
   - `/api/wallets/conversions`
   - `/api/wallets/deposits`
   - `/api/wallets/withdrawals`
2. For top-up and transaction endpoints, choose one canonical API family and expose it consistently:
   - either add `/api/wallet/*` aliases for the singular public routes
   - or move frontend to the exact mounted route family and document that wallet top-up remains singular

Recommended direction:

- expose `/api/wallet/*` compatibility aliases in backend if those routes are intended to remain public and auth-aware
- keep business wallet domain canonical under `/api/wallets/*`

Acceptance criteria:

- no frontend wallet call depends on a non-mounted namespace
- wallet route families are documented with singular vs plural meaning

### Fix 4: Decide player action behavior instead of keeping dead calls

Problem:

- frontend still calls:
  - `/players/{id}/scout`
  - `/players/{id}/shortlist`
  - `/players/{id}/contact`
- no mounted backend handlers were found

Owning files:

- [frontend/lib/data/player_service.dart](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/frontend/lib/data/player_service.dart:134>)
- [frontend/lib/data/player_service.dart](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/frontend/lib/data/player_service.dart:138>)
- [frontend/lib/data/player_service.dart](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/frontend/lib/data/player_service.dart:142>)
- [backend/app/players/router.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/backend/app/players/router.py:1>)

Implementation:

Choose one:

1. Implement real backend handlers in `players.router` or another canonical player workflow module.
2. Reclassify these actions as unsupported and remove them from the live backend path.

Recommended direction:

- if these actions are not on the active shipped path, block them honestly in the UI and delete the dead API calls now
- if they are product-critical, implement them behind `/api/players/{id}/...` and update frontend accordingly

Acceptance criteria:

- no frontend-visible player action points at a dead route
- unsupported actions render blocked/unavailable, not fake success

### Fix 5: Remove stale support-only route probes from feature support

Problem:

- support fixtures/probes reference non-runtime routes such as:
  - `/admin/world/clubs`
  - `/admin/world/cultures`
  - `/admin/world/narratives`
  - `/broadcast/home`
  - `/matches/viewer/...`
  - `/matches/3d/...`

Owning files:

- [frontend/lib/features/shared/data/gte_feature_support.dart](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/frontend/lib/features/shared/data/gte_feature_support.dart:392>)
- [frontend/lib/features/shared/data/gte_feature_support.dart](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/frontend/lib/features/shared/data/gte_feature_support.dart:418>)
- [frontend/lib/features/shared/data/gte_feature_support.dart](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/frontend/lib/features/shared/data/gte_feature_support.dart:450>)
- [frontend/lib/features/shared/data/gte_feature_support.dart](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/frontend/lib/features/shared/data/gte_feature_support.dart:699>)

Implementation:

1. Separate app-navigation fixture paths from HTTP API capability checks.
2. Replace support probes with real mounted endpoints:
   - `/api/broadcast/home` instead of `/broadcast/home`
   - actual admin world mutation/read endpoints instead of non-existent collection roots
3. Remove fake match-viewer URL support from HTTP-capability checks.

Acceptance criteria:

- frontend support checks only target real backend contracts

## Contract Cleanup

This batch is broader than the immediate fixes and should happen after the low-risk mismatches are resolved.

### Cleanup 1: Choose a single canonical route family per capability

Candidate families to normalize:

- players
- clubs
- competitions
- market
- wallets
- matches
- match viewer
- notifications
- player cards
- regen universe

Owning files:

- [backend/app/core/api_contract.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/backend/app/core/api_contract.py:122>)
- [backend/app/modules.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/backend/app/modules.py:52>)
- frontend repositories under `frontend/lib/data/**`

Implementation:

1. Document canonical public path per family.
2. Mark which direct legacy paths remain compatibility-only.
3. Update frontend repositories to canonical paths.
4. Keep compatibility aliases for one migration window.

Acceptance criteria:

- every frontend repository family targets one canonical namespace

### Cleanup 2: Stop overloading direct routes and API aliases in new code

Implementation:

1. New backend modules should declare whether they are:
   - canonical `/api/...`
   - direct internal/non-product
   - admin-only
2. Avoid blanket aliasing unless required.
3. Prefer explicit alias routers over generic duplication when semantics differ.

## Runtime Profile Cleanup

### Problem

`tools/run_gtex_live_backend.py` currently boots a reduced local profile, but the distinction is easy to miss.

Owning files:

- [tools/run_gtex_live_backend.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tools/run_gtex_live_backend.py:125>)
- [backend/app/core/config.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/backend/app/core/config.py:56>)
- [backend/app/core/config.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/backend/app/core/config.py:81>)
- [backend/app/core/config.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/backend/app/core/config.py:117>)
- [backend/app/core/config.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/backend/app/core/config.py:141>)
- [backend/app/core/config.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/backend/app/core/config.py:196>)
- [backend/app/core/config.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/backend/app/core/config.py:207>)

### Plan

1. Rename or document the current runner as `reduced-local-live` behavior.
2. Add a fuller integration runner profile with:
   - outbox relay on
   - projection workers on
   - queue consumers on where safe
   - startup seeding policy explicit
3. Emit startup logs that clearly declare:
   - reduced local profile
   - full integration profile
   - staging-like profile

Acceptance criteria:

- engineers can tell from startup output whether they are validating only HTTP routing or actual backend platform behavior

## Product Backend vs Expansion Backend Split

### Required product backend set

Treat these as release-blocking:

- auth/session/users
- clubs/profile
- competitions/hosted/streamer
- matches/match-viewer/broadcast/realtime
- players/market/orders/transfer-market/player-cards
- wallets/treasury/policies
- regen/federations/world/daily-challenges
- creator/community/feed/notifications/moderation/disputes
- admin/ingestion/risk/observability

### Expansion or admin-heavy backend set

These should be explicitly tagged as expansion/admin/experimental:

- academy
- ultimate league
- infinite league
- competitive integrity
- champions league
- world super cup
- fast cups
- ownership groups
- broadcast rights
- tickets
- creator campaigns
- creator cards
- real-world hub
- regens alternate families
- surveillance
- value engine
- agents

Plan:

1. Add a backend ownership/status matrix doc.
2. Mark each module:
   - product
   - admin
   - expansion
   - experimental
   - dormant
3. Use that matrix to drive hydration policy and local profile defaults.

## Suggested Execution Order

Status update:

- `2026-04-19`: `Batch A` is complete in the current workspace. Admin notifications are mounted, creator clip earnings use the canonical media-engine API namespace, dead player actions are blocked instead of calling missing routes, feature-support probes target mounted API contracts, and wallet calls now use the canonical plural `/api/wallets/...` family with backend compatibility aliases retained.

### Batch A: Real contract bugs

1. Mount admin notifications correctly.
2. Fix creator clip earnings namespace.
3. Normalize wallet singular/plural usage.
4. Decide player action behavior.
5. Remove stale feature support probes.

### Batch B: Canonical route normalization

1. Canonicalize `/api/...` families.
2. Keep `/api/v1/...` as compatibility only.
3. Reduce direct route usage in frontend repositories.

### Batch C: Runtime profile clarity

1. Split reduced local vs fuller integration profiles.
2. Improve startup logs and docs.

### Batch D: Expansion isolation

1. Label backend modules by product status.
2. Restrict expansion-domain hydration and ownership.

## Verification Requirements

Add or update tests for:

1. Route contract snapshots for frontend-visible API families.
2. A module-registration test that asserts admin notifications are mounted.
3. A frontend repository path test for wallet/media/player endpoints.
4. A reduced-profile vs full-profile startup smoke test.

## Recommended First Implementation PR

The first PR should contain only Batch A:

- add `notifications_admin` module registration
- fix creator clip earnings route usage
- normalize wallet path usage
- remove or block dead player action calls
- strip stale support-only route probes from HTTP capability checks

That PR gives the largest clarity gain with the least architecture risk.
