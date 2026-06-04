# CODEX Runtime Proof Report

Verified on March 29, 2026 against the shipped local runtime and the provided external Render Postgres.

- Backend boot command used for proof: `python -m uvicorn backend.app.asgi:app --host 127.0.0.1 --port 8000`
- Base URL under test: `http://127.0.0.1:8000`
- Boot proof:
  - `GET /health` -> `200 {"status":"ok"}`
  - `GET /ready` -> `200 {"status":"ready","checks":{"database":{"status":"ok","detail":null}}}`
  - `GET /version` -> `200 {"app_name":"Global Talent Exchange API","environment":"production","api_version":"0.1.0","phase_marker":"phase-8"}`
- Raw evidence artifacts:
  - `.codex_tmp/runtime_probe_detailed.json`
  - `.codex_tmp/runtime_proof_server.log`
  - `.codex_tmp/runtime_proof_followup_wait.log`

## Global runtime facts observed

- The configured database is schema-incomplete for this shipped runtime. Confirmed missing relations during startup or feature calls:
  - `wallets`
  - `viral_leaderboard_entries`
  - `season_pass_seasons`
  - `gtex_jackpot_rounds`
  - `leaderboard_seasons`
  - `national_regen_seeds`
  - `player_share_markets`
  - `player_share_events`
- Real-player import data does exist in the configured database:
  - `real_player_profiles` count: `50`
  - `ingestion_players` count: `50`
  - `real_player_import_batches` count: `3`
- Public real-player discovery was not stable immediately after readiness. An immediate post-ready probe timed out once, but after a `120s` post-ready soak the same endpoint returned `200` with `total: 50`.

## Item-by-item proof

### 1. Login/signup flow

- Status: `VERIFIED BLOCKED`
- Route/screen: `/profile/login` -> `ProfileLoginScreen`; `/profile/signup` -> `ProfileSignupScreen`
- Backend endpoint(s): `POST /auth/login`, `POST /auth/register`
- Blocking reason: both submit actions timed out at `~20s` on a clean boot. No completed uvicorn access log entries were emitted for either request in the proof run.
- Blocker type: `auth`

### 2. Home real data load

- Status: `VERIFIED BLOCKED`
- Route/screen: `/home` -> `HomeScreen`
- Backend endpoint(s) exercised by the shipped screen: `GET /api/competitions`, `GET /hosted-competitions`, `GET /streamer-tournaments`, `GET /players/real-universe`, `GET /api/transfer-market/listings`, `GET /daily-challenges`, world endpoints under `/regen-universe/*` and `/federations`
- Blocking reason: `HomeScreen` aggregates `competitionHubProvider`, `marketDashboardProvider`, `worldAggregateProvider`, and `liveTasksProvider`. In the proof run:
  - `GET /api/competitions` timed out
  - `GET /hosted-competitions` timed out
  - `GET /streamer-tournaments` timed out
  - `GET /regen-universe/tracking` returned `500 Internal Server Error`
  - Any one of those provider failures is enough for the shipped home route to enter its blocked state
- Blocker type: `environment`

### 3. World real data load

- Status: `VERIFIED BLOCKED`
- Route/screen: `/world` -> `WorldScreen`
- Backend endpoint(s): `GET /regen-universe/rising-stars`, `GET /regen-universe/scouting-feed`, `GET /regen-universe/seasons`, `GET /regen-universe/awards`, `GET /regen-universe/hall-of-fame`, `GET /federations`, `GET /regen-universe/tracking`, plus competition-family discovery endpoints
- Blocking reason:
  - Partial world endpoints did respond:
    - `GET /regen-universe/rising-stars` -> `200 {"entries":[]}`
    - `GET /regen-universe/scouting-feed` -> `200 {"items":[]}`
    - `GET /regen-universe/seasons` -> `200 []`
    - `GET /regen-universe/awards` -> `200 []`
    - `GET /regen-universe/hall-of-fame` -> `200 {"entries":[]}`
    - `GET /federations` -> `200 []`
  - But the shipped `WorldScreen` also requires:
    - `GET /regen-universe/tracking` -> `500`
    - competition-family discovery -> blocked by competition timeouts
  - Server log showed `/regen-universe/tracking` failing because `national_regen_seeds` does not exist.
- Blocker type: `data`

