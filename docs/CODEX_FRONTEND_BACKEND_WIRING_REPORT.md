# CODEX Frontend/Backend Wiring Report

## Scope

- Canonical shipped runtime remains:
  - `frontend/lib/main.dart`
  - `frontend/lib/navigation/app_router.dart`
- Legacy API-heavy code was reused as bridge material inside the active Riverpod shell.
- Silent fixture fallback was removed from the active-shell wiring by forcing critical clients to `live` mode unless the app is explicitly launched in fixture mode.
- Active shipped path now treats missing backend/auth/config state as `BLOCKED`, not as demo success.

## Runtime Status Summary

- `DEMO` shipped surfaces on the active path: `0`
- Removed as production truth:
  - `frontend/lib/shared/providers/regen_provider.dart`
  - `frontend/lib/shared/providers/exchange_hub_provider.dart`
  - `frontend/lib/shared/providers/match_provider.dart`
- New shared truth-state primitives:
  - `frontend/lib/shared/models/data_source_status.dart`
  - `frontend/lib/shared/widgets/data_source_badge.dart`
  - richer persisted active session in `frontend/lib/shared/models/auth_session.dart`

## ACTIVE Shipped Screens

| Screen / Route | Status | Driving Providers / Repositories | Backend Endpoint Mapping | Notes / Blockers |
| --- | --- | --- | --- | --- |
| `Home` | `LIVE` | `profileDataProvider`, `competitionHubProvider`, `marketDashboardProvider`, `worldAggregateProvider`, `liveTasksProvider` | Aggregates `/api/auth/me`, `/users/me`, `/users/me/profile`, `/clubs/{club_id}`, `/api/competitions`, `/api/hosted-competitions`, `/api/streamer-tournaments`, `/players/real-universe`, `/players/{player_id}/shares/market`, `/players/me/shares/holdings`, `/api/transfer-market/listings`, `/wallets/summary`, `/wallets/overview`, compliance/policy endpoints, `/regen-universe/*`, `/api/federations`, `/api/daily-challenges`, `/api/daily-challenges/me` | Summary surface only; shows blocked child-provider failures honestly. |
| `Matches` | `LIVE` | honest route hub in `frontend/lib/features/match/match_screen.dart` | No direct fetch; routes into `Spectate` and `Simulate` | No mock match cards remain. |
| `Matches > Spectate` | `LIVE` | `frontend/lib/features/match/match_spectate_screen.dart` | `/api/matches/{match_key}/spectate`, `/api/match-viewer/{match_key}`, `/match-viewer/{match_key}`, `/api/match-viewer/{match_key}/session`, `/match-viewer/{match_key}/session` | Opens existing 2D/Broadcast+/auto-render viewer only after a real viewer/session payload resolves. Invalid match keys or missing viewer contracts surface as `BLOCKED`. |
| `Matches > Simulate` | `BLOCKED` | `frontend/lib/features/match/match_simulate_screen.dart` | None; local simulation only | Intentionally labeled local simulation. Not treated as a live backend feed. |
| `Market` | `LIVE` | `marketDashboardProvider`, `playerShareDetailProvider` | `/players/real-universe`, `/players/real-universe/search`, `/players/real-universe/{player_id}`, `/players/{player_id}/shares/market`, `/players/{player_id}/shares/events`, `/players/me/shares/holdings`, `/players/{player_id}/shares/buy`, `/api/transfer-market/listings`, `/api/transfer-market/listings/{listing_id}/bids`, `/api/transfer-market/watchlist`, `/wallets/summary`, `/wallets/overview`, wallet/compliance policy endpoints | Split into `Player Shares` and `Transfer Listings`. Tradable state only appears when a live market/listing exists. Transfer actions are blocked without verified club context. |
| `World` | `LIVE` | `worldAggregateProvider` | `/regen-universe/rising-stars`, `/regen-universe/scouting-feed`, `/regen-universe/seasons`, `/regen-universe/awards`, `/regen-universe/hall-of-fame`, `/regen-universe/tracking`, `/api/federations`, plus competition family summaries from `/api/competitions`, `/api/hosted-competitions`, `/api/streamer-tournaments` | Summary/discovery only. Federation join is intentionally disabled until a club-backed mutation flow is wired. |
| `Competitions` | `LIVE` | `competitionHubProvider` | `/api/competitions`, `/api/hosted-competitions`, `/api/streamer-tournaments` | Families remain distinct: GTEX-hosted football, user-hosted football, creator e-game tournaments. |
| `Competitions > GTEX Detail` | `LIVE` | `gtexCompetitionDetailProvider`, `CompetitionApi` | `/api/competitions/{competition_id}`, `/api/competitions/{competition_id}/financials`, `/api/competitions/{competition_id}/standings`, `/api/competitions/{competition_id}/fixtures`, `/api/competitions/{competition_id}/join`, `/api/competitions/{competition_id}/publish`, `/api/competitions/{competition_id}/launch` | Publish/launch require authorized roles; backend errors are surfaced directly. |
| `Competitions > Hosted Detail` | `LIVE` | `hostedCompetitionDetailProvider`, `HostedCompetitionApi` | `/api/hosted-competitions/{competition_id}`, `/api/hosted-competitions/{competition_id}/finance`, `/api/hosted-competitions/{competition_id}/standings`, `/api/hosted-competitions/{competition_id}/join`, `/api/hosted-competitions/{competition_id}/launch` | Launch/join remain backend-authorized. |
| `Competitions > Streamer Detail` | `LIVE` | `streamerTournamentDetailProvider`, `StreamerTournamentEngineRepository` | `/api/streamer-tournaments/{tournament_id}`, `/season/current`, `/api/streamer-tournaments/{tournament_id}/join`, `/api/streamer-tournaments/{tournament_id}/publish` | Role-based publish restrictions remain backend-enforced. |
| `Profile` | `LIVE` | `profileDataProvider`, session/auth providers | `/api/auth/me`, `/users/me`, `/users/me/profile`, `/users/{user_id}/followers`, `/users/{user_id}/following`, `/clubs/{club_id}` | Guest path is honest and routes into sign-in / sign-up instead of faking protected data. |
| `Profile > Login` | `LIVE` | `exchangeApiClientProvider`, `appSessionControllerProvider` | active auth/login endpoint via `GteApiRepository.login(...)` | Persists enriched session shape into the active shell. |
| `Profile > Signup` | `LIVE` | `exchangeApiClientProvider`, `appSessionControllerProvider` | active auth/register endpoint via `GteApiRepository.register(...)` | Persists enriched session shape into the active shell after registration. |
| `Profile > Admin` | `BLOCKED` | `adminImportOverviewProvider` with strict `isAdmin` gating | `/internal/ingestion/providers/{provider_name}/health`, `/internal/ingestion/real-players/status`, `/internal/ingestion/real-players/batches`, `/internal/ingestion/real-players/batches/{batch_id}`, `/internal/ingestion/real-players/batches/{batch_id}/issues`, `/internal/ingestion/real-players/batches/{batch_id}/valuation-status`, `/internal/ingestion/real-players/import`, `/internal/ingestion/real-players/batches/{batch_id}/resume`, `/players/{player_id}/shares/issue` | Fully blocked for signed-out and non-admin users. Also blocked if ingestion provider config, API keys, or backend admin access are missing. |
| `Tasks` | `LIVE` | `liveTasksProvider` | `/api/daily-challenges`, `/api/daily-challenges/me`, `/api/daily-challenges/{challenge_key}/claim` | Fake season-pass/task simulator removed from shipped path. |
| `Clips` | `LIVE` | `ViralFeedApiRepository.standard(...)` | `/feed/for-you`, `/feed/following`, `/feed/trending`, `/feed/for-you/refresh` | Already live-backed; now remains part of the active-shell audit. |

