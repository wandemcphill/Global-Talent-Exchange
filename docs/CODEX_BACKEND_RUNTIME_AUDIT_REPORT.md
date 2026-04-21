# CODEX Backend Runtime Audit Report

## Scope

This audit answers four questions:

1. What backend runtime does this project actually boot?
2. What backend domains does the current project expect?
3. Which frontend expectations still do not map cleanly to mounted backend routes?
4. Which richer backend domains exist but are currently outside the active product path?

Raw comparison artifact generated during this audit:

- `.codex_tmp/backend_route_audit_runtime.json`

Audit basis:

- `backend/app/main.py`
- `backend/app/modules.py`
- `backend/app/core/api_contract.py`
- `backend/app/core/config.py`
- `tools/run_gtex_live_backend.py`
- `Docs/CODEX_FRONTEND_BACKEND_WIRING_REPORT.md`
- `Docs/FRONTEND_WIRING_READINESS.md`
- `Docs/CODEX_SILENT_FALLBACK_KILL_LIST.md`

## Executive Summary

- The project does **not** have many separate deployed backends. It has **one large FastAPI monolith** that behaves like a backend platform made of many domain slices.
- That monolith is mounted through `create_app()` in `backend/app/main.py`, then expanded by `register_modules(app, modules)` in `backend/app/main.py`.
- The module registry in `backend/app/modules.py` defines **154 `DomainModule`s**. Only a small eager subset is mounted immediately; the rest are lazy-hydrated.
- The local launcher you are actually using, `tools/run_gtex_live_backend.py`, boots a **reduced local profile** with several async/runtime systems explicitly disabled.
- Runtime route audit result:
  - **2619** mounted backend paths
  - **419** unique frontend network paths
  - **397** frontend paths matched mounted backend routes
  - **22** frontend paths did not match runtime routes
  - **101** backend route families are referenced by the frontend network layer
  - **169** runtime backend route families had no frontend network references in this audit

The core problem is not only "missing routes." It is a combination of:

- mount-pattern fragmentation (`/x`, `/api/x`, `/api/v1/x`)
- a reduced local runtime profile that disables meaningful subsystems
- frontend code that still references some legacy or support-only endpoints
- a backend surface area that is much larger than the active shipped shell

## Finding 1: The runtime is a modular platform, not a simple API

`backend/app/main.py` wires the app in three layers:

- `register_core(app)` mounts health, middleware, and shared infrastructure
- `install_api_contracts(app)` adds versioned alias behavior
- `register_modules(app, modules)` mounts the domain modules

Relevant code:

- [backend/app/main.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/backend/app/main.py:106>)
- [backend/app/main.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/backend/app/main.py:107>)
- [backend/app/main.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/backend/app/main.py:108>)

`backend/app/modules.py` makes the backend behave like multiple internal backends:

- lazy-hydration bypass for auth, competitions, broadcast, matches, match viewer, hosted competitions, and streamer tournaments
- eager modules for auth, realtime, competitions, hosted competitions, live matches, manager market, match viewer, streamer tournaments, and world simulation

Relevant code:

- [backend/app/modules.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/backend/app/modules.py:15>)
- [backend/app/modules.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/backend/app/modules.py:30>)
- [backend/app/modules.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/backend/app/modules.py:52>)

Implication:

- The project already assumes a multi-domain backend platform.
- Frontend route failures can come from domain registration shape, mount alias shape, or disabled runtime services, not only from "route missing from code."

## Finding 2: Local "live" backend runs on a stripped profile

The backend you are currently using is not the full platform profile.

`tools/run_gtex_live_backend.py` sets local defaults that disable large parts of the platform:

- startup seeding off
- API cache off
- distributed rate limiting off
- task queue off
- outbox relay off
- Kafka API queue consumer off
- Kafka simulation consumer off
- projection workers off
- live commentary LLM off
- social content LLM off

Relevant code:

