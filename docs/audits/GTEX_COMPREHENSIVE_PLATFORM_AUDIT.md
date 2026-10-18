# GTEX comprehensive platform audit

**Status of the platform: not complete.** This audit does not certify any screen, role, or financial flow as production-ready. No row in the screen inventory is `VERIFIED COMPLETE`.

| Item | Value |
| --- | --- |
| Repository | `wandemcphill/Global-Talent-Exchange` |
| Branch audited | `main` |
| Commit | `3e2e94b661c060dbd67512756923d0b4eecc0b8a` |
| Commit date | 2026-10-18 03:45:44 UTC (`feat: encrypt KYC and bank identifiers at rest with blind indexes (#264)`) |
| Audit date | 2026-10-18 |
| Environment | Cursor cloud agent, Linux. Flutter is not installed. `pytest` and FastAPI are not installed. No browser, no production database, no payment credentials. |
| Umbrella issue | [#267](https://github.com/wandemcphill/Global-Talent-Exchange/issues/267) |
| Inventories | `docs/audits/GTEX_SCREEN_INVENTORY.csv` (152 rows), `docs/audits/GTEX_ROLE_FEATURE_MATRIX.csv` (30 rows) |
| Roadmap | `docs/audits/GTEX_REMEDIATION_ROADMAP.md` |

## Executive summary

GTEX is one backend with two frontends that do not cover the same product.

Flutter web is the Render production shell. `render.yaml` builds `ops/render/build-frontend.sh` into `frontend/build/web` and publishes that directory. There is no `/console` rewrite on this commit. React lives at `frontend/react-shell/` and is a narrower owner console (control center, clubs, market signings, competitions, text match center, squad, academy, national rentals, finance, inbox, admin). Serving it beside Flutter is open work: issue [#263](https://github.com/wandemcphill/Global-Talent-Exchange/issues/263) and pull request [#265](https://github.com/wandemcphill/Global-Talent-Exchange/pull/265). Do not treat React as deployed.

The backend is a large modular FastAPI app (`backend/app/main.py`, `backend/app/modules.py`). Ledger posting, FanCoin versus GTEX Coin, hosted-competition funding modes, and agent-wallet non-authority match the economic constitution closely enough to say issue [#2](https://github.com/wandemcphill/Global-Talent-Exchange/issues/2) is largely implemented in code. That is not a production settlement certificate. Deposits, withdrawals, webhooks, jackpots, and prize payouts were not executed.

The highest-confidence defects from static evidence:

1. Flutter user signup always sends Turnstile token `dev-bypass` (`frontend/lib/screens/auth/gtex_account_signup_screens.dart`). Production services set `GTE_APP_ENV=production`. If a Turnstile secret is configured, that token is rejected. If it is not configured, the security check is a no-op while the screen says it runs automatically. **FND-001, P1.**
2. Prestige catalogue items (Harbour Jet, Lagoon Coach, Icon Watch) can be purchased and gifted in `purchase_asset` / `offer_gift`, but `perform_desk_action` has no purchase or gift action and neither shell exposes one. **FND-002, P1.**
3. Flutter calls the club-sale market and several club-identity routes whose routers are not mounted in `DOMAIN_MODULES`. **FND-003, P1.**
4. Registration still asks the user to be a user, creator, or trader. Trader signup collects country and preferred currency. React signup hardcodes Nigeria and can create a club during signup. That contradicts the account model on issue [#228](https://github.com/wandemcphill/Global-Talent-Exchange/issues/228). **FND-005, P1.**
5. The club desk can auction “the first owned asset” and bid on “the first other auction” when the client omits ids. The Flutter client omits them. **FND-016, P1.** A focused repair is separated from this baseline report.
6. Staff, transfers, competitions, and news each have more than one engine. Issues [#169](https://github.com/wandemcphill/Global-Talent-Exchange/issues/169) and [#176](https://github.com/wandemcphill/Global-Talent-Exchange/issues/176) remain the lifecycle track. This audit did not re-run those suites.

## Commands run

| Command | Result |
| --- | --- |
| `git fetch origin main` | `main` is `3e2e94b661c060dbd67512756923d0b4eecc0b8a` |
| `gh issue view` for #2, #169, #176, #228, #263, #267 | Bodies and comments read. All six issues are open. |
| `gh pr list` | #265 open for `/console`. #260 merged the React source. |
| Static route extraction from `app_router.dart`, `gte_route_data.dart`, `frontend/react-shell/src/App.tsx` | 152 inventory rows |
| `python3 -c "import pytest"` | `ModuleNotFoundError`. Backend tests were not executed. |
| `which flutter` | Not installed. Flutter analyze/tests were not executed. |
| Browser / Playwright at 390x844, 768x1024, 1440x900 | Not run. No screenshots. |
| Deposits, withdrawals, jackpot funding, payouts | Not performed. |

## Linked issue status

| Issue | State on 2026-10-18 | What this audit found |
| --- | --- | --- |
| [#2](https://github.com/wandemcphill/Global-Talent-Exchange/issues/2) Economic foundation | Open | Code matches the constitution for gift conversion, non-giftable GTEX Coin, host-funded Coin prizes, FanCoin participant purses, fee bps from admin policy, agent wallet as a projection, and `payout_eligible` default false. Default seed for competition fee is still 3000 bps in `admin_engine`. Not production-certified. |
| [#169](https://github.com/wandemcphill/Global-Talent-Exchange/issues/169) Lifecycle tracking | Open | Still the right tracker. Academy, staff, scouting, national rental, competition, and awards were not re-certified here. |
| [#176](https://github.com/wandemcphill/Global-Talent-Exchange/issues/176) Lifecycle repair | Open | Canonical services exist for the flows in that brief. Parallel legacy paths are still mounted or still reachable from UI. Phase 6G in the issue comment is out of scope and was not implemented. |
| [#228](https://github.com/wandemcphill/Global-Talent-Exchange/issues/228) Browser verification | Open | No authenticated browser pass in this audit. Registration, regen presentation, and player cards still diverge from the product comments on that issue. |
| [#263](https://github.com/wandemcphill/Global-Talent-Exchange/issues/263) React at `/console` | Open | Not on this `main`. PR #265 is the implementation and is unmerged. React `BrowserRouter` has no basename. |

## Inventory totals

Source: `GTEX_SCREEN_INVENTORY.csv`. Status means end-to-end product status, not “a widget file exists”.

| Shell | BROKEN | DUPLICATED | NOT IMPLEMENTED | NOT VERIFIABLE | PARTIAL | VERIFIED COMPLETE | Rows |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Flutter | 16 | 41 | 4 | 42 | 31 | 0 | 134 |
| React | 1 | 1 | 0 | 1 | 15 | 0 | 18 |
| Total | 17 | 42 | 4 | 43 | 46 | 0 | 152 |

Role matrix (`GTEX_ROLE_FEATURE_MATRIX.csv`): 30 roles or role-like actors. None are `VERIFIED COMPLETE`. Counts: PARTIAL 16, NOT VERIFIABLE 8, NOT IMPLEMENTED 3, DUPLICATED 1, BROKEN 0 (role gaps are recorded as partial or not implemented because the role string is missing rather than a single broken screen). Club owner, staff, and registration rows carry the P1 findings.

`DUPLICATED` includes intentional legacy redirects (`/wallet` to `/app/capital`) as well as real parallel products. Redirects are listed so deep links are not mistaken for missing screens. The finding ids call out the parallel products that matter.

## Canonical sources

| Domain | Canonical code | Parallel or legacy path | Note |
| --- | --- | --- | --- |
| Ledger | `backend/app/wallets/service.py` posting `LedgerAccount` / `LedgerEntry` / `LedgerTransaction` | `UserWallet` projection, `AgentWalletRecord` (explicitly not spend authority), `ledger/service.py` event log | Constitution section on ledger authority holds in code. |
| Currencies | `backend/app/economy/currency_policy.py` FanCoin = `LedgerUnit.CREDIT`, GTEX Coin = `LedgerUnit.COIN` | Gift engine `service.py` still contains older same-unit logic | Package import patches in the canonical gift service. Read the canonical module before changing gifts. |
| Gifts | `backend/app/gift_engine/canonical_service.py` | Legacy gift service body | FanCoin in, GTEX Coin out. GTEX Coin is not a gift source in the canonical policy. |
| Hosted competitions | `hosted_competition_engine/coin_aware_service.py` used by the router | `hosted_competition_engine/service.py` still used by calendar seed | Templates: `user-hosted-cup-8`, `user-hosted-league-10`, `queue-cup`. |
| Other competitions | `competition_engine` dispatcher | fast cups, infinite league, owner-console mini leagues, champions league wrappers, world super cup | Wrappers should delegate. They are still separate products in the UI. |
| National team | `backend/app/national_team_engine/` | `POST /api/v1/tournaments/{id}/rent` in `api_v1` | V1 rent calls `_require_demo_fixture_support`. Flag `GTE_ENABLE_API_V1_DEMO_FIXTURES` defaults off and is unset in `render.yaml`. |
| National templates | `national_team_engine/competition_profiles.py` | — | `gtex-world-cup`, `gtex-u20-world-cup`, `gtex-u17-world-cup`, `gtex-afcon`, `gtex-u20-afcon`, `gtex-u17-afcon`, `gtex-copa`, `gtex-u20-copa`, `gtex-u17-copa`, `gtex-euros`, `gtex-u20-euros`, `gtex-u17-euros`. |
| Transfers | `backend/app/transfer_market/` with `_resolve_actor_club_id` | Owner `POST /owner/clubs/{id}/sign`, share `app/market/`, unmounted `orders` and `portfolio` routers | Authorization tests exist under `backend/tests/players/`. Not re-run here. |
| Player shares | `backend/app/market/router.py` | Player-card marketplace `app/player_cards/` | Different assets. Flutter `/player-cards` redirects to the transfer hub. |
| Staff gameplay | `club_growth` contracts and `evaluate_staff_role` | `manager_market`, `manager_marketplace`, owner `manager_json`, club-legacy executives | Four hiring surfaces. |
| Prestige assets | `club_legacy/operations.py` catalogue and `purchase_asset` | Club cosmetic `POST /api/clubs/catalog/purchase` | Cosmetic purchase is not the jet/watch catalogue. |
| News | Flutter news agency reads `GET /api/story-feed` | `legend_layer` `/news/feed`, `ai_reporter`, viral feed | UI does not unify them. |
| Inbox | `GET /owner/inbox` | Flutter `/inbox` redirects to community | React `/app/inbox` is the owner inbox. Flutter `/inbox` is not. |
| Auth roles | `UserRole`: user, admin, super_admin, scout, agent, club, coin_trader | `PublicAccountType`: user, creator, coin_trader | No player, moderator, or general-manager login role. |
| Admin capabilities | `get_current_admin` plus `require_admin_capability` | Per-screen string checks | `finance_admin`, `market_ops_admin`, `competition_ops_admin`, `god_mode`, `scoped_admin` live in godmode state, not `UserRole`. |
| Club sale | Service and router file `backend/app/club_sale_market/router.py` | Not mounted | Flutter repository calls `/api/clubs/sale-market/...`. |
| Identity | Jersey router is mounted (`club_identity.jerseys`) | Dynasty, reputation, and trophy routers are not in `modules.py` | Flutter still has those routes. |

Routers present on disk and not referenced by `router_path` in `modules.py`: `club_sale_market/router.py`, `portfolio/router.py` (legacy; `portfolios` is mounted), `orders/router.py`, `club_identity/dynasty/api/router.py`, `club_identity/reputation/router.py`, `club_identity/trophies/router.py`.

## Domain traces

Code presence is not `VERIFIED COMPLETE`. Flows below are static traces.

### A. Registration and club creation — PARTIAL

Flutter account select sends people to `/auth/signup/user`, `/auth/signup/creator`, or `/auth/signup/trader`. User signup collects name, handle, password, and date of birth, then `POST /auth/signup/user`, then `/app/home`. It does not collect nationality. It does send `turnstileToken: 'dev-bypass'`. Creator signup collects country. Trader signup collects country and preferred currency and shows a client-generated TOTP secret. `POST /auth/register` is 410.

React `/signup` posts a signup that hardcodes `country: "Nigeria"` and can include club fields. Onboarding then `POST /api/clubs` with hardcoded `country_code: "NG"` and `city_name: "Lagos"`.

Club creation after login also exists as Flutter `POST /api/clubs` (`CreateClubScreen`) and `POST /owner/clubs/claim`. Three creation paths do not share one state machine.

Issue #228 requires: normal account, GTEX ID, sign in, then optionally create a club. That is not what either shell does today.

### B. Club owner journey — PARTIAL

Signed-in Flutter `/app/home` mounts `OwnerConsoleScreen`. `/app/club` mounts `GtexClubOwnerDashboardScreenV2` when a club id exists. React `/app` is `ControlCenter`. Owner HTTP includes claim, activate, sign, manager hire/fire, academy intake, and facility upgrade on `owner_console/router.py`, plus club-ops and club-infra routes. `HomeDashboardScreen` is not referenced by the shell.

A club can be operated from the owner console without a General Manager. The GM hire button on the legacy desk creates a `ClubLegacyExecutive`, not a `club_growth` staff contract, and nothing in this trace shows that executive changing tactics.

### C. Prestige assets — PARTIAL, purchase NOT IMPLEMENTED on HTTP

Catalogue in `club_legacy/operations.py`: Harbour Jet (`gtex-jet-harbour`, 50000, cap 5), Lagoon Coach (`gtex-coach-lagoon`, 8000, cap 10), Icon Watch (`gtex-watch-icon`, 20000, cap 1). Club caps: 5 jets, 10 coaches. `purchase_asset` debits club GTEX through `post_club_legacy_transfer`, checks supply, and is idempotent on `idempotency_key`. `offer_gift` / `resolve_gift` move an owned asset to `owner_class=player`.

`perform_desk_action` accepts hire, preset, preseason, sponsor, manager offer, case, list auction, and place bid. It does not accept purchase or gift. The showroom and desk widgets do not call those functions. There is no React prestige desk. No `backend/tests/club_legacy` test was found that drives purchase through HTTP. The feature flag `club_legacy` 404s the whole router when disabled.

Cars and buses are not catalogue SKUs. The coach SKU is a vehicle (Lagoon Coach), not a coaching staff member. Do not invent prices or extra SKUs.

### D. Player and regen cards — PARTIAL

Flutter canonical real-player widget: `frontend/lib/ui_gtex/football/gtex_player_card.dart`. Regen widget: `frontend/lib/ui_gtex/football/gtex_regen_card.dart`. They do not share a base class. React uses `PlayerCard.tsx` and `PlayerDrawer.tsx`. Profile route `/players/:playerId/profile` is `GtexFmPlayerProfileScreen`. `/player-cards` redirects to the transfer hub, so the marketplace screen is only on `/player-cards/inventory`. Scout and shortlist client methods point at `POST /scout/report/{id}` and talent shortlist routes. Issue #228 still asks for a shared grid, hero, and compact card system and for regen nationality/name integrity. This audit did not query live seed data, so the Albanian/Italian name defect is **not re-verified** and remains an open #228 item.

### E. Transfers and markets — PARTIAL

Club-to-club bids go through `transfer_market` and the service checks the authenticated actor’s club rather than trusting `bidder_club_id` alone. Tests exist (`test_transfer_authorization.py`, `test_transfer_ownership_authorization.py`) and were not run. Owner signing (`POST /owner/clubs/{id}/sign`) is a different transaction from a club-to-club transfer. Share trades are `app/market`. Platform purchase versus club transfer is the distinction issue #176 requires; the code has separate modules, which is necessary, but the Flutter market lane presents them in one shell. Listing deep link `/market/transfers/:listingId` degrades to the hub.

React market can sign and buy shares. It does not host the transfer center.

### F. Wallets — code path present, settlement NOT VERIFIABLE

`GET /wallets/overview` and related routes read the ledger. Deposits and withdrawals are implemented in wallet and treasury services with idempotency keys. Paystack is enabled in `render.yaml` (`GTE_ENABLE_PAYSTACK=true`) and secrets are `sync: false`. KoraPay keys are also `sync: false`. Whether those secrets are populated in Render was not checked. No deposit, webhook, or withdrawal was sent. There is no first-class “send GTEX Coin to a username” wallet route in the Flutter client. User-to-user value moves through gifts (FanCoin to GTEX Coin) or coin-trader orders.

Agent payout eligibility defaults false (`agents` model `payout_eligible`). Agent wallet methods that would spend raise rather than post. That matches issue #2.

### G. Competitions — PARTIAL

User-hosted templates and escrow idempotency keys live in the hosted competition engine (`hosted-settlement:{id}`). Platform competitions also include fast cups, infinite league, owner-console loops, and the national profiles listed above. Settlement idempotency tests exist (`test_hosted_competition_coin_escrow.py` and related) and were not run. React competition detail links some scheduled fixtures to `#` (`CompetitionDetail.tsx`).

### H. National team and rentals — PARTIAL

Flutter `GtexNationalTeamRentalScreenV2` and React `NationalTeam.tsx` target the national-team engine. React auto-build returns a plan and does not rent. The legacy v1 rent route remains mounted and returns unavailable unless demo fixtures are enabled. That is the correct fail-closed behavior for the default flag, and it is still a second rental model waiting to be removed.

### I. Jackpots, drops, rewards — NOT VERIFIABLE

Jackpot routes exist on `gtex/router.py` (`/jackpot/state`, contribute, admin trigger). `render.yaml` crons cover ingestion, repricing, value snapshots, regen rebuild, squad tier, regen bootstrap, and player-share issuance. No cron in that file is named for jackpot funding. Reward claims exist on season pass and daily challenge routers. Automated jackpot funding was not observed and was not triggered.

### J. Staff — PARTIAL and DUPLICATED

`evaluate_staff_role` knows `first_team_manager`, `youth_coach`, `first_team_coach`, `scout`, `agent`, `medical`, and `performance_analyst`. Aliases map manager and head coach onto first-team manager. There is no General Manager and no Head of Youth Development in that policy. Those names exist as club-legacy executive roles (`gm`, `hoyd`) and as a desk button that hires a GM executive with a fixed payload (`role: gm`, name Ada Okonkwo, wage 4000). Owner-console `POST /owner/clubs/{id}/manager` writes `manager_json`. `club_growth` service maps scout, coach, and manager types onto `scout_quality`, `training_bonus`, and `negotiation_bonus`. This audit did not prove a signed staff row changes a lineup.

### K. Newsroom and inbox — PARTIAL

Producers and the Flutter news screen are listed in the canonical table. Owner inbox items are written by owner console and club legacy and read by `GET /owner/inbox`. Flutter’s `/inbox` path does not open that inbox. Empty, error, and unread behavior were not exercised.

### L. Admin — code path present, NOT VERIFIABLE in the browser

`/admin` requires `controller.isAdmin && controller.session != null`, and `gtexIsAdminRole` includes super admin, god mode, admin, and scoped admin. Individual screens such as gift economy and fan wars check only `admin` and `super_admin`. React admin checks `admin` and `super_admin` and is absent from the mobile nav. Finance control tower uses `get_current_admin`. Treasury uses permission strings such as `manage_treasury_withdrawals`. These are different gates. A pass on one does not imply a pass on the others.

### M. Deployment — Flutter only on this commit

`gtex-web` static site, Flutter build, publish path `frontend/build/web`. API `gtex-api`, RQ worker, simulation worker, outbox relay, player-ingestion worker, and the crons named above are declared in `render.yaml`. Worker health in Render, including the suspended ingestion worker in issue [#136](https://github.com/wandemcphill/Global-Talent-Exchange/issues/136), was not queried. `docs/REACT_CONSOLE_RENDER.md` is not on `main`. CORS allow-origin in `render.yaml` is `https://gtex-web-tw6c.onrender.com`.

### N. Shell recommendation

Keep Flutter as the default product at `/`. Keep React as an owner-operations console and publish it only under `/console` after PR #265 is reviewed. Do not rewrite Flutter into React to make the screens look alike.

Reasons from this tree:

- Flutter owns matchday, regen world, lineup, newsroom, admin command center, public club pages, and the route aliases users already have.
- React owns a tighter owner loop (onboarding stage, control center, finance, inbox decisions) and is missing lineup, 2D/3D match, regen world, newsroom, KYC, and transfer listings.
- React is not basename-aware. Shipping it at `/` would collide with Flutter.
- One API and one ledger stay the source of truth. Shells must not grow private balances or private competition engines.

Target route map:

| URL | Shell | Job |
| --- | --- | --- |
| `/` and existing Flutter paths | Flutter | Product, including fans, matchday, markets, regen world, admin |
| `/console/*` | React, after #265 | Owner control center, clubs, finance, inbox decisions, academy, national entry |
| `/api` and `/api/v2` | Backend | Only mounted canonical routers |

Rollout: merge #265 only when Flutter `/` still builds, `/console` assets load, and a refresh of `/console/login` serves the React document. Rollback: remove the three `/console` rewrites and stop copying the React build. Flutter remains up.

Shared contract: generate client types from the mounted OpenAPI surface so a Flutter route cannot call an unmounted router without a failing check. That check does not exist today (`FND-003`).

## Design proposal

These are structural proposals for the shells that already exist. They do not add currencies, prices, or rules.

### Club home

One Club HQ, reached from `/app/club` and from the owner console club section. Do not keep a second dashboard on `/app/home` for signed-in owners; home can deep-link here.

1. Identity bar: crest, club name, Club ID, city, one philosophy line, public-page link.
2. Today: at most three owner inbox decisions, next fixture, club GTEX balance from the ledger.
3. Squad strip: senior XI using the shared player card compact variant. Empty state is an explicit “no senior contract” message, not sample players.
4. Operations: staff (one list that shows club-growth contracts, not a second executive list), academy intake, facilities, transfer room.
5. Secondary: showroom exhibits that are actually owned. Catalogue items that cannot be purchased stay out of this page until `FND-002` is wired.

### Owner profile

Public page, separate from Club HQ and from `/profile` settings.

1. Person: display name, GTEX ID, account age. No wallet controls.
2. Clubs: cards linking to public club pages the user owns.
3. Showroom: owned prestige assets only, with edition number and supply cap from the catalogue.
4. Record: awards and competition finishes that already have a persisted source. Omit sections with no source.

### Newsroom

One column bound to `GET /api/story-feed`.

1. Filters: club, competition, type. Filters must be query params the story-feed API already supports; do not merge other feeds in the client.
2. Each row: headline, time, source event id, club or player link.
3. Empty state: “No stories”. Remove placeholder AI copy when the feed is empty.
4. Other producers (`legend_layer`, viral) stay on their own routes until a backend projection exists.

### Transfer market

Four labeled lanes, each bound to the service that already implements it:

1. Platform sign — owner sign endpoint.
2. Club transfer — transfer-market listings and bids. Bid button disabled until the server resolves exactly one acting club.
3. Free agent / regen offer — regen contract inbox and quote/submit.
4. Shares — share market, visually distinct from player cards.

Player cards in all four lanes use the same identity header (portrait, name, flag, position, age, rating).

### Inbox

React `/app/inbox` and a Flutter route that calls `GET /owner/inbox` (not the community redirect) should be the same list.

1. Rows are persisted `OwnerInboxItem` records: title, body, actions returned by the API, read state.
2. Actions post the action key the item already carries. No client-invented approve.
3. Empty, error, and retry states. No sample manager quote.

### Player card and regen card

One identity header used by `GtexPlayerCard`, `GtexRegenCard`, and React `PlayerCard`.

| Variant | Use | Fields |
| --- | --- | --- |
| Grid | Regen world, market browse | Portrait, name, flag, position, rating, age, rarity or origin |
| Compact | Lists, squad strip, search | Portrait, name, position, rating |
| Hero | Profile | Grid fields plus club or free-agent label, contract state, and only the actions the backend allows |

Do not copy a licensed card game layout. Regen names and nationalities must come from the seed record. If lineage is absent, the hero says so.

## Findings

| ID | Sev | Status | Evidence | Reproduction | Remedy |
| --- | --- | --- | --- | --- | --- |
| FND-001 | P1 | Open | `gtex_account_signup_screens.dart` line 373 sends `dev-bypass`. `turnstile.py` accepts that token only when `GTE_APP_ENV` is development, test, or local. `render.yaml` sets `GTE_APP_ENV=production` on services. Turnstile secret is not declared in `render.yaml`. | Sign up on Flutter against an API that has `GTE_TURNSTILE_SECRET_KEY` set and `GTE_APP_ENV=production`. Expect “Security check failed”. With no secret, signup succeeds and the caption “Security check runs automatically” is false. | Real Turnstile widget, or stop claiming a check. Do not keep a hardcoded bypass. |
| FND-002 | P1 | Open | `purchase_asset` and `offer_gift` exist. `perform_desk_action` ends at `unknown_action` for anything else. Showroom widget has no buy or gift control. | As a club owner with `club_legacy` enabled, open the showroom. No control calls `purchase_asset`. | Expose the existing functions with sku, owner class, idempotency key, and recipient. Do not add SKUs. |
| FND-003 | P1 | Open | `club_sale_market/router.py` and dynasty, reputation, and trophy routers are absent from `modules.py`. Flutter calls `/api/clubs/sale-market/listings` and identity paths. | Open `/clubs/sale-market` or `/clubs/{id}/identity/dynasty` against this API. Expect 404. | Mount only after settlement review, or remove the Flutter routes. Do not mount `instant-sell` and `transfer` casually. |
| FND-004 | P1 | Open, owned by #263 / #265 | `render.yaml` `gtex-web` build is Flutter only. React `BrowserRouter` has no basename. | Fetch `/console/` on a deploy of this commit. React is not there. | Review and merge #265, then verify `/`, `/console/`, and refresh of `/console/login`. |
| FND-005 | P1 | Open, tracked by #228 | Account selector and three signup screens. Trader country and preferred currency. React Nigeria hardcode and inline club. | Walk `/account/select` and React `/signup`. | One normal-account signup. Club, creator, and trader capabilities after login. |
| FND-006 | P2 | Open, tracked by #2 | Gift and wallet code match the constitution. No user-to-user GTEX send route in Flutter. Fee default seed is 3000 bps. | Read `currency_policy.py`, `canonical_service.py`, `competition_funding_policy.py`, agent `payout_eligible`. | Keep #2 open until a ledger test run is green on current main. Do not add a send-coins feature in this audit. |
| FND-007 | P1 | NOT VERIFIED | Jackpot routes exist. No jackpot cron in `render.yaml`. | Read `render.yaml` cron names and `gtex/router.py`. | Decide whether funding is admin-triggered or scheduled. Do not trigger it from this audit. |
| FND-008 | P1 | Open, tracked by #176 | `api_v1/router.py` `POST /tournaments/{id}/rent` calls demo fixtures. National engine is separate. | Call the v1 route with the demo flag off. Expect unavailable. With the flag on, expect in-memory rent. | Remove or permanently 410 the v1 rent route after confirming no client uses it. |
| FND-009 | P1 | Open, tracked by #169/#176 | Four staff surfaces. No GM or HYD in `evaluate_staff_role`. | Hire GM on the desk. Read `club_staff` tables. The executive row is the legacy table. | Pick club-growth contracts as canonical. Map or retire legacy executives. |
| FND-010 | P1 | Open | Transfer, share, card, and owner-sign modules. Several competition runtimes. | Compare route prefixes in `modules.py`. | Document the lane in the UI. Do not merge the ledgers. |
| FND-011 | P1 | Open, tracked by #228 | Two Flutter card widgets. `/player-cards` redirect. Regen cap and naming not re-tested. | Open `/player-cards`. Land on the transfer hub. | Shared card header. Point `/player-cards` at the marketplace. Re-test regen seeds. |
| FND-012 | P2 | Open | News agency uses story-feed. `/inbox` redirects to community. React inbox is owner inbox. | Compare `app_router.dart` `/inbox` redirect with `GET /owner/inbox`. | One inbox route per shell bound to owner inbox. |
| FND-013 | P2 | Open | Admin checks differ by screen. No moderator `UserRole`. | Compare `gtexIsAdminRole` with `GiftEconomyAdminScreen` role set. | One admin dependency for admin screens. |
| FND-014 | P1 | NOT VERIFIED | Payment provider secrets are dashboard-managed. No sandbox run. | `render.yaml` Paystack and Kora keys `sync: false`. | Sandbox verification outside this agent. No live money. |
| FND-015 | P2 | Open | Signed-in home is owner console. Club lane is another dashboard. Public club is `/world/clubs/:clubId`. `/profile` is account settings. | Read shell home branch in `gte_navigation_shell_screen.dart`. | Adopt the Club HQ and owner profile structures above. |
| FND-016 | P1 | Repair in a focused PR | `perform_desk_action` selects the first owned asset or the first other auction when ids are missing. Flutter `owner_console_api.dart` sends only price or amount. | Tap “Auction an asset” or “Place bid” on the desk. | Require `asset_id` and `listing_id`. |

P3 notes, not separate repairs: design-lab routes are unlinked fixtures; many Flutter paths are aliases; `gteShellHomeRouteName` is unused; React ships an unused shadcn kit.

## What is already in good shape

- Ledger is the monetary authority, and the agent wallet is marked as a projection with payout eligibility defaulting false.
- Canonical gifts convert FanCoin to GTEX Coin and reject GTEX Coin as a source.
- Hosted competition HTTP uses the coin-aware service and distinguishes host-funded GTEX Coin prizes from FanCoin entry pools.
- Transfer bid authorization derives the club from the authenticated actor.
- API v1 demo rent fails closed unless the demo flag is on.
- Club-legacy purchase, if it is called, uses the ledger, supply caps, and an idempotency key.
- KYC and bank identifier encryption landed on this `main` via #264. This audit did not re-test it.
- Flutter remains the deployed shell, which is the right default until React is basename-correct and explicitly published.

## Blockers

| Blocker | Classification |
| --- | --- |
| No pytest/FastAPI in this environment | Tests listed in the roadmap were not executed here |
| No Flutter SDK | Widget tests not executed |
| No Playwright browser session against a seeded API | Issue #228 remains open. Viewports not captured |
| Payment secrets not available and must not be used for live charges | Deposits, withdrawals, payouts **NOT VERIFIED** |
| Jackpot funding not triggered | **NOT VERIFIED** |
| Render worker runtime state, including issue #136 | **NOT VERIFIED** |
| `club_legacy` flag state in production | Showroom and desk may 404. **NOT VERIFIED** |

## Existing audits reused

September 2026 documents under `docs/audits/` (`gtex-p7-fe-exit-gate-certification.md`, route integrity sweep, FEV readiness, product parity, market, club progression) describe an earlier Flutter pass. They are not a substitute for this matrix. P7-FE exit does not mean #228 browser verification or this umbrella audit is complete.