## Creator / Media Ownership Note

The shipped shell does not currently present a primary-nav creator hub, but the live creator-related clients already depend on multiple backend owners. That split is real in the current checkout and should be treated as an explicit contract, not as alias drift:

- `CreatorApi` profile/referral surfaces use `/api/creators/...` for creator identity, summary, competitions, finance, and public profile lookup. The only bare legacy creator aliases still mounted are `/creators/me/insights` and `/creators/me/copilot/analyze`; there is no generic `/creators/{handle}` fallback contract.
- `CreatorApplicationApi` and creator share-market repositories use `/api/creator/...` and `/api/admin/creator/...` for onboarding, verification, application, and fan-share-market operations.
- Creator clip earnings and creator-league monetization use `/api/media-engine/...` and `/api/admin/media-engine/...`.
- Public creator links and public media asset links remain intentionally non-API:
  - `/community/creator/{handle}`
  - `/media-engine/downloads/{token}`

This means the creator product is currently a composed surface spanning at least three backend owners plus two public web surfaces. It should not be flattened into a single namespace unless backend ownership is intentionally redesigned.

Recommended migration posture:

- short term: keep the split explicit and enforce it with transport tests
- medium term: either formalize the split as permanent product architecture or rename the families into clearer product-facing domains with compatibility aliases
- do not combine authenticated API renames with public web/link renames in the same rollout