- [tools/run_gtex_live_backend.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tools/run_gtex_live_backend.py:125>)
- [tools/run_gtex_live_backend.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tools/run_gtex_live_backend.py:127>)
- [tools/run_gtex_live_backend.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tools/run_gtex_live_backend.py:128>)
- [tools/run_gtex_live_backend.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tools/run_gtex_live_backend.py:129>)
- [tools/run_gtex_live_backend.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tools/run_gtex_live_backend.py:130>)
- [tools/run_gtex_live_backend.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tools/run_gtex_live_backend.py:131>)
- [tools/run_gtex_live_backend.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tools/run_gtex_live_backend.py:132>)
- [tools/run_gtex_live_backend.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tools/run_gtex_live_backend.py:133>)
- [tools/run_gtex_live_backend.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tools/run_gtex_live_backend.py:134>)
- [tools/run_gtex_live_backend.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tools/run_gtex_live_backend.py:135>)

Implication:

- A route may exist in code and even be mounted, while the domain still behaves partially inert in local runs because its workers, relays, projections, or background flows are disabled.
- This is especially important for commentary, notifications, ingestion, feed freshness, analytics projections, and async market/runtime behavior.

## Finding 3: The project expects a smaller "required backend set" than the codebase contains

The shipped shell documented in `Docs/CODEX_FRONTEND_BACKEND_WIRING_REPORT.md` depends on a narrower subset of backend families than the codebase exposes.

The active shipped screens explicitly depend on:

- auth/session/profile
- competitions
- hosted competitions
- streamer tournaments
- players / player shares / transfer market
- wallets / treasury / policy / compliance
- regen universe / federations / world summaries
- matches / match viewer / broadcast
- daily challenges
- feed / clips

Relevant doc anchors:

- [Docs/CODEX_FRONTEND_BACKEND_WIRING_REPORT.md](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/Docs/CODEX_FRONTEND_BACKEND_WIRING_REPORT.md:24>)
- [Docs/CODEX_FRONTEND_BACKEND_WIRING_REPORT.md](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/Docs/CODEX_FRONTEND_BACKEND_WIRING_REPORT.md:28>)
- [Docs/CODEX_FRONTEND_BACKEND_WIRING_REPORT.md](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/Docs/CODEX_FRONTEND_BACKEND_WIRING_REPORT.md:30>)
- [Docs/CODEX_FRONTEND_BACKEND_WIRING_REPORT.md](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/Docs/CODEX_FRONTEND_BACKEND_WIRING_REPORT.md:32>)
- [Docs/CODEX_FRONTEND_BACKEND_WIRING_REPORT.md](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/Docs/CODEX_FRONTEND_BACKEND_WIRING_REPORT.md:33>)
- [Docs/CODEX_FRONTEND_BACKEND_WIRING_REPORT.md](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/Docs/CODEX_FRONTEND_BACKEND_WIRING_REPORT.md:34>)
- [Docs/CODEX_FRONTEND_BACKEND_WIRING_REPORT.md](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/Docs/CODEX_FRONTEND_BACKEND_WIRING_REPORT.md:38>)
- [Docs/CODEX_FRONTEND_BACKEND_WIRING_REPORT.md](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/Docs/CODEX_FRONTEND_BACKEND_WIRING_REPORT.md:42>)
- [Docs/CODEX_FRONTEND_BACKEND_WIRING_REPORT.md](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/Docs/CODEX_FRONTEND_BACKEND_WIRING_REPORT.md:43>)

That is the backend contract the current product actually needs to keep healthy.

## Finding 4: The backend surface is heavily fragmented by mount style

The same capability is often reachable through more than one namespace:

- direct routes like `/match-viewer/...`
- `/api/...` aliases
- `/api/v1/...` aliases generated by API contract wrapping

Relevant code:

- [backend/app/core/api_contract.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/backend/app/core/api_contract.py:31>)
- [backend/app/core/api_contract.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/backend/app/core/api_contract.py:122>)
- [backend/app/core/api_contract.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/backend/app/core/api_contract.py:129>)
- [backend/app/core/api_contract.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/backend/app/core/api_contract.py:131>)

