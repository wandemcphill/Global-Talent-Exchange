# Current State Contract Matrix

Verified against the current workspace on 2026-04-11.

This document is the Phase 0 source of truth for backend/frontend alignment. It replaces the older audit snapshot where that snapshot no longer matches this checkout.

## Canonical Override - 2026-06-04

The production GTEX direction is now the canonical Flutter/backend football operating system.
The active match experience is 2D broadcast-style match center only.
Legacy Unity, native 3D, pseudo-3D, and original visual runtime work is quarantined and must not be promoted into production navigation, deploy gates, monetization, CTAs, or product-facing contracts.
Older route rows below that describe 3D/native/Unity as live are retained only as historical audit context when not updated.

## Status Labels

- `LIVE`: reachable UI path and real backend path are both present
- `LIVE_WITH_GAP`: feature is live but has truthfulness, durability, placeholder, or scope gaps
- `READ_ONLY`: surfaced in UI, but key write/actions are missing
- `HIDDEN`: backend exists, but the UI surface is hidden or blocked
- `UNWIRED`: backend exists, no meaningful frontend path verified
- `DECISION_REQUIRED`: backend module exists, but product scope still needs ship/hide/deprecate decision
- `QUARANTINED`: legacy/reference surface may exist, but is hidden from production and must not be promoted without explicit user direction
- `STALE_AUDIT_CLOSED`: the older audit claim is not true for this checkout

## Baseline Inventory

- Backend router files found under `backend/app`: `113`
- Frontend feature directories found under `frontend/lib/features`: `39`
- Primary-nav live destinations in the active shell: `5`
- Known screen implementations currently returning `GteRouteIntegrityScreen.blocked/hidden`: `6`

## Active Route Surface Baseline

### Primary navigation

| Surface | State | Notes |
|---|---|---|
| Home | `LIVE` | Active primary destination |
| Matches | `LIVE` | Active primary destination |
| Scouting | `LIVE` | Active primary destination |
| World | `LIVE` | Active primary destination |
| Profile | `LIVE` | Active primary destination |

### Quick-access live routes

| Surface | State | Notes |
|---|---|---|
| Clips | `LIVE` | Quick action, not primary nav |
| Transfer Center | `LIVE` | Real transfer-market route |
| Federations | `LIVE` | Live governance context, membership, rankings |
| National Teams | `LIVE` | Live competition/ranking route |
| Tasks | `LIVE` | Live daily challenge route |
| Streamer Tournament Engine | `LIVE` | Live route |

### Deep or gated routes

| Surface | State | Notes |
|---|---|---|
| Transfer Listing Detail | `HIDDEN` | Deep route |
| Federation Detail | `HIDDEN` | Deep route |
| National Team Detail | `HIDDEN` | Deep route |
| Competition Detail | `HIDDEN` | Deep route |
| 2D Match Viewer | `LIVE_WITH_GAP` | Canonical match direction; deep route/surface still needs final route-depth and realtime verification |
| Broadcast+ Viewer | `HIDDEN` | Deep route |
| 3D Match Viewer | `QUARANTINED` | Legacy/reference only; no production promotion |
| 2D Spectate Probe | `HIDDEN` | Deep route |
| Simulation | `HIDDEN` | Reserved for explicit fixture-mode local simulation |
| Native 3D | `QUARANTINED` | Android/native bridge code may exist, but production GTEX must not route or monetize it |

### Known route-integrity walls still present in screen implementations

| Screen | State | Notes |
|---|---|---|
| God Mode Admin | `HIDDEN` | Screen intentionally hidden |
| Treasury Ops | `HIDDEN` | Screen returns blocked wall |
| Admin Financial Dashboard | `HIDDEN` | Screen returns blocked wall |
| Club Admin | `HIDDEN` | Screen returns blocked wall |
| Creator Leaderboard | `HIDDEN` | Screen returns blocked wall |
| Community Hub | `HIDDEN` | Screen intentionally hidden |

## Stale Audit Claims Closed