### 4. GTEX-hosted competitions

- Status: `VERIFIED BLOCKED`
- Route/screen: `/competitions/gtex` -> `LiveCompetitionsHubScreen`
- Backend endpoint(s): `GET /api/competitions`
- Blocking reason: `GET /api/competitions` timed out at `~20s` in the proof run, so the GTEX family list could not be proven live.
- Blocker type: `environment`

### 5. User-hosted football competitions

- Status: `VERIFIED BLOCKED`
- Route/screen: `/competitions/hosted` -> `LiveCompetitionsHubScreen`
- Backend endpoint(s): `GET /hosted-competitions`
- Blocking reason: `GET /hosted-competitions` timed out at `~20s` in the proof run, so hosted competition discovery could not complete.
- Blocker type: `environment`

### 6. Streamer/e-game tournaments

- Status: `VERIFIED BLOCKED`
- Route/screen: `/competitions/streamer` -> `LiveCompetitionsHubScreen`; `/competitions/streamer/engine` -> `StreamerTournamentEngineRouteScreen`
- Backend endpoint(s): `GET /streamer-tournaments`, `GET /leaderboard/global?limit=12`, `GET /season/current`, `GET /season/history?limit=4`
- Blocking reason:
  - `GET /streamer-tournaments` timed out at `~20s`
  - `GET /leaderboard/global?limit=12` timed out at `~20s`
  - `GET /season/current` timed out at `~20s`
  - `GET /season/history?limit=4` -> `500 Internal Server Error`
  - Server log showed two concrete backend defects during this lane:
    - `streamer_tournaments.status IN ('PUBLISHED','LIVE','COMPLETED')` failed with `invalid input value for enum streamertournamentstatus: "PUBLISHED"`
    - leaderboard routes failed because `leaderboard_seasons` does not exist
- Blocker type: `data`

### 7. Player shares market

- Status: `VERIFIED BLOCKED`
- Route/screen: `/market` -> `TransferMarketScreen` player shares section
- Backend endpoint(s): `GET /players/{player_id}/shares/market`, `POST /players/{player_id}/shares/buy`
- Blocking reason:
  - For three real players returned by discovery, all share-market lookups failed:
    - `GET /players/590ea6c0-2dde-4067-bf82-b920f98335ed/shares/market` -> `500`
    - `GET /players/716ecb87-c6fd-41cd-90a1-6fc3a836c67b/shares/market` -> `500`
    - `GET /players/c75d78d2-f8f2-4896-acee-cfbbe22cd524/shares/market` -> `500`
  - Server log showed the exact cause: relation `player_share_markets` does not exist.
- Blocker type: `data`

### 8. Transfer listings market

- Status: `VERIFIED LIVE`
- Route/screen: `/market` -> `TransferMarketScreen` transfer listings section
- Backend endpoint(s): `GET /api/transfer-market/listings`, `GET /api/transfer-market/listings?player_id={player_id}`
- Exact evidence observed:
  - `GET /api/transfer-market/listings` -> `200` in `687ms` with body `[]`
  - `GET /api/transfer-market/listings?player_id=590ea6c0-2dde-4067-bf82-b920f98335ed` -> `200` with body `[]`
  - `GET /api/transfer-market/listings?player_id=c75d78d2-f8f2-4896-acee-cfbbe22cd524` -> `200` with body `[]`
  - Uvicorn access log recorded `200` responses for these listing calls
- Note: this lane is live but empty. The overall `/market` dashboard is still degraded by the blocked player-share subcalls above.

### 9. Real-player discovery after import