Examples of duplicated families found in runtime:

- `/api/clubs` and `/clubs`
- `/api/players` and `/players`
- `/api/market` and `/market`
- `/api/wallets` and `/wallets`
- `/api/matches` and `/matches`
- `/api/match-viewer` and `/match-viewer`
- `/api/player-cards` and `/player-cards`
- `/api/regen-universe` and `/regen-universe`
- `/api/competitive-integrity` and `/competitive-integrity`
- `/api/ultimate-league` and `/ultimate-league`

Implication:

- Some "missing backend" symptoms are really namespace drift, not absent business logic.
- The backend needs a canonical public mount policy.

## Current Consolidation Hotspots

- `treasury` already owns `/api/disputes`, while `dispute_engine` still mounts `/disputes` and `/admin/disputes`. Promoting `dispute_engine` into `/api/disputes` causes a real router collision.
- `creator` and `media_engine` still expose mixed backend shapes: the creator product is split across at least two owners, with `/api/creators/...` served by `backend/app/segments/creators/segment_creators.py` and `/api/creator/...` plus admin/share-market routes served by `backend/app/creator/router.py`. The only remaining bare creator aliases are `/creators/me/insights` and `/creators/me/copilot/analyze`; there is no generic bare `/creators/{handle}` parity. `media_engine` still mounts bare `/media-engine/*` even though the shipped frontend now targets `/api/media-engine/*`. `media_engine` also emits public download/share URLs such as `/media-engine/downloads/...`, so collapsing that module to `api_only` would be a behavior change, not just alias cleanup. Community-facing web links under `/community/creator/...` are a separate public surface and should not be collapsed into API routing by accident.

### Creator Ownership Matrix

- `/api/creators/...`: creator identity, profile, finance, and copilot endpoints from `backend/app/segments/creators/segment_creators.py`. The only legacy bare aliases left in this family are `/creators/me/insights` and `/creators/me/copilot/analyze`. These are consumed by `frontend/lib/data/creator_api.dart`.
- `/api/creator/...` and `/api/admin/creator/...`: creator onboarding, application, verification, and fan-share-market endpoints from `backend/app/creator/router.py`. These are consumed by `frontend/lib/data/creator_application_api.dart` and `frontend/lib/features/creator_share_market/data/creator_share_market_repository.dart`.
- `/api/v1/media-engine/...` and `/api/v1/admin/media-engine/...`: creator clip earnings, creator league monetization, and stadium control endpoints exposed from `backend/app/media_engine/router.py` through the API contract layer. These are consumed by `frontend/lib/data/creator_api.dart` and `frontend/lib/features/creator_stadium_monetization/data/creator_stadium_monetization_repository.dart`.
- `/media-engine/downloads/...` and `/community/creator/...`: public non-API asset and profile-link surfaces. These are intentionally separate from the authenticated API contract and should not be collapsed into `api_only` routing.

## Required Backend Domains The Project Expects

This is the practical backend map the project currently depends on.

### 1. Core identity and session backend

Purpose:

- sign-in
- sign-up
- bootstrap session
- role and permission context

Primary route families:

- `/api/auth`
- `/api/session`
- `/auth`
- `/users`

Representative modules:

- `auth`
- `users`

### 2. Club and profile context backend

Purpose:

- profile screen
- user club context
- club-based authorization for live product surfaces

Primary route families:

- `/users`
- `/clubs`
- `/api/clubs`

Representative modules:

- `clubs`
- `canonical_clubs`
- `admin_clubs`
- club identity subdomains

### 3. Competition backend

Purpose:

- GTEX competitions
- hosted competitions
- streamer tournaments
- standings, fixtures, joins, publish, launch

Primary route families:

- `/api/competitions`
- `/api/hosted-competitions`
- `/api/streamer-tournaments`

Representative modules:

- `competitions`
- `hosted_competition_engine`
- `streamer_tournament_engine`

### 4. Match, viewer, and broadcast backend

Purpose:

