# GTEX: Owner Control Center (web-first launch surface)

## Original problem statement
"GTEX Nigeria Launch Plan: A web-first football club-owner platform where users build, run, and monetize clubs in a persistent football world through players, managers, facilities, competitions, and platform-native economy systems." It must be positioned as a club-owner simulator, not FM/FIFA/eFootball. The home is the Owner Control Center with 6 blocks: My Clubs, Owner Inbox, Today's Decisions, Live Club Health, Competition & Fixtures Rail, Club Economy Snapshot. Manager and regen realism engines, competitions (GTEX-hosted and user-hosted), club-building systems, and a 2D match experience with light owner controls. A unified financial ledger is the single source of truth. Two currency rails: GTEX Coin and Fan Coin, with labelled balances. Club shares are reframed as Club Support Units (not investments). Anti-collusion rules for 3-club ownership. Nigeria launch with payout eligibility, KYC thresholds, fraud review and feature-level restrictions. Football-native gifting, sponsor slots with a 70/30 split, 2D now and 3D later. Stack: React + TypeScript, FastAPI, MongoDB (the user's existing repo actually uses SQLAlchemy/SQLite/Postgres).
User choices: work inside the existing repo (github.com/wandemcphill/Global-Talent-Exchange) with no parallel app; keep its FastAPI backend as the source of truth and build a new React web frontend; JWT auth (existing); Claude Sonnet 4.5 for light AI; Paystack (live keys provided); use the repo's existing coin conversions (1 GTEX Coin = ₦100 = 100 Fan Coin); payouts follow the repo's withdrawal_controls (manual_bank_transfer).

