# GTEX P6 Production Gap Backlog

This file is the production-gap execution addendum for `P6` in `GTEX_TASKS.md`.

It does not replace phase gating. It translates the verified frontend, backend, payments, competition, and admin gaps into an execution order that is honest about missing inputs, verification, and blockers.

## Non-Negotiable Rules

- Do not use fake, placeholder, guessed, or default production values for URLs, secrets, webhook targets, admin credentials, or release defines.
- If a task requires a real environment value and that value has not been provided by the user or ops, mark the task `BLOCKED_PENDING_INPUT`.
- Do not count fixture-only or mock-only tests as production proof.
- Every completed task must include repo verification and, where relevant, staging or production-like verification.
- If a task cannot be verified end to end, say so explicitly and keep it open.

## Inputs Received On 2026-04-23

These values and decisions were provided by the user and can now be treated as real project inputs unless later changed explicitly.

- Staging API base URL: `https://gtex-api-69rq.onrender.com`
- Production API base URL: `https://gtex-api.onrender.com`
- Non-canonical production backend hostname received earlier:
  - `https://api.gtex.onrender.com`
  - Treat this as superseded for production config unless the user explicitly reactivates it later.
- Web frontend base URL: `https://gtex-web.onrender.com`
- KoraPay live credentials were provided out-of-band in the chat.
  - Do not commit live secrets, public keys, or encryption keys into tracked repo files.
  - Use deployment secret injection or a secret manager only.
- KoraPay callback behavior confirmed by the user:
  - `redirect_url` is for the user browser, not the server-to-server webhook
  - `notification_url` is for KoraPay's server-to-server callback
  - provided redirect URL: `https://gtex-web.onrender.com/`
  - resolved production notification URL: `https://gtex-api.onrender.com/integrations/payments/korapay/webhook`
  - note: this final URL is derived by applying the user-confirmed canonical production backend hostname to the repo-verified webhook route
  - do not point `GTE_KORAPAY_REDIRECT_URL` at the webhook endpoint
- Bootstrap admin plan provided:
  - `GTE_BOOTSTRAP_ADMIN_ENABLED=true`
  - `GTE_BOOTSTRAP_ADMIN_EMAIL=platform-root@gtex.onrender.com`
  - `GTE_BOOTSTRAP_ADMIN_USERNAME=gtex_root`
  - `GTE_BOOTSTRAP_ADMIN_DISPLAY_NAME=GTEX Root Admin`
  - `GTE_BOOTSTRAP_ADMIN_PASSWORD` must come from vault as a `32+` character random secret
- Treasury operating intent:
  - deposit mode: `automatic` or `hybrid`, with manual deposit fallback available through admin control
  - processor mode: `automatic_gateway`
  - withdrawal mode: `hybrid`, with automatic gateway settlement plus manual fallback
- Competition family decision:
  - both competition families are valid shipped products
  - GTEX competitions are admin-hosted, free-to-join, rule-gated competitions that mirror real-world tournaments and pay withdrawable winnings
  - hosted competitions are user-hosted or admin-hosted, pay-to-host competitions such as fast cup style formats
- Inventory requirement:
  - `5000+` means searchable, buyable, and tradeable
  - purchased and traded players must be usable in both GTEX competitions and user-hosted competitions
  - the same expectation applies to regens, whether pre-seeded or generated later