- spectating
- match session payloads
- commentary
- broadcast channels
- replay and match streams

Primary route families:

- `/api/matches`
- `/matches`
- `/api/match-viewer`
- `/match-viewer`
- `/api/broadcast`
- `/realtime`

Representative modules:

- `matches`
- `match_viewer`
- `match_engine`
- `broadcast_network`
- `broadcast`
- `realtime`
- `live_matches`
- `replay_archive`

### 5. Market and player backend

Purpose:

- real player discovery
- player share markets
- transfer listings and bids
- player cards

Primary route families:

- `/players`
- `/api/players`
- `/api/market`
- `/api/orders`
- `/api/transfer-market`
- `/player-cards`

Representative modules:

- `players`
- `market`
- `orders`
- `transfer_market`
- `player_cards`
- `manager_market`

### 6. Wallet, treasury, policy, and finance backend

Purpose:

- balances
- deposits and withdrawals
- bank accounts
- KYC
- treasury ops
- policy/compliance surfaces

Primary route families:

- `/wallets`
- `/api/wallets`
- `/wallet`
- `/api/admin/treasury`
- `/api/bank-accounts`
- `/api/kyc`
- `/policies`

Representative modules:

- `wallets`
- `treasury`
- `policies`
- `admin_finance`
- `admin_godmode`

### 7. World and progression backend

Purpose:

- regen universe
- federations
- world narratives and culture
- daily challenges

Primary route families:

- `/regen-universe`
- `/api/federations`
- `/api/world`
- `/api/daily-challenges`

Representative modules:

- `regen_universe`
- `federations`
- `world_simulation`
- `daily_challenge_engine`

### 8. Community, creator, and clip backend

Purpose:

- clips/feed
- creator onboarding
- creator dashboards
- moderation, disputes, governance
- notifications

Primary route families:

- `/feed`
- `/api/creator`
- `/api/creators`
- `/media-engine/creator-league`
- `/api/notifications`
- `/api/moderation`
- `/api/disputes` (treasury-owned dispute surface)
- `/disputes` (legacy `dispute_engine` surface that collides if promoted)
- `/api/governance`

Representative modules:

- `creator`
- `community_engine`
- `media_engine`
- `viral`
- `notifications`
- `moderation`
- `dispute_engine`
- `governance_engine`

### 9. Admin and ingestion backend

Purpose:

- real-player import
- operational controls
- admin dashboards
- finance controls
- referrals and clubs admin

Primary route families:

- `/internal/ingestion`
- `/api/admin/*`
- `/admin/*`

Representative modules:

- `ingestion`
- `player_import`
- `admin_access`
- `admin_finance`
- `admin_engine`
- `risk_ops_engine`
- `observability`

## Real Contract Gaps Found In The Current Runtime

These are the backend mismatches that appear real, not just naming noise.

### 1. Admin notification announcements were previously unmounted

Frontend expects:

- `/admin/notifications/announcements`

Backend file defines that admin route:

- [backend/app/notifications/router.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/backend/app/notifications/router.py:178>)

But module registration mounts only `notifications_router`, not the aggregate `router`:

- [backend/app/modules.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/backend/app/modules.py:705>)

Current status:

- This gap is closed in the current checkout.
- `notifications_admin` is mounted through `backend/app/modules.py`, and shipped frontend/admin callers now use canonical `/api/admin/notifications/...` routes.

### 2. Media earnings path drift

Frontend expects:

- [frontend/lib/data/creator_api.dart](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/frontend/lib/data/creator_api.dart:1>) referencing `/api/media-engine/me/clip-earnings` first, with an explicit legacy fallback to `/media-engine/me/clip-earnings`

Backend mounts:

- [backend/app/media_engine/router.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/backend/app/media_engine/router.py:71>)
- [backend/app/media_engine/router.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/backend/app/media_engine/router.py:770>)

Current status:

- The old pre-normalization media clip-earnings namespace drift is closed in the current checkout.
- The remaining issue is architectural, not a missing route: `media_engine` still mixes authenticated API routes under `/api/media-engine/...` with intentional public asset routes under bare `/media-engine/downloads/...`.