These items were valid for an older snapshot but are not open defects in this checkout:

| Audit claim | Current status |
|---|---|
| Alembic versions missing | `STALE_AUDIT_CLOSED` |
| Paystack signature verification absent | `STALE_AUDIT_CLOSED` |
| Startup auth secret not validated | `STALE_AUDIT_CLOSED` |
| Frontend platform directories missing | `STALE_AUDIT_CLOSED` |
| Native 3D bridge absent | `STALE_AUDIT_CLOSED` |
| Wallet top-up uses wrong request/response field names | `STALE_AUDIT_CLOSED` |
| Fan prediction route is not registered | `STALE_AUDIT_CLOSED` |
| Hosted competition launch/finance paths lack UI surface | `STALE_AUDIT_CLOSED` |
| Transfer-market frontend is only manager-market wiring | `STALE_AUDIT_CLOSED` |
| World simulation has no frontend wiring | `STALE_AUDIT_CLOSED` |
| Club badge, dynasty, prestige leaderboard, and honors timeline routes are missing/mismatched | `STALE_AUDIT_CLOSED` |

## Canonical Domain Matrix

| Domain | Backend surface | Frontend surface | Status | Current reality | Fix phase |
|---|---|---|---|---|---|
| Auth and sessions | `auth`, auth-session checks | Login/signup/profile/session flows | `LIVE_WITH_GAP` | Boot-time auth secret validation exists, but custom token implementation remains long-term audit debt. | `A1`, `A10` |
| Wallet funding and withdrawal | `wallets`, payment providers | Wallet overview, funding, withdrawal screens | `LIVE_WITH_GAP` | Core wallet UI exists and active rails work, but stub rails are still exposed or ambiguously represented. | `A1` |
| Payment provider truthfulness | Stub providers under `wallets/providers` | Wallet method discovery and funding UX | `LIVE_WITH_GAP` | Card-like methods still imply support without real processor implementations. | `A1` |
| Admin finance and god mode | `admin_finance`, `admin_godmode`, `treasury` | Admin command center plus blocked screens | `HIDDEN` | Backend is substantive, but several dedicated admin screens still resolve to blocked/hidden walls. Mutable admin-finance files are tracked in git. | `A1`, `A5` |
| Schema and startup safety | Startup/config/alembic | No direct UI | `LIVE_WITH_GAP` | Alembic exists, but startup still has schema-repair behavior that can mask migration drift. | `A2` |
| Backbone and degraded mode | `backbone`, Kafka/Redis consumers, worker entry points | No direct UI | `LIVE_WITH_GAP` | System degrades rather than hard-crashes, but dependency state is not explicit enough for operators. | `A2`, `A9` |
| Creator profile and referral durability | `segment_creators`, referrals services and models | Creator dashboard, referral hub, rewards, share-code screens | `LIVE_WITH_GAP` | Core creator profile routes are live under `/api/creators/...`, but durability and ownership are still split from creator-ops routes under `/api/creator/...`. | `A3` |
| Creator application and share market ops | `creator/router` creator and admin routes | Creator application flow, creator share-market repositories/screens | `LIVE` | Onboarding, verification, application, and fan-share-market operations are live under `/api/creator/...` and `/api/admin/creator/...`; the remaining risk is namespace ownership confusion, not route absence. | Regression coverage plus ownership cleanup |
| Creator monetization and public media assets | `media_engine`, highlight/download services | Creator finance clip earnings, creator league monetization, clip/download links | `LIVE_WITH_GAP` | Authenticated monetization calls now use `/api/media-engine/...`, but public download URLs intentionally remain under bare `/media-engine/downloads/...`. This mixed API/public shape is real and should not be flattened accidentally. | `A4`, ownership cleanup |
| Highlights | `highlights`, `media_engine` | Match highlights screen | `LIVE_WITH_GAP` | Backend can fall back to placeholder black renders and still record success semantics. | `A4` |
| Tasks and daily challenges | `daily_challenge_engine` | Tasks screen plus older GTEX UI demo surfaces | `LIVE_WITH_GAP` | Live challenge claim flow exists; older demo task flows still use shallow local state and should not be treated as canonical. | `A4` |
| Fixture fallback behavior | Multiple APIs | Secondary frontend APIs | `LIVE_WITH_GAP` | Main shell is mostly truthful, but many secondary APIs still default to `liveThenFixture`. | `A4` |
| Club identity | `club_identity` dynasty/jerseys/reputation/trophies | Dynasty, trophy, honors, jersey, reputation screens | `LIVE` | Backend/frontend contract is aligned in the current checkout. | None beyond regression tests |
| Club ops and academy/scouting/finance | `academy`, `club_finance`, related club ops modules | Club finance, scouting, academy, branding, sponsorship catalog screens | `LIVE_WITH_GAP` | Extensive UI exists, but many surfaces still allow fixture fallback and some deeper action flows remain incomplete. | `A4`, `A8` |
| Hosted competitions | `hosted_competition_engine` | Competition hub, hosted detail, launch, finance | `LIVE` | Launch and finance are wired in the current checkout. | Regression coverage only |
| Fan predictions | `fan_predictions` | Registered route and prediction screen | `LIVE` | Deep route is registered and functional; the remaining issue is discovery, not absence. | Optional product polish |
| Fan Wars | `fan_wars` | Fan Wars screen and controller | `LIVE_WITH_GAP` | Screen exists, but some intended participation/admin actions still look incomplete or underexposed. | `A8` |
| Transfer market | `transfer_market` | Transfer center and transfer market screens/providers | `LIVE` | Real transfer-market endpoints are wired in the current checkout. | Regression coverage only |
| Player-card marketplace | `player_cards` marketplace and loans | Player-card marketplace screen/controller/repository | `LIVE` | Sales, swaps, and loan settlement are wired. | Regression coverage only |
| Federations | `federations` | Federations hub and federation screens | `LIVE` | Live federation route is wired, including governance context and rankings. | `A8` for action depth |
| Governance | `governance_engine` | Federation governance context plus standalone API file | `READ_ONLY` | Governance data is surfaced through federation views, but standalone governance actions are not clearly shipped in UI. | `A6`, `A8` |
| Community and social | `community_engine`, `club_social` | Social screen plus hidden community hub | `HIDDEN` | Backend exists; active shell still hides community hub and broader community actions are not fully exposed. | `A5`, `A6`, `A7` |
| Gifting | `gift_engine` | `GtexGiftingSheet` exists | `UNWIRED` | Widget exists but no verified reachable call site sends gifts through the backend. | `A6` |
| Sponsorship | `sponsorship_engine` | Sponsorship contract/package screens plus admin APIs | `READ_ONLY` | Contract and package views exist, but user-side offer discovery and application flow are missing. | `A6`, `A8` |
| Replay | `matches` replay endpoints | Match replay calls from frontend | `LIVE_WITH_GAP` | Frontend replay works through match replay endpoints. | `A8` |
| Replay archive | `replay_archive` | No verified dedicated UI path | `UNWIRED` | Archive-specific policy and retrieval routes exist, but the frontend is not using them as the primary replay surface. | `A8` |
| Match center | `matches`, `live_matches`, realtime match streams | 2D viewer, broadcast match center | `LIVE_WITH_GAP` | Canonical direction is 2D broadcast match center with backend-authored score, timeline, stats, positions, commentary, and reconnect state. Legacy 3D/native bridge paths are quarantined. | `A4`, `A5` |
| World simulation | `world_simulation`, `football_universe`, related world routes | Football world simulation feature/screens | `LIVE` | Contrary to the old audit, this is wired in the current checkout. | Regression coverage only |
| Streamer tournament engine | `streamer_tournament_engine` | Live streamer engine route/screen | `LIVE` | Current surface is wired. | Regression coverage only |
| Creator-league settlements/admin | Creator-league admin and settlement paths | Creator league admin screen/routes | `LIVE` | Admin settlement flow exists in current checkout. | Regression coverage only |

