# CODEX Auth + Schema Emergency Report

Verified on March 30, 2026.

## Source Truth

- `Docs/CODEX_RUNTIME_PROOF_REPORT.md`
- `Docs/CODEX_FULL_APP_VERIFICATION_REPORT.md`

## Baseline Before Repair

- Shipped runtime database: `gte_backend.db`
- Shipped Alembic revision on disk before repair: `20260322_0029_regen_universe_layer`
- Stale shipped database backup created at: `.codex_tmp/gte_backend_pre_auth_schema_fix_20260330_072615.db`

Confirmed missing runtime relations on the shipped database before repair:

- `wallets`
- `viral_leaderboard_entries`
- `season_pass_seasons`
- `gtex_jackpot_rounds`
- `leaderboard_seasons`
- `national_regen_seeds`
- `player_share_markets`
- `player_share_events`

Source-truth auth baseline from the runtime proof report:

- `POST /auth/register` timed out at about `20011ms`
- `POST /auth/login` timed out at about `20007ms`
- no completed uvicorn access log entries were emitted for those requests

Source-truth schema/runtime baseline from the runtime proof report:

- `/regen-universe/tracking` was blocked by missing `national_regen_seeds`
- player-share routes were blocked by missing `player_share_markets` and `player_share_events`
- wallet/compliance routes were blocked by missing `wallets`
- streamer season and leaderboard routes were blocked by missing `leaderboard_seasons`

## Repair Applied

- Auth repair already present in the workspace was preserved and runtime-proven:
  - auth routes bypass lazy module hydration
  - `auth` remains eager-loaded
- The shipped database was upgraded from `0029` to the current workspace repair head.
- The runtime upgrade path was restored through `backend/migrations/versions/20260330_0077_merge_runtime_schema_heads.py`, which merges the competing `0075` and `0076` schema-repair branches back into a single Alembic head.

Why the merge migration was required:

- the workspace contained parallel unmerged schema-repair heads:
  - `20260330_0075_competition_discovery_perf_indexes`
  - `20260330_0076_regen_tracking_schema_repair`
- without a merge revision, `ensure_database_schema_current(...)` failed before startup with an Alembic multiple-head error

Promotion flow used:

1. copied the stale shipped `gte_backend.db` to a dry-run upgrade database
2. upgraded the dry-run copy successfully to `20260330_0077_merge_runtime_schema_heads`
3. promoted the verified upgraded copy back onto `gte_backend.db`
4. copied the repaired database to `.codex_tmp/gte_backend_after_probe.db` for disposable runtime proof traffic

Primary runtime startup smoke after promotion:

- booted `gte_backend.db` with migration checks enabled
- `GET /ready` -> `200 {"status":"ready","checks":{"database":{"status":"ok"},"schema":{"status":"ok"}}}`

Primary repaired database state after promotion:

- current revision: `20260330_0077_merge_runtime_schema_heads`
- `wallets`: `18`
- `viral_leaderboard_entries`: `0`
- `season_pass_seasons`: `0`
- `gtex_jackpot_rounds`: `0`
- `leaderboard_seasons`: `0` before runtime probe, then auto-created during season route proof on the disposable probe copy
- `national_regen_seeds`: `0`
- `player_share_markets`: `150`
- `player_share_events`: `150`

## Probe Harness

- repaired proof database copy: `.codex_tmp/gte_backend_after_probe.db`
- isolated config copy: `.codex_tmp/runtime_probe_config_auth_schema`
- probe artifact: `.codex_tmp/auth_schema_runtime_probe_after.json`
- runtime mode for probe isolation:
  - migration check disabled because the probe DB copy was already upgraded
  - startup seeding disabled
  - auth code was the current workspace runtime path

## Before / After Probe Results