## Core Business Questions

### Are GTEX-hosted competitions live in the app?

Yes. They are now visible from the active shell through the dedicated competitions hub and detail routes backed by `/api/competitions`.

### Are user-hosted competitions live in the app?

Yes. They are now visible from the active shell through `/api/hosted-competitions`, with detail, standings, finance, join, and launch routed into dedicated screens.

### Is the regen universe actually live in the app?

Yes. The active `World` tab no longer reads hardcoded regen data and now loads live regen/history/federation payloads.

### Can imported real-life football players actually appear in the app?

Yes, if import succeeds in the backend and the player is returned by `/players/real-universe` or related discovery endpoints. The active `Market` tab now reads those endpoints directly.

### Are imported players actually tradable?

Conditionally. A player is shown as tradable only when a live share market exists at `/players/{player_id}/shares/market` or when a live transfer listing exists in `/api/transfer-market/listings`. Import alone is not treated as tradability.

### Which visible surfaces are still demo-only?

None on the shipped active path. The intentionally local `Matches > Simulate` route is marked `BLOCKED` as a non-live simulation flow, not as `DEMO`.

## Session / Context Wiring

- Active session is now persisted with:
  - `accessToken`
  - `sessionId`
  - `userId`
  - `role`
  - `permissions`
  - `clubId`
  - `clubName`
  - raw backend JSON
- Active-shell providers now expose:
  - API base URL
  - backend mode
  - authenticated API client
  - admin flag
  - club context
  - data-source status badges

## Key Integrity Changes

- Silent mock/demo truth removed from:
  - market
  - world
  - matches
  - tasks
  - home summaries
- Player share trading and transfer listings are now distinct UI concepts.
- Admin import tooling is strictly gated under `Profile > Admin`.
- `Matches` now separates:
  - `Spectate`: live backend viewer path
  - `Simulate`: explicit local simulation path

## Remaining Risks And Real Blockers

- Real-player import still depends on backend configuration:
  - `SPORTMONKS_BASE_URL=https://api.sportmonks.com/v3/football`
  - `SPORTMONKS_API_TOKEN`
  - `GTE_REAL_PLAYER_IMPORT_PROVIDER=sportmonks` for the primary import lane
  - optional secondary fallback: `API_SPORTS_BASE_URL=https://v3.football.api-sports.io`, `API_SPORTS_API_KEY`, and `GTE_REAL_PLAYER_IMPORT_PROVIDER=api_sports`
  - valid admin credentials
- Real-player trading still depends on environment state:
  - imported player must exist in discovery endpoints
  - share market must be issued or transfer listing must exist
  - user wallet/compliance must permit purchase
- Match spectating still depends on a valid match key and a live viewer/session payload from the backend.
- Federation membership mutation is still intentionally disabled from the `World` summary because the active session does not yet guarantee a safe club-backed federation action flow.
- Transfer-listing actions depend on verified club context in the active session.
- Creator ownership remains split across `/api/creators/...`, `/api/creator/...`, and `/api/media-engine/...`. Current transport tests lock that split down, but the product still needs a long-term naming/ownership decision.

## Next Steps

1. Validate with real admin and non-admin accounts against the target backend.
2. Configure ingestion provider secrets and verify an import batch end-to-end.
3. Confirm at least one imported player has an issued share market and can be purchased from the live `Market` tab.
4. Decide whether creator/backend ownership stays permanently split or is renamed into clearer product-facing families without breaking `/community/creator/...` and `/media-engine/downloads/...`.
4. Confirm a real `match_key` that resolves both viewer and session payloads for `Matches > Spectate`.
5. Replace deprecated `RadioListTile` usage in `Profile > Admin` with Flutter's newer radio-group pattern when the project upgrades that UI path.