- Bulk share-market issuance policy provided:
  - platform targets:
    - searchable universe: `>= 5000`
    - active buyable and tradeable share markets: `>= 5000`
    - one active market per player
    - zero manual one-by-one issuance in normal operations
  - eligibility for bulk issuance:
    - published real player
    - `is_tradable = true`
    - canonical display name exists
    - country exists
    - club or competition context exists
    - reference value exists, or fallback valuation is available
    - no existing active market already exists
    - no integrity hold, sanctions flag, or manual block flag exists
  - idempotency outputs required:
    - `created`
    - `updated`
    - `skipped_existing`
    - `skipped_blocked`
    - `failed`
  - cohort issuance rule:
    - issue by import batch, league, country, supply tier, or liquidity band
    - recommended live slice: `250` to `500` players per issuance job
    - always dry-run first, then report, then execute live, then verify
  - initial status rule:
    - default `active`
    - force `paused` when valuation confidence is low
    - force `paused` when liquidity desk funding is missing
    - block or skip when integrity or manual review is required
  - supply matrix:
    - `icon`: total shares `2000`, initial circulating cap `300`, initial MM inventory target `250`
    - `elite`: total shares `1500`, initial circulating cap `220`, initial MM inventory target `180`
    - `core`: total shares `1000`, initial circulating cap `150`, initial MM inventory target `120`
    - `prospect`: total shares `600`, initial circulating cap `80`, initial MM inventory target `80`
    - `discovery`: total shares `300`, initial circulating cap `40`, initial MM inventory target `50`
  - price rule:
    - initialize from the existing reference-value-based pricing path
    - clamp to a safe launch floor and ceiling
    - do not hand-edit prices player by player except for exception cases
  - liquidity rule:
    - every active market must have seeded sell-side liquidity before being marked buyable
    - `initial_liquidity_coin = max(initial_MM_inventory_target x initial_share_price, platform_minimum)`
    - platform minimum liquidity per market: `25 coin`
    - preferred minimum for core and above: `50-150 coin`
  - buy CTA rule:
    - show live buy only when market is active, supply is available, liquidity target is met, the user passes trading checks, and the market is not under integrity hold
  - missing production artifact requested by the user:
    - `backend/config/player_share_issuance.toml`
    - `backend/scripts/issue_player_share_markets.py`

## Remaining Required Inputs Before Certain Tasks Can Close

These are still missing or still need confirmation. Until then, affected tasks are blocked from true completion.

1. Confirm that deployed production config has been updated to use the canonical production backend hostname everywhere it matters.
   - frontend `GTE_API_BASE_URL`
   - KoraPay `GTE_KORAPAY_NOTIFICATION_URL`
   - operator docs and health checks
2. Confirm that the bootstrap admin password is present in vault and injected into the real staging and production environments.

## Repo-Verified Corrections That Must Override Older Notes

- The weaker trading guard is on `backend/app/players/router.py`, not on `backend/app/gtex/router.py`.
- The current KoraPay webhook surface in this repo is `/integrations/payments/korapay/webhook`.
  - Verified in `backend/app/admin_finance/router.py`.
- Render web builds already enforce `GTE_API_BASE_URL` in `ops/render/build-frontend.sh`.
  - Remaining work is to extend that enforcement to every release profile, not to invent it from scratch.
- Hosted competition creation is not absent from the codebase.
  - The remaining gap is parity, canonical routing, and discoverability of the hosted path.

## Execution Order

### 0. Freeze Real Inputs And Product Decisions
Status: `BLOCKED_PENDING_INPUT`

Why this must happen first:
- Several high-risk tasks cannot be closed honestly without real environment values or product decisions.

Required inputs:
- All items listed in `Remaining Required Inputs Before Certain Tasks Can Close`.

Verification:
- Inputs are written into the deployment or release record used by the team.
- No task below is marked complete while still depending on guessed values.

Honest blockers:
- If the user or ops has not provided the values, the affected tasks remain open even if code work is finished.

### 1. Enforce Reliable Live Boot Across All Release Profiles
Priority: `P0`

Files:
- `frontend/lib/app/gte_app_config.dart`
- `frontend/lib/app/gte_bootstrap_failure_app.dart`
- `ops/render/build-frontend.sh`
- `render.yaml`
- any actual mobile or production build scripts and CI workflows that ship Flutter artifacts

Why:
- Live mode is the default frontend mode.
- The app throws when `GTE_API_BASE_URL` is missing.
- Render web builds already enforce the variable, but shipped coverage across all release profiles is not yet proven.

Required inputs:
- Actual release environment base URLs.

Work:
- Keep live mode if that remains the shipped requirement.
- Extend `GTE_API_BASE_URL` enforcement to every release profile that can ship.
- Keep failure copy user-facing and environment-aware instead of developer-only shell text.

Verification:
- Repo verification:
  - Confirm `ops/render/build-frontend.sh` fails fast when `GTE_API_BASE_URL` is missing.
  - Add equivalent checks to all remaining release build entrypoints.
- Runtime verification:
  - Build each shipped artifact with the real environment base URL.
  - Confirm the live shell mounts normally and does not drop into bootstrap failure.

Honest blockers:
- If a release profile does not yet have a real build script or CI path, that profile is not verified and must stay open.

### 2. Enable First Working Admin And Remove The Treasury Rail Lock
Priority: `P0`