## Decision Queue: Backend Modules With No Verified Meaningful Frontend Surface

These modules are present in the backend and need an explicit product decision even if no immediate implementation starts.

| Module family | Current status | Notes | Fix phase |
|---|---|---|---|
| `reward_engine` | `DECISION_REQUIRED` | No verified dedicated frontend surface found. | `A7` |
| `betting` | `DECISION_REQUIRED` | Backend router exists, no meaningful frontend path verified. | `A7` |
| `club_infra_engine` | `DECISION_REQUIRED` | Backend exists; no verified upgrade/action UI found. | `A7` |
| `club_social` | `DECISION_REQUIRED` | Backend exists, but active frontend community path remains hidden and broader social graph actions are not verified. | `A7` |
| `history_engagement` | `DECISION_REQUIRED` | No verified frontend surface found. | `A7` |
| `legend_layer` | `DECISION_REQUIRED` | No verified frontend surface found. | `A7` |
| `live_ops` | `DECISION_REQUIRED` | No verified frontend surface found. | `A7` |
| `manager_duels` | `DECISION_REQUIRED` | No verified frontend duel surface found. | `A7` |
| `moments` | `DECISION_REQUIRED` | No verified canonical live moments UI found. | `A7` |
| `regen_ecosystem` | `DECISION_REQUIRED` | Regen UI exists elsewhere, but ecosystem-specific action surface is not verified. | `A7` |
| `simulation_matchmaking` | `DECISION_REQUIRED` | No verified frontend surface found. | `A7` |
| `surveillance` | `DECISION_REQUIRED` | Backend exists, no verified admin UI path found. | `A7` |
| `ticketing` | `DECISION_REQUIRED` | Backend exists, no verified standalone ticketing UI found. | `A7` |
| `ultimate_league` | `DECISION_REQUIRED` | Backend exists, no verified frontend surface found. | `A7` |
| `infinite_league` | `DECISION_REQUIRED` | Backend exists, no verified frontend surface found. | `A7` |
| `broadcast_rights` | `DECISION_REQUIRED` | Backend exists, no verified frontend surface found. | `A7` |
| `creator_campaign_engine` | `DECISION_REQUIRED` | Backend exists, no verified user-facing campaign flow found. | `A7` |
| `fast_cups` | `DECISION_REQUIRED` | Backend exists, no verified dedicated fast-cup creation/discovery path found. | `A7` |