- Status: `VERIFIED LIVE`
- Route/screen: `/market` -> `TransferMarketScreen` search field and player detail sheet
- Backend endpoint(s): `GET /players/real-universe?limit=3`, `GET /players/real-universe/search?search=Casemiro&limit=12`, `GET /players/real-universe/search?search=Luka%20Modri%C4%87&limit=12`, `GET /players/real-universe/search?search=Manuel%20Neuer&limit=12`, `GET /players/real-universe/{player_id}`
- Exact evidence observed:
  - After a `120s` post-ready soak, `GET /players/real-universe?limit=3` -> `200` in `17649ms`
  - The payload reported `total: 50` and returned real imported players including:
    - `590ea6c0-2dde-4067-bf82-b920f98335ed` -> `Casemiro`
    - `716ecb87-c6fd-41cd-90a1-6fc3a836c67b` -> `Luka Modric`
    - `c75d78d2-f8f2-4896-acee-cfbbe22cd524` -> `Manuel Neuer`
  - Search returned exact matches:
    - `GET /players/real-universe/search?search=Casemiro&limit=12` -> `200`, `total: 1`
    - `GET /players/real-universe/search?search=Luka%20Modri%C4%87&limit=12` -> `200`, `total: 1`
    - `GET /players/real-universe/search?search=Manuel%20Neuer&limit=12` -> `200`, `total: 1`
  - Detail calls returned live imported metadata:
    - `GET /players/real-universe/590ea6c0-2dde-4067-bf82-b920f98335ed` -> `200`
    - Evidence in payload: `is_verified_real_player: true`, `source_name: "transfermarkt_2nd_zip"`, `ingestion_batch_id: "2nd-zip-8963e625c0c0-all:publish:190-2347:7e3d7a93"`
    - Similar `200` detail responses were observed for Luka Modric and Manuel Neuer

### 10. Tradable real-player visibility

- Status: `VERIFIED BLOCKED`
- Route/screen: `/market` -> `TransferMarketScreen` tradability state inside the player shares section
- Backend endpoint(s): `GET /players/{player_id}/shares/market`, `GET /players/{player_id}/shares/events`
- Blocking reason:
  - Tradability in the shipped market route is derived from `/players/{player_id}/shares/market`
  - For all sampled real players, that endpoint returned `500`
  - `/players/{player_id}/shares/events` also returned `500`
  - Server log showed the exact missing relations:
    - `player_share_markets`
    - `player_share_events`
- Blocker type: `data`

### 11. Wallet/compliance state

- Status: `VERIFIED BLOCKED`
- Route/screen: `/market` -> `TransferMarketScreen` wallet and compliance section
- Backend endpoint(s) used by the shipped screen after auth: `GET /api/wallets/summary`, `GET /api/wallets/overview`, `GET /policies/me/compliance`
- Blocking reason:
  - The runtime could not establish an authenticated session because `/auth/login` and `/auth/register` both hung
  - Independently, startup failed against the missing `wallets` relation before any wallet feature proof was possible
  - Exact startup error observed: `relation "wallets" does not exist`
- Blocker type: `data`

### 12. Tasks list and claim persistence

- Status: `VERIFIED BLOCKED`
- Route/screen: `/tasks` -> `TasksScreen`
- Backend endpoint(s): `GET /daily-challenges`, `GET /daily-challenges/me`, `POST /daily-challenges/{challengeKey}/claim`
- Blocking reason:
  - `GET /daily-challenges` did return live data, but the data itself disabled the feature:
    - `200 {"feature_enabled": false, "challenges": []}`
  - No challenge keys were published, so there was nothing claimable to persist
  - Because auth was also blocked, `/daily-challenges/me` and a real `POST /daily-challenges/{challengeKey}/claim` could not be exercised
- Blocker type: `config`

### 13. Clips feed load

- Status: `VERIFIED BLOCKED`
- Route/screen: `/clips` -> `ClipsBlockedScreen` in the current runtime session
- Backend endpoint(s): `GET /feed/for-you?limit=10&refresh=true`, `GET /feed/following?limit=10&refresh=true`
- Blocking reason:
  - Both feed endpoints returned `401`
  - Exact response detail: `Authentication credentials were not provided.`
  - The shipped router only opens `ViralFeedScreen` when a real authenticated session exists; current auth flow could not produce one
- Blocker type: `auth`

### 14. Matches overview

- Status: `VERIFIED BLOCKED`
- Route/screen: `/matches` -> `MatchScreen`
- Backend endpoint(s): `GET /api/broadcast/home`
- Blocking reason:
  - Direct probe: `GET /api/broadcast/home` -> `401`
  - Exact response detail: `Authentication credentials were not provided.`
  - The shipped `MatchScreen` is intentionally blocked when unauthenticated, and current auth endpoints never completed
- Blocker type: `auth`

### 15. 2D viewer