Files:
- `backend/app/core/config.py`
- `backend/app/main.py`
- `backend/app/models/treasury.py`
- `backend/app/wallets/router.py`
- admin runtime state and admin UI surfaces that control payment rails

Why:
- `GTE_BOOTSTRAP_ADMIN_ENABLED` is disabled by default.
- `treasury_settings.deposit_mode` defaults to `manual`, which blocks gateway deposits before provider secrets even matter.

Required inputs:
- Real bootstrap admin values.
- Real treasury operating decision for deposits and withdrawals.

Work:
- Make first-admin provisioning explicit for staging and production.
- Remove ambiguity around who is responsible for switching treasury deposit and withdrawal modes.
- Ensure the active production payment rail matches the intended treasury mode.

Verification:
- Repo verification:
  - Confirm bootstrap admin settings are validated when enabled.
  - Confirm wallet overview provider status reflects treasury mode correctly.
- Runtime verification:
  - Authenticate with the real staging admin account.
  - Confirm payment rails are not blocked solely because treasury mode stayed `manual`.

Honest blockers:
- Without real admin bootstrap values, this task cannot be called complete.
- Without an explicit treasury mode decision, payment work remains partially blocked.

### 3. Complete The KoraPay Deployment Contract Using The Correct Webhook Route
Priority: `P0`

Files:
- `backend/.env.example`
- `backend/app/wallets/funding_service.py`
- `backend/app/admin_finance/service.py`
- `backend/app/admin_finance/router.py`
- `ops/k8s/base/secret.example.yaml`
- real deployment manifests and secret injection paths

Why:
- KoraPay initialization and verification exist.
- `.env.example` is missing `GTE_KORAPAY_WEBHOOK_SECRET`.
- The currently verified webhook route is `/integrations/payments/korapay/webhook`.

Required inputs:
- Real KoraPay secret key.
- Real redirect URL.
- Real notification URL.
- Real webhook secret.
- Real public backend URL that KoraPay can reach.

Work:
- Add the missing KoraPay webhook envs to the documented contract.
- Make local, staging, and deployment manifests agree on the same required variables.
- Confirm the public KoraPay dashboard target uses the current repo route.

Verification:
- Repo verification:
  - Run the existing KoraPay webhook tests in `backend/tests/admin_finance/`.
  - Confirm the env contract is consistent between `.env.example` and `ops/k8s/base/secret.example.yaml`.
- Runtime verification:
  - Perform a real staging transaction using the real staging URLs and secrets.
  - Confirm checkout, redirect, webhook delivery, signature verification, and settlement all complete.

Honest blockers:
- Without real KoraPay credentials and public callback URLs, only repo-level verification is possible.
- Repo tests are not enough to claim live KoraPay readiness.

### 4. Lock Player Share Buy And Sell Behind Trading Compliance
Priority: `P0`

Files:
- `backend/app/players/router.py`
- `backend/app/auth/dependencies.py`
- `backend/tests/players/test_player_share_market_routes.py`
- `backend/tests/e2e/test_critical_system_reliability.py`

Why:
- `get_current_trading_user()` already exists with risk and wallet checks.
- Player share buy and sell still depend on `get_current_user()`.

Work:
- Switch `POST /players/{player_id}/shares/buy` to `get_current_trading_user`.
- Switch `POST /players/{player_id}/shares/sell` to `get_current_trading_user`.
- Leave read-only holdings on the weaker read path unless product says otherwise.

Verification:
- Repo verification:
  - Add or update backend tests so authenticated but trading-blocked users fail with the expected status codes.
  - Keep a positive-path test for a verified trading-enabled user.
- Runtime verification:
  - Use real staging accounts only if they exist:
    - one intentionally trading-blocked account
    - one verified trading-enabled account
  - Confirm blocked users cannot place trades and eligible users still can.

Honest blockers:
- If no staging accounts exist with the needed compliance states, runtime verification stays blocked.

### 5. Replace The Transfer-Market 12-Result Peek With Real Paged Discovery
Priority: `P0`

Files:
- `frontend/lib/features/transfer_market/live_market_provider.dart`
- `frontend/lib/features/transfer_market/transfer_market_screen.dart`
- `frontend/lib/data/player_service.dart`
- `frontend/lib/shared/providers/live_clients_provider.dart` if needed

Why:
- The current transfer-market discovery path hard-caps the initial fetch to 12 players.
- It also performs per-player market fan-out, which does not scale for large discovery.
- `PlayerService` already supports cursor-aware discovery against `/players`.