## Platform and Internal Modules Outside Direct Frontend Contract Scope

These backend families are real and important, but they are not expected to have direct frontend feature parity by themselves:

- `backbone`
- `bootstrap`
- `cache`
- `common`
- `config`
- `core`
- `economy`
- `fairness`
- `global_memory`
- `infrastructure`
- `integrity_engine`
- `jobs`
- `ledger`
- `models`
- `observability`
- `orchestrator`
- `runtime_config`
- `value_engine`
- related admin/internal routing families such as `admin_access`, `analytics`, `moderation`, `policies`, and `risk_ops_engine`

These still matter for later remediation phases, but they are not counted as missing frontend features by default.

## Phase Mapping Summary

| Phase | What it resolves |
|---|---|
| `A1` | Payment truthfulness, fraud protection coverage, mutable finance state in git |
| `A2` | Schema drift, migration discipline, runtime/dependency clarity |
| `A3` | In-memory creator/referral state and durability gaps |
| `A4` | Placeholder success states, fixture fallback, lint/config truthfulness |
| `A5` | Hidden/blocked route cleanup |
| `A6` | Missing user actions for already-shipping features |
| `A7` | Ship/hide/deprecate decisions for backend-only modules |
| `A8` | Completion of partially wired/read-only features |
| `A9` | Regression coverage and observability |
| `A10` | Code-lie cleanup, naming cleanup, doc alignment |

## Exit Condition For Phase 0

Phase 0 is complete when this matrix is the reference document used to drive Phases `A1` through `A10`, and later task work updates this matrix rather than re-litigating the older audit snapshot.