## Architecture
- /app/gtex = user's repo (excluding .git, ops, zips, Gtex_Test_Migration). /app/backend/server.py imports `app.main.get_asgi_app()` from /app/gtex/backend. DB: SQLite at /app/gtex/data_local/gte_backend.db (DATABASE_URL). Backend changes in /app/gtex need `supervisorctl restart backend`.
- New domain module: /app/gtex/backend/app/owner_console (models, ledger, engine, service, competitions, money, ai, router), registered in app/modules.py (api_only, /api/owner/*). Alembic migration 20261016_0130_owner_console_foundation.
- Frontend: /app/frontend (CRA + TypeScript 4.9): pages Landing, Auth, Onboarding, ControlCenter, MyClubs, Market, Competitions, CompetitionDetail, MatchCenter, Squad, Academy, Finance, Inbox, Admin, PaymentCallback.

## Implemented (2026-10-16)
- Ownership-first landing; signup with club; first-club activation wizard (activate grant, then sign 11 players incl. a GK from the repo market, then appoint a manager from the repo catalog, then enter a competition).
- Owner Control Center with all 6 blocks; world-day ticks; inbox with what/why/actions; Claude-voiced messages.
- Manager traits/mood, hire/fire; regens with personality and growth drivers plus explanations; facilities; academy intake.
- GTEX-hosted plus user-hosted competitions (invite codes), league/knockout, AI fill, 2D match center (commentary, momentum, narrative, gift rail).
- Unified ledger (gross/fee/net/status/class) with labelled balances; club treasuries; capital inject/distribute (earned-only) and a capped sister-club capital move.
- Anti-collusion: same-owner bracket block, knockout auto-routing, related-party transfer fair-value band and cooldown, shuffle flags, rotation/forfeit flags, payout holds, integrity score, admin review desk.
- Withdrawals: country/KYC/integrity/balance checks, pending review, admin approve/hold/reject (manual bank transfer).
- Paystack LIVE deposits: initialize, verify on callback, webhook (/api/owner/deposits/webhook, HMAC with secret key), credited as "deposited" at ₦100 = 1 GTX.
- Fan Coin conversion at the repo rate 1:100; Club Support Units (non-investment framing); sponsor and endorsement deals (70/30); read-only coin traders directory.

## Implemented (2026-10-16, iteration 2)
- One Wallet: every owner-console LedgerEvent now also posts balanced double-entry transactions into the repo wallet ledger (WalletService.append_transaction, idempotency oc:<event>:<phase>). The owner wallet is the repo user COIN/CREDIT account, and club cash is the repo club treasury account. Pending/held money sits in owner_console:held until release or reversal. Existing events were backfilled.
- Fiat rates come from the repo's admin-controlled TreasurySettings (deposit ₦900, withdrawal ₦880 per GTEX Coin), used for Paystack deposits and withdrawals.
- Coin Trader Orders on the Finance page: buy/sell with verified traders through the repo coin_traders API (create, accept with escrow, proof, confirm/release, cancel, dispute) plus a trader desk view. Demo trader seeded by scripts/seed_demo_coin_trader.py.

## Iteration 3 (2026-10-16): run the user's own GTEX app
- User direction: no parallel app. Make the existing GTEX (Flutter frontend + FastAPI backend) functional and audit the planned items.
- The repo's Flutter web app is built (`/root/flutter`, `cd /app/gtex/frontend && flutter build web --release --dart-define=GTE_API_BASE_URL=<preview url> --dart-define=GTE_BACKEND_MODE=strict_live`) and served on port 3000 by `/app/frontend/flutter-server.js` (`yarn start`). The React console is no longer served (`yarn start:react-console`).
- Fixes in repo: gtex_universe dataclass super() TypeError (jackpot/world pulse), /api/v2/auth/* aliases for the Flutter contract, POSIX-locale boot crash in web/index.html.
- Parity audit: /app/gtex/docs/EMERGENT_PARITY_AUDIT_2026-10-16.md
- Open (resolved in iteration 4): /api/v2/players/markets 503; lineup AI auto-draft fallback.

## Iteration 4 (2026-10-16): live DB + React blended onto existing backend
- User choices: serve the React UI wired to the existing backend; keep the owner_console features (mounted on the existing modules and wallet ledger); allow Alembic migrations on the live Supabase DB; improve player/regen cards; national team player rental.
- Backend now on the LIVE Supabase Postgres (DATABASE_URL in /app/backend/.env) with Cloudinary, Korapay and the user's auth/JWT/media secrets; GTE_BACKEND_MODE=live; root admin vidvimedialtd@gmail.com. Boot takes about 3-4 min (110ms DB round-trip).
- Migrations 0130 (owner_console) and 0131 (lowercase wallet/projection/transaction enum values) applied. ledger_entries is append-only, so the model reads legacy uppercase values via _LegacyCaseEnum.
- Market 503 fix: the api_v1 module is now registered last in modules.py, so /api/v2/players/{player_id} no longer shadows /players/markets (40,352 live markets).
- AI Coach fallback: team_factory._ai_coach_auto_draft picks the best-fit XI out of position when no formation can be satisfied (unit-checked).
- Owner quotes use the repo valuation (player_summary_read_models.current_value_credits); position normalization (GK to goalkeeper).
- React (yarn start = craco): the api.ts interceptor unwraps the /api/v2 envelope; auth via /api/v2/auth/*; FUT-style PlayerCard (tiers, plus a Regen tier); PlayerDrawer scouting report (real-universe signals, form, share market buy); world market on /api/v2/players; Share Market panel on /api/v2/players/markets; Squad card view; Academy regen cards; new /app/national page (repo national-team-engine: enter as a nation, rental pool, rent, free-player claim, AI auto-build squad, admin seed defaults).
- Verification: self-tested (curl and screenshots, read-only on the live DB). The testing agent timed out.

## Iteration 5 (2026-10-16): national tournaments live + academy pack reveal
- Seeded the 12 default national tournaments on the live DB (World Cup, AFCON, Copa, Euros in senior, U20 and U17; status draft) via the admin seed endpoint.
- End-to-end on live data: the root admin took charge of Nigeria in GTEX AFCON (entry 3487e6de-...) and claimed 5 free players (Okoye, Tella, Ndidi, Gidado, John). A paid rental is correctly refused because the admin wallet holds 0 GTX (loan 100 GTX).
- Perf: the rental pool went from over 220s (timeout) to about 19s. _priced_pool batches demand counts into 2 grouped queries, and image metadata is selectin-loaded. Applied to the list, auto-build, free-claim and rent paths. The UI pages the pool 12 at a time with Load more.
- Academy pack reveal (PackReveal.tsx, framer-motion): unseen regens per club (localStorage gtex.regens.seen.<club>) trigger a sealed pack, then card-by-card flips with a Wonderkid banner (ceiling of 15+), then a summary. It shows once per regen.
- PlayerCard: the badge moved to the card corner (no name overlap), with an initials fallback for broken photos. The National page defaults to the tournament you've entered.

## Iteration 6 (2026-10-16): faster rental pool + first paid rental
- _prefetch_eligibility batches the injury/sanction/agency/contract/active-rental/member checks for a pool page (one grouped query per check). The rental pool now takes about 4s warm through the public URL (was about 19s). GTE_DB_POOL_SIZE=6 / GTE_DB_MAX_OVERFLOW=4 (was 3/2, which starved requests behind background workers).
- Admin wallet funded with no real money (user's instruction): scripts/admin_credit_wallet.py posts a balanced ADMIN_ADJUSTMENT from the platform COIN account (metadata real_money=false). 150 GTX credited to vidvimedialtd@gmail.com.
- Fixed a pre-existing repo bug: the paid national rental idempotency key was 163 chars, over the varchar(128) column, so every paid rental returned 500. It's now a sha256-based key.

## Iteration 7 (2026-10-17): pre-seeded national regens repaired + tradeable
- New app/services/regen_culture_name_pools.py: about 60 naming cultures (given and surname kept together) plus COUNTRY_PROFILES for all 157 nations (cultures, face-bank ethnicity groups, capital) and COUNTRY_CODE_REPAIRS. regen_country_name_pools installs culture pools for countries without a hand pool (the previous fallback was Nigerian names). RegenPortraitService uses the explicit face groups and serves face-bank assets via their Cloudinary URL (the old URL was http://127.0.0.1:8000).
- scripts/repair_national_regen_seeds.py ran on the live DB. 11,200 seeds now have unique, country-correct names (no numeric suffixes; 3,290 had Nigerian names in foreign pools). Codes repaired: BEL/ENG/ESP/FRA/GER/ITA/NED/ETH/hash codes to ISO; EN/SC/NI for the home nations; IE/CZ/TR duplicate pools merged to 140. Every seed has a Cloudinary face (7,009 distinct, dealt per ethnicity group), trade flags on, and minted_player_id.
- Tradeable: 11,200 ingestion_players (source_provider gtex_national_seed, deterministic uuid5 ids) plus approved portrait image rows. scripts/bulk_issue_regen_markets.py --provider gtex_national_seed issued 11,200 share markets (25 GTX platform liquidity each, 280k total; repo policy). The script now writes lowercase enum values (it used to write COIN/SYSTEM, which broke reads; the rows it wrote were normalized).
- The market detail uses the seed rating/potential for regens. The React PlayerDrawer falls back to a Regen dossier (/api/market/players/{id}) when the player isn't real.

## Iteration 8 (2026-10-17): regen filter + regen share pricing
- app/players/regen_share_pricing.py (regen_rating_potential_rarity_v1): price = 0.012 x 1.06^(rating-60) x (1 + 0.012 x min(potential-rating, 30)) x rarity (common 1.0 / rare 1.1 / elite 1.3 / legendary 1.75), clamped to 0.005-0.25 GTX. Medians: common 0.026, rare 0.037, elite 0.057, legendary 0.089 (real players have a median of 0.05).
- scripts/reprice_national_regen_markets.py repriced all 11,200 untraded national-regen markets (circulating 0 only; the old price is kept in metadata). bulk_issue_regen_markets uses the model for gtex_national_seed going forward.
- GET /api/v2/players/markets gained source=regen|real and nation=<country name or alpha2> filters. Items now carry image_url (primary portrait), nationality_code and is_regen. New GET /api/v2/players/markets/nations?source= returns name/code/count.
- React ShareMarket: 'Regens only' toggle, nation dropdown with counts, photo thumbnails, Regen badge, debounced search.
- The gtex_regen lane (12,000 older tradeable regens, 9,256 with numbered names like 'Harry Robinson 48', no photos) was repaired by scripts/repair_gtex_regen_lane.py: unique country-true names (unique across both lanes), Cloudinary face-bank portrait rows, previous name kept in dna_profile.previous_full_name. The /markets/nations result is cached in memory for 15 min.
- Known gap: about 16k real (sportmonks) players have no portrait row in the source data, so they show initials thumbnails.

## Iteration 9 (2026-10-17): Wonderkid spotlight + price history chart
- User choices: a wonderkid is a regen aged 21 or under, ranked by potential (regens only). Price history uses real share events plus a new daily price snapshot from now on.
- GET /api/v2/players/markets?sort=wonderkid: regens only (source is pinned to regen), DOB within 21 years, ordered by potential desc, then headroom (potential minus rating) desc. Rating and potential come from dna_profile (current_rating/potential_rating for national seeds, overall/potential for the gtex_regen lane). List items now carry rating and potential (null for real players).
- New table player_share_price_snapshots (migration 20261017_0133; unique player_id+snapshot_date). PlayerTokenMarketService.snapshot_share_prices does one INSERT…SELECT with ON CONFLICT DO NOTHING. The cron is POST /api/v2/players/markets/price-snapshots/cron (Bearer WEBHOOK_CRON_SECRET, returns 202 and runs in the background), scheduled daily at 00:05 UTC in /app/.emergent/crons.yml. The first snapshot was written on 2026-10-17.
- GET /api/v2/players/{id}/shares/price-history?range=7d|30d|all merges share events (an issue event shows as "listed" at the repriced initial_share_price_coin), daily closes, a carry-forward point and the current price, and returns open/current/high/low/change_pct/trade_count.
- React: the ShareMarket sort select (Name/Wonderkid), an OVR → POT column, and a Wonderkid spotlight strip (top 5) when a nation is picked. PriceHistoryChart (recharts, 7D/30D/ALL) sits in the drawer share box and is refreshed after a buy.
- Testing: iteration_8, backend 13/13 and frontend 100%.

## Iteration 10 (2026-10-17): Native Flutter UI for Wonderkids + price history
- User note: GTEX's real app is Flutter (/app/gtex/frontend). The React price-chart and Wonderkid UI was left out of the merge; the backend was merged. User choices: Wonderkids as a new Regen World left-panel section; price chart in the regen dossier rail AND the Transfer Hub selected-player panel; install the Flutter SDK to verify.
- New: lib/features/regen_redesign/data/gtex_share_market_api.dart (GtexShareMarketReader interface + GtexShareMarketApi on GteAuthedApi; models GtexWonderkid/GtexShareNation/GtexSharePriceHistory).
- New widgets: gtex_wonderkid_board.dart (nation dropdown, ranked rows, top 5 gold "spotlight", tap opens player via GtexPlayerNavigator) and gtex_share_price_history_panel.dart (fl_chart step line, 7D/30D/ALL chips, change %, H/L/trades, untraded note, 404 → "no issued share market").
- Wired up: GtexRegenWorldScreenV2 gets an optional `shareMarket` (also on .fixture); RegensScreenV2 passes GtexShareMarketApi(universeApi.client); GtexMarketSelectedPlayerPanel gets an optional priceHistoryBuilder that the Transfer Hub screen supplies.
- API contract regenerated with the repo's own tools (tools/audit/generate_contract_audit.py, then generate_api_contract_bindings.py), which updated docs/*, shared/api_contract.json and gte_api_contract.g.dart. This also picked up older backend routes that hadn't been regenerated before.
- Flutter 3.38.10 (git clone, arm64) is at /opt/flutter. Tests: new test/regen_redesign/gtex_wonderkid_price_history_test.dart passes 5/5; the regen_redesign, player_market_redesign and canonical_player_detail suites pass 101/101; flutter analyze shows no new issues; check_api_contract_violations is clean.
- KNOWN existing issue: the live Flutter web build shows "Regen world unavailable" and "Player market unavailable". The backend's SQLAlchemy QueuePool (size 6, overflow 4) runs out when the Flutter shell fires many parallel requests (for example /api/v2/market/players gives a 500 after 31s, and /regen-universe/tracking takes 18-27s). Not fixed yet; awaiting the user's decision.

## Iteration 11 (2026-10-17): Faster live screens, wonderkid badges, Flutter Owner Console phase 1
- Performance: GTE_MARKET_RECORDS_CACHE_TTL_SECONDS=300, with stale-while-revalidate plus a background warm at startup in app/market/repositories.py and main.py. A cold load takes about 90s; once warm, /market/players and /browse/catalog answer in about 0.2s. MemoryCacheBackend in core/cache.py is used by response_cache when Redis is absent. /regen-universe/tracking now reads only the columns it needs (18-27s down to about 5s, about 0.2s cached). DB pool raised to 10 + 6.
- Wonderkid badge: /players/markets?sort=wonderkid items now carry price_change_7d_pct (computed by _price_series / _price_change_7d). The Flutter wonderkid rows show a coloured 7D badge.
- Owner Console (Flutter): lib/features/owner_console/{data/owner_console_api.dart, presentation/owner_console_screen.dart, widgets/owner_console_sections.dart}. Signed-in users see it instead of HomeScreen (gte_navigation_shell_screen._buildHomeDestination); signed-out visitors keep HomeScreen. Sections: Control Center (Today's Decisions with one-tap routes, Board Table, Owner Inbox, Live Club Health, Competition & Fixtures, Club Economy), My Clubs (focus filters the Control Center by club, plus a claim-a-club empty state), Market & Transfers (links), Manager & Squad (national squad, rental pool link, auto-build suggestion with a review step, admin-only seed), Academy / Regens (wonderkid board plus a Regen World link). Wallet and role chips sit in the header; the signed-in footer sits at the bottom.
- Backend: /owner/control-center now also returns `board` (standings for the owner's competitions).
- Tests: test/owner_console passes 7/7; regen, player-market and owner suites pass 98/98; flutter analyze is clean. Checked live after logging in as admin: the console shows 50 GTX and SUPER_ADMIN, and the Nigeria squad loads.
- Flutter SDK lives at /root/flutter (persistent). After an SDK change, run `flutter clean`, otherwise tests fail with an ink_sparkle shader error.
- Phase 2 still to do: Admin Review (Trust & Payouts) section and inline decision actions (DONE in iteration 12). Phase 3: parity check against the React preview, then retire the React frontend.

## Iteration 12 (2026-10-17): Owner Console phase 2 (Flutter)
- User choices: inline buttons for every decision type the backend supports; "renew contract" is the existing regen_breakthrough "Offer improved academy contract (1,000)"; Admin Review is for admin and super_admin only; testing stays read-only on live data.
- No new backend endpoints. The console uses POST /owner/inbox/{id}/decide plus the /owner/admin/review-queue, withdrawals/{id}/review, flags/{id}/{clear|action} and payouts/{id}/release endpoints, which already have the get_current_admin guard.
- Flutter: OwnerDecisionRow renders each decision's own actions. decisionMovesMoney (transfer_bid accept, facility approve, regen contract, competition enter, sponsor/endorsement accept) asks for confirmation first. Rows show busy and error states, and after an action an outcome banner appears and the Control Center refreshes. New widgets/owner_admin_review_section.dart (AdminReviewSection plus the confirmOwnerAction dialog, with an optional note for withdrawals). The OwnerConsoleSection.admin menu item is hidden for non-admins.
- Preview: built with `--base-href /flutter-preview/` and copied to /app/frontend/public/flutter-preview (CRA serves it at /flutter-preview/index.html).
- Tests: test/owner_console passes 14/14; regen and market suites green; analyze clean; the API contract check is clean. Testing agent iteration_9: 100%, read-only (the live review queue is empty and the admin owns 0 clubs).
- Known minor issue (pre-existing): the /signin deep link shows "Route unavailable". Sign-in works from the header button.

## Iteration 13 (2026-10-17): Decision countdown and owner alerts
- User choices: overdue decisions auto-expire with the game's safe default and leave an inbox note. Windows: transfer_bid 48h; regen_breakthrough, sponsor and endorsement 72h; competition_invite 24h; everything else 96h. A one-time warning goes out 6h before the deadline. Wonderkid alert: a regen aged 21 or under moving 10% or more in 7 days, sent to share holders and to the owner of his club, once per player per ISO week.
- Backend: new app/owner_console/alerts.py (respond_by, expire_decision via resolve_item in a savepoint, warn_decision, sweep_decisions, sweep_price_jumps). Decisions that existed before rollout get a fresh clock from CLOCK_START (2026-10-17). inbox_dict now includes respond_by. The control center and the inbox endpoint sweep the user's decisions on read, and decisions are sorted by deadline before the [:6] cut. New cron POST /api/owner/alerts/cron (WEBHOOK_CRON_SECRET bearer, BackgroundTasks) runs every 15 minutes, set in .emergent/crons.yml.
- Flutter: OwnerInboxEntry.respondBy. Each decision row shows a countdown ("Respond by · 2d 3h left") that ticks every minute; under 6h it turns red as "Respond soon". Decisions are sorted by deadline, and the panel shows "N urgent". Inbox alert rows (wonderkid_price_jump, decision_expiring, decision_expired) use their own accents and icons.
- Tests: backend tests/test_owner_alerts.py passes 6/6; Flutter test/owner_console passes 17/17; a read-only sweep on the live DB ran and rolled back (0 open decisions, 0 price jumps).

## React parity gap (found 2026-10-17, approved plan: port everything, then serve Flutter at the main address and delete React)
Flutter has no screens yet for: Finance (balances, Paystack deposit with /payment/callback verify, withdrawals with eligibility, ledger, Fan Coin, support units, coin-trader desk), Onboarding (create a first club with POST /clubs, activate, sign squad via /owner/clubs/{id}/sign + /owner/market/quote, manager from /managers/catalog, first competition or finish-onboarding), Competitions (list, enter, host, join-by-code, detail with standings, play-next, forfeit and fixtures), Match Center (event replay, owner view, gift rail), My Clubs actions (facility upgrade, capital inject, distribute and sister-transfer, sponsors, supporters, disclosures, new club), Squad (manager sheet, fire, hire, mentality, squad list, internal transfers), Academy (intake, advance, regen cards) and the full Inbox page with filters.

## Backlog
- P0: Bridge the owner-console ledger with the repo's existing wallet ledger: DONE (iteration 2).
- P0: Register the Paystack webhook URL in the dashboard for the production domain.
- P1: KYC submission UI (/api/kyc); Paystack transfer payouts if processor mode changes; remove the demo trader and its 2,000 GTX demo float before launch.
- P1: Fix the pre-existing GtexUniverseService super() TypeError in the repo's gtex runtime hook.
- P2: Club identity editor (crest/colours), supporter-only competitions, 3D/season passes.
- P1: Admin must click 'Seed default tournaments' on /app/national to open rentals: DONE.
- P1: Fund the wallet to complete a paid national rental: DONE via admin adjustment (no real money). Eligibility batching: DONE.
- P2: Other ledger idempotency keys that may exceed 128 chars, e.g. fast-cup-entry:{cup}:{club}:{actor} in app/fast_cups/services/finance.py; audit them.
- P2: The regen share list item now carries an image field. Regen pricing: DONE (iteration 8).
- P1: /api/market/players is slow (about 60s) on the live DB; React uses /api/v2/players instead.
- Future: Phase 3 manager requests and regen pressure; Phase 4 unified ledger and anti-collusion hardening; Phase 5 gifting and sponsor inventory.