Work:
- Move the transfer-market discovery flow onto `PlayerService.getPlayers()`.
- Add debounced search and a real browse path with `load more` or infinite scroll.
- Reduce or remove the per-row `/shares/market` fan-out from the initial search path.
- Fix any UI text that names the wrong endpoint or implies nonexistent browsing depth.

Verification:
- Repo verification:
  - Add or update frontend tests around search, pagination, and route text.
- Runtime verification:
  - Against a real large dataset, confirm the user can search beyond the first page and continue browsing.
  - Confirm the screen no longer behaves like a 12-result peek.

Honest blockers:
- If the environment does not yet contain a large enough player corpus, runtime proof stays blocked.

### 6. Make Searchable And Buyable Player States Explicit
Priority: `P0`

Files:
- `backend/app/players/real_player_service.py`
- `backend/app/players/router.py`
- `backend/app/players/token_service.py`
- `frontend/lib/features/transfer_market/live_market_provider.dart`
- `frontend/lib/features/transfer_market/transfer_market_screen.dart`

Why:
- Searchability and share-market tradability are separate systems.
- If the UI does not label the state clearly, discoverable-but-unbuyable players look broken.

Work:
- Expose a clear market availability state for each discovered player.
- Render separate UI states such as:
  - searchable only
  - market pending
  - market active
  - market blocked
- Show buy actions only when the market is active.

Verification:
- Repo verification:
  - Add API and UI tests covering each state.
- Runtime verification:
  - Confirm the UI distinguishes existence from tradability using real staged data.

### 7. Import, Publish, And Issue A Real 5000+ Searchable And Tradeable Player Corpus
Priority: `P0`

Files:
- `ops/real-player-bulk-import-runbook.md`
- `backend/scripts/import_real_players_bulk.py`
- `backend/scripts/report_real_player_import.py`
- `backend/scripts/publish_real_players.py`
- `backend/scripts/issue_player_share_markets.py` if it does not yet exist
- `backend/data/real_player_batches/first_batch.json`
- `backend/data/real_player_batches/first_controlled_batch_v1.json`
- `backend/app/players/token_service.py`
- `backend/app/players/router.py`
- player-share market tests

Why:
- The repo samples are far too small to prove the shipped requirement.
- The runbook already targets a real staged import and publish pipeline.
- The shipped requirement is no longer just discovery.
- `5000+` must be searchable, buyable, tradeable, and usable in both GTEX and hosted competitions.

Required inputs:
- Real source dataset or the actual import run plan approved by ops.
- Real issuance cohort and the initial liquidity, price, and default status rules.

Work:
- Treat the small sample files as fixtures only, not as release evidence.
- Run the real stage -> report -> repair -> publish flow.
- Publish enough rows to exceed the approved searchable threshold.
- Issue player share markets in bulk for the approved cohorts so the same corpus is not only searchable but also buyable and tradeable.
- Verify that issued and acquired players remain eligible for both GTEX competitions and hosted competitions.

Verification:
- Repo verification:
  - Keep the runbook accurate and executable.
- Runtime verification:
  - Confirm the live API pages through a corpus greater than the target threshold.
  - Confirm search by name, club, country, and position returns dense real results.
  - Confirm the same corpus can be bought and traded through the live app flows.
  - Confirm acquired players are usable in both competition families.

Honest blockers:
- Without a real import source and a real publish run, no one should claim the large-player requirement is done.
- Without real issuance rules and a successful bulk issuance run, no one should claim the `buyable` or `tradeable` requirement is done.

### 8. Keep Both Competition Families Intentional And Close The Hosted Invite Gap
Priority: `P0`

Files:
- `backend/app/segments/competitions/segment_competitions.py`
- `backend/app/hosted_competition_engine/router.py`
- `backend/app/hosted_competition_engine/service.py`
- `backend/app/hosted_competition_engine/schemas.py`
- `frontend/lib/data/competition_api.dart`
- `frontend/lib/data/hosted_competition_api.dart`
- `frontend/lib/models/hosted_competition_models.dart`
- `frontend/lib/features/competitions/live_competitions_hub_screen.dart`
- `frontend/lib/features/competitions/live_competitions_provider.dart`
- `frontend/test/hosted_competition_api_test.dart`
- backend tests under `backend/tests/hosted_competition_engine/`