Actual mounted family is `media-engine`, not `media`.

Result:

- This is a namespace mismatch, not a missing earnings implementation.

### 3. Wallet namespace drift

Frontend still calls singular `/api/wallet/*` paths:

- [frontend/lib/data/gte_api_repository.dart](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/frontend/lib/data/gte_api_repository.dart:857>)
- [frontend/lib/data/gte_api_repository.dart](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/frontend/lib/data/gte_api_repository.dart:899>)
- [frontend/lib/data/gte_api_repository.dart](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/frontend/lib/data/gte_api_repository.dart:919>)
- [frontend/lib/data/gte_api_repository.dart](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/frontend/lib/data/gte_api_repository.dart:934>)

Backend mounts:

- plural wallet domain under `/wallets`
- public singular routes under `/wallet`

Relevant code:

- [backend/app/wallets/router.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/backend/app/wallets/router.py:94>)
- [backend/app/wallets/router.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/backend/app/wallets/router.py:95>)
- [backend/app/wallets/router.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/backend/app/wallets/router.py:464>)
- [backend/app/wallets/router.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/backend/app/wallets/router.py:476>)
- [backend/app/wallets/router.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/backend/app/wallets/router.py:510>)

Result:

- `/api/wallet`
- `/api/wallet/transactions`
- `/api/wallet/top-up/initiate`
- `/api/wallet/top-up/verify`

do not exist as mounted runtime routes even though the wallet subsystem itself is present.

### 4. Player workflow action endpoints are referenced in frontend but absent in backend

Frontend still calls:

- [frontend/lib/data/player_service.dart](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/frontend/lib/data/player_service.dart:134>)
- [frontend/lib/data/player_service.dart](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/frontend/lib/data/player_service.dart:138>)
- [frontend/lib/data/player_service.dart](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/frontend/lib/data/player_service.dart:142>)

Referenced endpoints:

- `/players/{id}/scout`
- `/players/{id}/shortlist`
- `/players/{id}/contact`

No matching mounted runtime routes were found in `players.router`.

Result:

- This is a real frontend-to-backend gap.

### 5. Admin world feature support probes do not match actual admin world routes

Frontend support code probes collection roots:

- `/admin/world/clubs`
- `/admin/world/cultures`
- `/admin/world/narratives`

Backend actually mounts:

- [backend/app/world_simulation/router.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/backend/app/world_simulation/router.py:19>)
- [backend/app/world_simulation/router.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/backend/app/world_simulation/router.py:82>)
- [backend/app/world_simulation/router.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/backend/app/world_simulation/router.py:97>)
- [backend/app/world_simulation/router.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/backend/app/world_simulation/router.py:112>)

Result:

- The backend has admin world mutation endpoints, but not the collection endpoints the feature-support code probes.
- This looks like stale support wiring, not a missing world system.

## Rich Backend Domains Currently Ignored Or Barely Used

These families have meaningful route depth but little or no frontend network usage in this audit.

### Operational and control plane domains

- `/admin/ops`
- `/admin/config`
- `/admin/player-import`
- `/api/admin/managers`
- `/surveillance`
- `/value-engine`

### Alternate competition and simulation domains

- `/competitive-integrity`
- `/api/competitive-integrity`
- `/ultimate-league`
- `/api/ultimate-league`
- `/infinite-league`
- `/api/infinite-league`
- `/champions-league`
- `/api/champions-league`
- `/world-super-cup`
- `/api/world-super-cup`
- `/fast-cups`
- `/api/fast-cups`
- `/leagues`
- `/api/leagues`

### Creator, campaign, and social expansion domains

- `/creator/cards`
- `/creator-campaigns`
- `/campaigns`
- `/api/campaigns`
- `/community/creator-matches`
- `/social`
- `/api/challenges`

### Rights, ownership, and meta-economy domains