- Status: `NOT VERIFIABLE IN CURRENT ENVIRONMENT`
- Route/screen: `/matches/viewer/:matchKey` -> `MatchViewerRouteScreen`
- Backend endpoint(s) required by the shipped route: `GET /api/match-viewer/{matchKey}`, `GET /api/match-viewer/{matchKey}/session`
- Exact blocking reason:
  - A real current `matchKey` could not be obtained because `GET /api/broadcast/home` returned `401`
  - Direct DB check found `0` `competition_matches` rows whose `metadata_json` contained `match_viewer`, so there was no fallback live viewer key to use for proof
- Blocker type: `auth`

### 16. Pseudo-3D/broadcast viewer

- Status: `NOT VERIFIABLE IN CURRENT ENVIRONMENT`
- Route/screen: `/matches/broadcast/:matchKey` -> `MatchBroadcastScreen`
- Backend endpoint(s) required by the shipped route: `GET /api/match-viewer/{matchKey}`, `GET /api/match-viewer/{matchKey}/session`
- Exact blocking reason:
  - Same blocker as item 15: no authenticated broadcast overview, no verified live `matchKey`, no DB fallback key
- Blocker type: `auth`

### 17. Flutter 3D viewer

- Status: `NOT VERIFIABLE IN CURRENT ENVIRONMENT`
- Route/screen: `/matches/3d/:matchKey` -> `LegacyMatchRuntimeBlockedScreen`
- Backend endpoint(s) required by the shipped route: `GET /api/match-viewer/{matchKey}`, `GET /api/match-viewer/{matchKey}/session`
- Exact blocking reason:
  - Same blocker as items 15 and 16: no authenticated broadcast overview, no verified live `matchKey`, no DB fallback key
  - This prevented proof of the Flutter fallback path under a real active match
- Blocker type: `auth`

### 18. Native 3D blocked truth

- Status: `VERIFIED BLOCKED`
- Route/screen: `/internal/dev/blocked-match-runtime` -> `BlockedMatchRuntimeScreen`
- Blocking reason:
  - The shipped blocked route explicitly states that the active shell does not mount a verified runtime bridge
  - The bridge code checks channel names `match_3d` and `match_3d/events`
  - In this shipped runtime, native 3D remains intentionally blocked instead of being mislabeled as the Flutter 3D surface
- Blocker type: `code`

### 19. Profile admin visibility

- Status: `NOT VERIFIABLE IN CURRENT ENVIRONMENT`
- Route/screen: `/profile/admin` -> `ProfileAdminScreen`
- Backend endpoint(s) that the shipped screen would need once an admin session exists: `GET /internal/ingestion/providers/football_data/health`, `GET /internal/ingestion/real-players/status?provider_name=football_data`
- Exact blocking reason:
  - A real admin session could not be established because `/auth/login` and `/auth/register` both hung
  - Guest probes to the protected admin endpoints returned `401 Authentication credentials were not provided.`
  - Without a real admin session, admin-surface visibility for an entitled user could not be proven
- Blocker type: `auth`

### 20. God Mode visibility and access

- Status: `NOT VERIFIABLE IN CURRENT ENVIRONMENT`
- Route/screen: `/profile/admin/god-mode` -> `ProfileGodModeScreen`
- Backend endpoint(s): `GET /api/admin/god-mode/bootstrap`
- Exact blocking reason:
  - Guest probe returned `401 Authentication credentials were not provided.`
  - A real admin or super-admin session could not be established because the shipped auth flow hung
  - That means positive God Mode visibility/access for an entitled user could not be proven in this environment
- Blocker type: `auth`

### 21. Delegated admin limited-permission behavior in practice

- Status: `NOT VERIFIABLE IN CURRENT ENVIRONMENT`
- Route/screen: `/profile/admin` -> `ProfileAdminScreen`
- Backend endpoint(s) that would matter for scoped behavior: admin import endpoints, share-issuance endpoints, and God Mode bootstrap
- Exact blocking reason:
  - No delegated-admin session with scoped permissions could be created because `/auth/login` and `/auth/register` hung
  - The current proof run therefore could not exercise the shipped permission gating in practice
  - Guest probes only proved that protected admin routes return `401`; they did not prove scoped-admin behavior
- Blocker type: `auth`

## Final classification count

- `VERIFIED LIVE`: `2`
- `VERIFIED BLOCKED`: `13`
- `NOT VERIFIABLE IN CURRENT ENVIRONMENT`: `6`