Why:
- GTEX competitions and hosted competitions are both surfaced.
- The user confirmed both are valid shipped products with distinct roles.
- Hosted competitions still lack invite and add-participant parity.

Work:
- Keep GTEX competitions as the admin-hosted, real-world mirror competition rail.
- Keep hosted competitions as the user-hosted or admin-hosted pay-to-host rail.
- Close the hosted invite gap by adding:
  - invite creation
  - invite listing
  - invite acceptance
  - participant management if required
- Make hosted creation and hosting discoverable in the real UI flow.
- Keep UI copy explicit so users can tell which family they are in and what each family is for.

Verification:
- Repo verification:
  - Add backend and frontend tests for create -> invite -> accept -> launch.
- Runtime verification:
  - Execute a GTEX competition flow against staging with real authenticated users.
  - Execute a hosted competition create -> invite -> accept -> launch flow against staging with real authenticated users.

Honest blockers:
- Repo route existence alone is not enough; the full user flow must work end to end.

### 9. Collapse Admin RBAC To One Database-Backed Source Of Truth
Priority: `P1`

Files:
- `backend/app/admin_access/router.py`
- `backend/app/admin_godmode/service.py`
- `backend/app/admin_godmode/runtime_paths.py`
- user or admin role models and migrations under `backend/migrations/`
- corresponding admin UI clients once the backend source of truth is final

Why:
- File-backed admin role state is still present.
- Multi-instance deployments and concurrent updates should not depend on flat JSON writes.

Required inputs:
- Agreement on the final RBAC ownership model and migration plan.

Work:
- Move role catalog, assignments, enabled state, and scoped permissions into durable database state.
- Use file-backed state only as a temporary import source if needed.
- Repoint admin role management away from direct JSON writes.

Verification:
- Repo verification:
  - Add tests proving role updates survive restart and second-process reads.
- Runtime verification:
  - Confirm two separate app instances or processes see the same RBAC state.

Honest blockers:
- If migrations are not created and applied, the task is not done.
- If the admin UI still writes flat files in parallel, the task is not done.

### 10. Move Market Discovery Off The In-Memory Full Table Scan
Priority: `P1`

Files:
- `backend/app/market/service.py`
- `backend/app/market/repositories.py`
- market query tests

Why:
- Market discovery still loads all tradable records and filters them in Python.
- That shape becomes unacceptable as the tradable market grows.

Work:
- Push filtering, sorting, and pagination into the SQL repository layer.
- Preserve cursor or paging semantics without rebuilding large filtered lists in memory.

Verification:
- Repo verification:
  - Add tests for search, filter, sort, and pagination semantics.
- Runtime verification:
  - Against a large tradable market, confirm response times remain acceptable and queries return the same business results.

Honest blockers:
- If only unit tests pass but no large-dataset runtime check exists, performance proof remains incomplete.

### 11. Final Verification Matrix Before Calling The Run Done
Priority: `P0`

This run should not be called complete until all applicable checks below have passed.

Required checks:
- Live app boot succeeds for every shipped release profile using real environment values.
- Payment rails are not blocked by unintended treasury mode.
- KoraPay:
  - checkout initializes
  - redirect returns correctly
  - webhook reaches `/integrations/payments/korapay/webhook`
  - invalid signatures fail closed
  - valid signatures settle the purchase order
- Player-share buy and sell:
  - blocked users cannot trade
  - verified users can trade
- Player discovery:
  - large corpus is reachable
  - transfer market can page through it
  - searchable and buyable states are clearly distinguished
- Player inventory:
  - the required `5000+` corpus is searchable, buyable, and tradeable
  - acquired players are usable in both GTEX competitions and hosted competitions
- GTEX competitions:
  - admin-hosted competition flow remains functional
- Hosted competitions:
  - create
  - invite or add participants
  - accept or join
  - launch
- Admin RBAC changes persist across restart or second-process reads.
- Unity Windows batch build remains green.

Honest blockers:
- If any item above is still unverified in a real environment, keep the run open.

## Remaining Inputs Still Needed From The User Or Ops

These are the real inputs still missing after the 2026-04-23 update:

1. Confirm that deployed production config now uses `https://gtex-api.onrender.com` as the canonical backend hostname for frontend builds, payment callbacks, and operator docs.
2. Confirm that the bootstrap admin password is present in vault and injected into the real staging and production environments.