- `/broadcast-rights`
- `/api/broadcast-rights`
- `/ownership-groups`
- `/api/ownership-groups`
- `/tickets`
- `/api/tickets`

### World and alternate progression domains

- `/academy`
- `/api/academy`
- `/regens`
- `/api/regens`
- `/real-world`
- `/awards`
- `/api/viral`

The important distinction:

- some of these are truly unused
- some are live backend capability that exists but is not part of the active shipped shell
- some are duplicated namespaces of an already-used domain

`Docs/FRONTEND_WIRING_READINESS.md` already hints at this split by listing large backend subsystems that exist and still need UI wiring:

- [Docs/FRONTEND_WIRING_READINESS.md](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/Docs/FRONTEND_WIRING_READINESS.md:7>)
- [Docs/FRONTEND_WIRING_READINESS.md](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/Docs/FRONTEND_WIRING_READINESS.md:47>)
- [Docs/FRONTEND_WIRING_READINESS.md](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/Docs/FRONTEND_WIRING_READINESS.md:75>)

## Silent Fallback Constraint Still Matters

The product rules remain correct:

- no user-visible live route should silently fall back
- no mock/stub/fixture should pretend to be live
- no swallowed backend failure should look like success

Relevant policy:

- [Docs/CODEX_SILENT_FALLBACK_KILL_LIST.md](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/Docs/CODEX_SILENT_FALLBACK_KILL_LIST.md:25>)
- [Docs/CODEX_SILENT_FALLBACK_KILL_LIST.md](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/Docs/CODEX_SILENT_FALLBACK_KILL_LIST.md:26>)
- [Docs/CODEX_SILENT_FALLBACK_KILL_LIST.md](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/Docs/CODEX_SILENT_FALLBACK_KILL_LIST.md:27>)

This means the right backend cleanup is:

- reduce ambiguity
- choose canonical route families
- expose missing routes honestly
- block unsupported surfaces rather than pretending they are wired

## Recommended Consolidation Plan

### Phase 1: Canonicalize public namespaces

Pick one public convention and stick to it:

- preferred public API family: `/api/...`
- compatibility alias family: `/api/v1/...`
- no new direct public routes unless they are explicitly non-API

Stop expanding both `/x` and `/api/x` for the same feature unless there is a hard migration reason.

### Phase 2: Separate core product backend from expansion backends

Treat these as the required product backend set:

- auth/session/users
- clubs/profile context
- competitions/hosted/streamer
- matches/match-viewer/broadcast/realtime
- players/market/orders/transfer-market/player-cards
- wallets/treasury/policies
- regen/federations/world/daily-challenges
- feed/creator/community/notifications/moderation/disputes
- admin/ingestion/risk/observability

Everything else should be marked one of:

- active product
- expansion track
- admin-only
- experimental
- dormant

### Phase 3: Fix the real mismatches first

Highest-value fixes:

1. mount admin notifications correctly
2. reconcile `media` vs `media-engine`
3. reconcile singular `/api/wallet/*` vs mounted wallet namespaces
4. either implement or delete player `scout`, `shortlist`, and `contact` calls
5. purge support-only route probes that look like real contracts

### Phase 4: Stop using the stripped local profile as proof of full backend health

Keep `tools/run_gtex_live_backend.py` for local lightweight runs, but document clearly that it is a reduced profile.

For true integration verification, add a fuller staging-like profile with:

- projection workers
- outbox relay
- queue consumers
- realistic notification/commentary/feed runtime behavior

## Bottom Line

The backend is messy in a specific way:

- not because there are many independent backends
- but because one modular backend currently exposes too many parallel route families, too many expansion domains, and too many runtime-profile differences

What the project **actually needs** is a clear canonical backend contract for the active shell, plus explicit separation between:

- required product backend domains
- admin/backoffice domains
- expansion domains
- experimental or dormant domains

Without that split, you keep getting the same class of failure:

- frontend calls a path that exists in concept
- backend implements similar logic somewhere else
- local runtime disables part of the machinery
- and the result looks like "the backend is broken" even when the problem is really contract drift