| Lane | Before | After rerun on March 30, 2026 | Current state |
| --- | --- | --- | --- |
| Login | source-truth timeout at `~20s` for both `/auth/register` and `/auth/login` | `/auth/register` -> `201` in `12969.39ms`; `/auth/login` -> `200` in `7747.39ms`; `/api/auth/me` -> `200` in `2038.64ms` | Primary auth blocker repaired |
| Home | source-truth blocked by competition timeouts and `/regen-universe/tracking` -> `500` | `/api/competitions` -> `200` in `292.75ms`; `/hosted-competitions` -> `200` in `18.81ms`; `/players/real-universe?limit=3` -> `200` in `225.50ms`; `/api/transfer-market/listings` -> `200` in `22.89ms`; `/daily-challenges` -> `200` in `24.90ms`; `/regen-universe/tracking` -> `200` in `40.98ms`; first cold `/streamer-tournaments` -> `200` in `106595.28ms` | Auth/schema blockers cleared, but Home is still not runtime-proven on a cold boot because the first streamer discovery call exceeds the old `20s` proof budget |
| World | source-truth blocked by `/regen-universe/tracking` -> `500` | `/regen-universe/rising-stars` -> `200`; `/scouting-feed` -> `200`; `/seasons` -> `200`; `/awards` -> `200`; `/hall-of-fame` -> `200`; `/federations` -> `200`; `/tracking` -> `200` | World schema blocker repaired |
| Competitions | source-truth blocked by competition timeouts and missing leaderboard season schema | warm rerun results: `/api/competitions` -> `200` in `20.30ms`; `/hosted-competitions` -> `200` in `10.41ms`; `/streamer-tournaments` -> `200` in `18.00ms`; `/leaderboard/global?limit=12` -> `200` in `88.24ms`; `/season/current` -> `200` in `15.90ms`; `/season/history?limit=4` -> `200` in `16.54ms` | Competition and season schema blocker repaired; cold streamer discovery still needs follow-up performance work |
| Market | source-truth blocked by missing player-share tables and missing wallets | `/players/{player_id}/shares/market` -> `200` in `20.23ms`; `/shares/events` -> `200` in `23.30ms`; `/api/wallets/summary` -> `200` in `54.73ms`; `/api/wallets/overview` -> `200` in `252.06ms`; `/policies/me/compliance` -> `200` in `140.57ms` | Market schema blocker repaired |
| Tasks | source-truth blocked by auth and disabled challenge publication | `/daily-challenges` -> `200`; `/daily-challenges/me` -> `200`; `/daily-challenges/daily-login/claim` -> `500` | Auth/schema blocker cleared, but claim persistence is still blocked by reward funding, not by auth or missing tables |
| Clips | source-truth blocked because auth could not produce a session and feed endpoints returned `401` | `/feed/for-you` -> `401 {"detail":"Missing identity context"}`; `/feed/following` -> `401 {"detail":"Missing identity context"}` even with a valid bearer token | Auth follow-on remains |
| Matches | source-truth blocked by unauthenticated `/api/broadcast/home` | `/api/broadcast/home` -> `200` in `31.29ms` | Matches overview auth blocker repaired |
| Admin Access | source-truth not verifiable because auth hung | super-admin `/auth/login` -> `200`; `/api/admin/god-mode/bootstrap` -> `200`; scoped-admin creation -> `201`; scoped-admin `/auth/login` -> `200`; scoped-admin `/internal/ingestion/real-players/status?provider_name=football_data` -> `200` | Auth blocker cleared and runtime admin sessions were proven, but two follow-ons remain: super-admin catalog routes returned `403` for missing `manage_manager_catalog`, and scoped-admin God Mode bootstrap returned `500` instead of a clean permission denial |

## Probe Details Worth Calling Out

### Auth

- Auth no longer hangs behind lazy module hydration.
- During the successful rerun, the middleware logged `lazy_hydration_bypassed=true` for `/auth/register` and `/auth/login`.
- Register and login are still slow because password hashing and verification dominate the request, but they complete under the old `20s` timeout threshold.

### Tasks Claim Failure

- The rerun reached a real claim path.
- The failure was no longer auth or schema.
- The server raised `RewardEngineError("Promo pool balance is lower than the reward amount.")`.

### Clips Follow-On

- A valid bearer token was accepted for `/api/auth/me`.
- The clips feed still returned `401` because the feed layer requires an identity context beyond bare login.
- This matches the requested classification: Clips is no longer a guest-route bug, but it is still blocked by an auth/identity follow-on.

### Admin Follow-Ons

- Super-admin God Mode bootstrap is live.
- Super-admin catalog/status endpoints currently return `403 Permission manage_manager_catalog is required for this action.`
- Scoped-admin catalog access works when `manage_manager_catalog` is explicitly granted.
- Scoped-admin God Mode bootstrap currently raises an unhandled `PermissionDeniedError` and surfaces as `500`; it should return a clean forbidden response in a follow-up pass.

## Final State After This Pass

Primary blockers repaired in this pass:

- auth/login/register no longer hang
- shipped runtime database is no longer schema-incomplete for the report-listed missing relations
- world tracking, player-share market/events, wallet summary/overview, leaderboard season routes, and matches overview all moved from auth/schema failure to live responses

Remaining follow-ons observed during rerun, intentionally left out of this pass:

- cold `/streamer-tournaments` discovery is still too slow for the old `20s` runtime proof budget
- daily-challenge claim fails because the promo pool is unfunded
- clips feed still rejects the session with `Missing identity context`
- super-admin catalog import/status access is still permission-blocked
- scoped-admin God Mode denial still surfaces as `500` instead of `403`
