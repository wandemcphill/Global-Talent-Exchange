# GTEX Backend Architecture Map (audit)

**Commit:** `6711a545f06ec6bda28a03379028fb8d63c50a3c` — *Publish the React shell at /console beside Flutter. (#265)*  
**Scope:** `/workspace/backend` (read-only)  
**Note:** `#272` (`cf087bc5`) is an ancestor of this commit; FND-016 code is present.

---

## 1. Mount surface (`main.py` + `modules.py`)

### Boot path
- `create_app()` → `register_core()` + `register_modules(DOMAIN_MODULES)` — `backend/app/main.py:53-83`, `124-149`
- Core always mounts: health router, TTS (`/tts`), static `/generated-media`, middleware (CORS, AuthEnforcement, RateLimit, RequestHardening, ClubApiV2Alias, Observability)
- Domain routers load via `DOMAIN_MODULES` with **eager** subset then **lazy** hydrate on first non-bypass request — `backend/app/modules.py:47-64`, `110-162`, `187-199`
- Path wrappers:
  - default: bare router path as defined
  - `api_only=True` → `/api` + `/api/v2` only — `_with_api_only` L83-87
  - `with_api_alias=True` → bare + `/api` + `/api/v2` — `_with_api_alias` L75-80

### Mounted modules (185 names in `DOMAIN_MODULES`)

`health`, `observability`, `admin_ops`, `admin`, `admin_access`, `admin_api`, `admin_finance`, `admin_godmode`, `admin_players`, `admin_engine`, `admin_engine_admin`, `launch_control`, `runtime_config`, `ai_manager`, `economy`, `economy_admin`, `gift_engine`, `football_gifts_phase3`, `gift_stats_phase3`, `admin_gifts_phase5`, `reward_engine`, `reward_engine_admin`, `fan_predictions`, `fan_predictions_admin`, `predictions`, `fan_wars`, `fan_wars_admin`, `daily_challenge_engine`, `hosted_competition_engine`, `hosted_competition_engine_admin`, `moderation`, `moderation_admin`, `national_team_engine`, `national_team_engine_admin`, `national_rental`, `story_feed_engine`, `story_feed_engine_admin`, `ai_reporter`, `gtex_news_engine`, `legend_layer`, `viral`, `attention_orchestrator`, `agents`, `pundits`, `betting`, `integrity_engine`, `integrity_engine_admin`, `auth`, `api_v1`, `jobs_api`, `organizations`, `wallets`, `coin_traders`, `admin_coin_traders`, `trader`, `paystack_webhooks`, `payment_webhook_aliases`, `payments`, `media_engine`, `media_engine_admin`, `broadcast_rights`, `broadcast_rights_admin`, `club_infra`, `club_infra_admin`, `club_ownership`, `player_import`, `community_engine`, `community_social_phase2`, `history_engagement`, `history_engagement_admin`, `club_social`, `leaderboards`, `leaderboards_admin`, `world_simulation`, `world_simulation_admin`, `discovery_engine`, `discovery_engine_admin`, `global_search`, `matchday_economy`, `operations_readiness`, `player_import_admin`, `risk_ops_engine`, `risk_ops_engine_admin`, `sponsorship_engine`, `sponsorship_engine_admin`, `ads_engine`, `club_finance`, `ownership_groups`, `ownership_groups_admin`, `owner_console`, `club_legacy`, `live_ops`, `creator_campaign_engine`, `creator_campaign_engine_admin`, `creator_marketplace`, `governance_engine`, `governance_engine_admin`, `real_world_hub`, `real_world_hub_admin`, `federations`, `federations_admin`, `dispute_engine`, `dispute_engine_admin`, `streamer_tournament_engine`, `streamer_tournament_engine_admin`, `policies`, `admin_policies`, `treasury`, `calendar_engine`, `calendar_engine_admin`, `attachments`, `analytics`, `admin_analytics`, `public_analytics`, `public_pulse`, `players`, `talent_exchange`, `talent_exchange_admin`, `global_memory`, `awards`, `platform_experience`, `regen_ecosystem`, `regen_creation`, `regen_universe`, `regen_universe_admin`, `player_lifecycle`, `player_agency`, `regen_living_star`, `transfer_market`, `football_events`, `football_events_admin`, `broadcast_network`, `football_universe`, `clubs`, `canonical_clubs`, `club_lifecycle`, `club_growth`, `admin_clubs`, `club_ops`, `competitions`, `ranking_integrity`, `tournaments`, `creators`, `referrals`, `admin_referrals`, `market`, `marketplace`, `manager_duels`, `manager_market`, `manager_marketplace`, `player_cards`, `ingestion`, `value_engine`, `surveillance`, `portfolios`, `leagues`, `champions_league`, `academy`, `squad_tiers`, `club_lineup`, `live_match`, `world_super_cup`, `fast_cups`, `commentary`, `live_matches`, `ticketing`, `infinite_league`, `match_engine`, `highlight_render` (startup hooks only, no router), `moments`, `matches`, `simulation_matchmaking`, `ultimate_league`, `competitive_integrity`, `match_viewer`, `club_identity` (**jerseys only**), `club_ops_admin`, `replay_archive`, `notifications`, `notifications_admin`, `broadcast`, `gtex`, `gtex_universe`, `realtime`, `users`

Source: `backend/app/modules.py:493-914`.

### Eager modules (boot-critical)
`auth`, `admin_api`, `broadcast_network`, `realtime`, `competitions`, `hosted_competition_engine`, `live_matches`, `matches`, `broadcast`, `manager_market`, `match_viewer`, `hosted_competition_engine_admin`, `streamer_tournament_engine`, `world_simulation` — L47-64.

### Router files on disk that look “unmounted” but are **indirectly mounted**

| File | Mounted via |
| --- | --- |
| `backend/app/club_sale_market/router.py` | `canonical_clubs` → `app.routes.clubs:router` L13 |
| `backend/app/club_identity/dynasty/api/router.py` | same L16 |
| `backend/app/club_identity/reputation/router.py` | same L14-15 (`/api` + `/api/v2` prefixes) |
| `backend/app/club_identity/trophies/router.py` | same L17 |
| `backend/app/competitions/router.py` | `competitions` → `app.routes.competitions` |
| `backend/app/competitions/creator_league_router.py` | `segments/competitions/segment_competitions.py:63` → routes.competitions |
| `backend/app/creator/router.py` | `creators` → `app.routes.creators` |
| `backend/app/orders/router.py` | `wallets` → `app.wallets.router` includes |
| `backend/app/portfolio/router.py` | `wallets` → `app.wallets.router` includes |

Evidence: `backend/app/routes/clubs.py:1-19`, `backend/app/routes/competitions.py`, `backend/app/wallets/router.py:1739-1757`.

### Truly not a DOMAIN module router
- `backend/app/competition_engine/` — **library only** (scheduler, queue_contracts, match_dispatcher, calendar_service). No HTTP router. Distinct from mounted `hosted_competition_engine` and `leagues.competition_engine`.

### `club_identity` DOMAIN entry vs identity sub-routers
- DOMAIN `club_identity` mounts **only** `app.club_identity.jerseys.router:router` — modules.py L884
- Dynasty / reputation / trophies are **not** named DOMAIN modules; they ride `canonical_clubs`

---

## 2. Auth roles & admin capabilities

### `UserRole` — `backend/app/models/user.py:17-24`
`user`, `admin`, `super_admin`, `scout`, `agent`, `club`, `coin_trader`

### `PublicAccountType` — L27-30
`user`, `creator`, `coin_trader`

### Dependency gates — `backend/app/auth/dependencies.py`
- `get_current_admin` — ADMIN | SUPER_ADMIN (L180-186)
- `get_current_trader_user` — `PublicAccountType.COIN_TRADER` (L207-214)
- `get_current_football_user` / `get_current_trading_user` — `PublicAccountType.USER` (L217-248)
- Super-admin-only helpers further down (L378+)

### Admin capabilities — `backend/app/admin/capabilities.py:21-39`
Enum includes: `manage_admin_roles`, `manage_commissions`, `manage_payment_rails`, `manage_withdrawals`, `manage_treasury_withdrawals`, `manage_liquidity_desk`, `manage_competitions`, `view_audit_log`, `view_integrity_controls`, `pause_payments`, manager-catalog/supply, regen universe/national/awards/generation, `manage_players`, `manage_talent_exchange`.

Enforcement: `assert_admin_capability` loads godmode profile; SUPER_ADMIN bypasses state load; ADMIN requires permission on profile — L70-108.

Default role packs — `backend/app/admin_godmode/service.py:79-128` (`GOD_MODE`, `finance_admin`, `market_ops_admin`, competition/regen ops, `support_admin`, scoped empty).

### Signup account types (still multi-lane)
- `/signup/user` → `PublicAccountType.USER` — `auth/router.py:615`
- `/signup/creator` → `CREATOR` — L702
- `/signup/trader` → `COIN_TRADER` — L778
- `/register` → **410 Gone** pointing at those three — L512-523

---

## 3. Wallet / ledger / currency / gifts

### `WalletService` — `backend/app/wallets/service.py`
Double-entry ledger authority: ensure accounts (user, escrow, platform, treasury, rewards, match pools, betting, lottery, burn, promo, player position accounts), payment events, conversions, payouts, reserve/settle/credit trade flows, portfolio snapshot, ledger listing. Mounted via DOMAIN `wallets`.

### Currency constitution — `backend/app/economy/currency_policy.py`
- FanCoin = `LedgerUnit.CREDIT`; GTEX Coin = `LedgerUnit.COIN` (L12-13)
- Gifts: source FanCoin only → destination GTEX Coin (L16-28)
- `assert_not_giftable` blocks gifting GTEX Coin (L42-44)
- Withdrawable = GTEX Coin only (L55-57)

### Gift engine (mounted, `api_only`)
- Modules: `gift_engine`, `football_gifts_phase3`, `gift_stats_phase3`, `admin_gifts_phase5` — modules.py L518-521
- HTTP: `/api|/api/v2/gift-engine/send`, `/gifts/...`, admin gifts — `gift_engine/router.py:32-35`, `285+`
- Canonical accounting: FanCoin spend → GTEX Coin credit — `gift_engine/canonical_service.py:32`, `184-230`

---

## 4. Transfers / shares / cards / owner sign

| Lane | Mount | Key paths |
| --- | --- | --- |
| Transfer market | `transfer_market` | `/api/transfer-hub/*`, `/api/transfer-market/*` — `transfer_market/router.py:134+` |
| Player share market | `market` | `/listings`, `/buy`, `/sell` — `market/router.py:138+`, `425+` |
| Marketplace | `marketplace` | separate DOMAIN module |
| Player cards | `player_cards` | `/player-cards/...`, marketplace sales/loans/swaps — `player_cards/router.py:72+` |
| Owner sign (market player) | `owner_console` (`api_only`) | `POST .../clubs/{club_id}/sign` → `sign_market_player` — `owner_console/router.py:198-202` |

Transfer ACL: resolves club via ownership + org membership; denies when no club context — `transfer_market/service.py:243-272`, `_require_actor_club_access` / `_require_actor_any_club_access`.

---

## 5. Competitions

| Engine | Mounted? | Notes |
| --- | --- | --- |
| `hosted_competition_engine` | **Yes** (`api_only`) | `/hosted-competitions`, admin twin — modules L540-548; eager |
| `national_team_engine` (+ rental) | **Yes** (`api_only`) | `/national-team-engine`, `/national` — L553-566 |
| `competitions` (routes aggregator) | **Yes** | includes segment + `competitions/router` + creator league |
| `streamer_tournament_engine` | **Yes** | eager admin twin |
| `leagues`, `champions_league`, `fast_cups`, `world_super_cup`, `infinite_league`, `ultimate_league`, `tournaments` | **Yes** | separate product lanes |
| `app.competition_engine` package | **No HTTP** | shared scheduling/dispatch library only |

---

## 6. Staff

| Surface | Mount | Mechanism |
| --- | --- | --- |
| Club growth staff contracts | `club_growth` (`api_only`) | `evaluate_staff_role` in `club_growth/staff_role_policy.py:60-113`; used by `ClubGrowthService` |
| Manager market catalog | `manager_market` (eager) | startup seed `_initialize_manager_market` |
| Manager marketplace | `manager_marketplace` | separate module |
| Club legacy executives | via `club_legacy` | `hire_executive` desk action + phase2 `POST /{club_id}/executives` — `operations.py:730-740`, `phase2_routes.py:69+` |

`evaluate_staff_role` allows: first_team_manager, youth_coach, first_team_coach, scout, agent, medical, performance_analyst. **No GM/HYD** (aligns with prior FND-009).

---

## 7. Prestige assets (purchase / gift / desk) — post-#272

### Service layer
- `purchase_asset`, `offer_gift`, `list_asset`, `perform_desk_action` — `club_legacy/operations.py`, impl in `full/phase4.py`
- `purchase_asset` requires owner + skus from catalogue — `phase4.py:60-63`

### HTTP exposure (YES — not desk)
`club_legacy` is mounted `api_only` and **includes all phase routers** — `club_legacy/router.py:211-233`:

| Action | Route | File |
| --- | --- | --- |
| Purchase | `POST /{club_id}/market/purchases` | `phase4_routes.py:53-68` |
| Gift | `POST /{club_id}/market/gifts` | L93-101 |
| List/auction | `POST /{club_id}/market/listings` | L130-142 |
| Desk (hire/preset/auction/bid/…) | `POST /{club_id}/desk` | `router.py:159-166` |

Effective URL (api_only): `/api|/api/v2/owner/legacy/...`.

### Desk actions — `perform_desk_action` L728-814
Supports: `hire`, `preset`, `preseason_*`, `sponsor_offer`, `manager_offer`, `open_case`, `list_auction`, `place_bid`.  
**No** `purchase` / `gift` desk actions.

### Flutter
No calls to `market/purchases` or `market/gifts` in frontend (grep empty). Desk/showroom still the UX gap from the audit.

### #272 effect
Only auction/bid target IDs — **not** purchase/gift wiring.

---

## 8. Jackpots / drops / cron (`render.yaml` vs code)

### Code (`gtex` module mounted, `with_api_alias`)
- Routes: `/jackpot/state`, contribute, admin runtime/balance/trigger — `gtex/router.py:69+`
- Trigger evaluation: threshold, failsafe clock, **scheduled drop cadence** (`jackpot_min_drops_per_day`), probability — `gtex/service.py:601-649`
- Config env knobs — `gtex/config.py:39-84`

### `render.yaml` crons (repo root) — **no jackpot cron**
| Cron | Schedule | Purpose |
| --- | --- | --- |
| `gtex-realplayer-ingest` | `0 3 * * *` | SportMonks ingest |
| `gtex-sofifa-import` | `0 6 1 * *` | monthly CSV |
| `gtex-appreciation-reprice` | `0 2 * * 1` | weekly reprice |
| `gtex-value-snapshots` | `0 4 * * *` | valuation rebuild |
| `gtex-regen-rebuild` | `0 4 1 * *` | monthly regen |
| `gtex-squad-tier-backfill` | `0 5 1 * *` | monthly |
| `gtex-regen-world-bootstrap` | `0 3 1 1 *` | annual/manual |
| `gtex-player-share-issuance` | `0 2 1 1 *` | annual/manual dry-run default |

Workers: `gtex-rq-worker`, `gtex-simulation-worker`, `gtex-outbox-relay`, `gtex-player-ingestion-worker`.  
Jackpot “scheduled drops” are **in-process** when `evaluate_trigger` runs (contribution / admin), not a Render cron.

---

## 9. Club sale market & club identity — mounted or not?

**Mounted** via `canonical_clubs` (`app.routes.clubs:router`), which is in `DOMAIN_MODULES` (modules.py L799).

| Feature | Paths (examples) | Status |
| --- | --- | --- |
| Club sale market | `/api/clubs/sale-market/listings`, `/api/clubs/{id}/sale-market/...`, instant-sell, transfer | **HTTP live** |
| Dynasty | `/api/clubs/{id}/dynasty`, history; leaderboard routes on dynasty router | **HTTP live** |
| Reputation | `/api|/api/v2/clubs/{id}/reputation` (+ history/prestige) | **HTTP live** |
| Trophies | `/api/clubs/{id}/trophy-cabinet`, honors, `/api/leaderboards/trophies` | **HTTP live** |
| Jerseys | DOMAIN `club_identity` | **HTTP live** |

Flutter repositories call these paths (`club_sale_market_repository.dart`, `dynasty_api_repository.dart`, `reputation_repository.dart`). Prior “unmounted → 404” claim does **not** hold at this commit.

Settlement caution still applies: `instant-sell` and `transfer` endpoints are exposed (`club_sale_market/router.py:200`, `404`).

---

## 10. Security patterns

### IDOR / ownership
- Club legacy: pervasive `require_owner(session, club_id, user_id)` — `delegation.py:58+`; purchase/gift/list gated in phase4
- Club sale: `club.owner_user_id != actor.id` → owner-required errors — `club_sale_market/service.py:136`
- Transfer market: club membership / owner resolution — `transfer_market/service.py:243+`
- Access control: `require_club_access` — `access_control/service.py:288+`
- Pattern is **handler/service-level**, not a global IDOR middleware

### Turnstile
- `backend/app/auth/turnstile.py`: bypass tokens `dev-bypass` / `test-bypass` only when `GTE_APP_ENV` ∈ {development, test, local} **and** secret is set (L47-52)
- If **no** secret: verification is a **no-op** (L43-44)
- Signup calls `verify_turnstile_token` — `auth/router.py:590`
- Flutter hardcodes `turnstileToken: 'dev-bypass'` — `frontend/lib/screens/auth/gtex_account_signup_screens.dart:373`
- `render.yaml`: `GTE_APP_ENV=production`; **no** `GTE_TURNSTILE_*` declared

### Webhook signatures
- Paystack: HMAC-SHA512 `x-paystack-signature`; optional via `GTE_PAYSTACK_WEBHOOK_SIGNATURE_OPTIONAL` — `admin_finance/service.py:532-551`
- KoraPay: HMAC-SHA256 over JS-canonical `data`; optional twin flag — L553-589
- Owner console also has Paystack webhook path — `owner_console/router.py:591`
- Request hardening allowlists signature headers — `core/request_security.py`

### Auth middleware coverage
`AuthEnforcementMiddleware` only forces auth on a **narrow** prefix set (`/api/admin`, `/api/wallet(s)`, `/api/profile`, `/api/session`, `/users/me`, …) — `auth/middleware.py:26-42`. Most money/game routes rely on per-route `Depends(get_current_user)` (or are public reads).

---

## Prior findings at `6711a545`

| ID | Verdict | Evidence |
| --- | --- | --- |
| **FND-001** | **CONFIRMED** | Flutter still sends `dev-bypass` (signup L373). Prod env rejects bypass if secret set; if secret unset, check is no-op while UI claims automatic check. Turnstile not in `render.yaml`. |
| **FND-002** | **CHANGED** | Purchase/gift **are** on HTTP (`phase4_routes` under mounted `club_legacy`). Still **not** desk actions; Flutter showroom still does not call them. #272 did not change this. Product gap remains P1 for UX wiring, not “service unreachable.” |
| **FND-003** | **CHANGED** (prior claim wrong / fixed by long-standing `routes/clubs`) | Sale-market + dynasty + reputation + trophies **are mounted** via `canonical_clubs`. Flutter calls hit live routers. Residual risk: financial endpoints (`instant-sell`, `transfer`) are live without the audit’s “mount after settlement review” gate. |
| **FND-005** | **CONFIRMED** | Three signup lanes + account selector remain; creator/trader create non-`USER` `PublicAccountType`. Normal-account-only commits (`c5d901c6`) are **not** ancestors of this commit. Issue #228 on GitHub is currently P7-FEV (number reused / audit cross-ref stale). |
| **FND-016** | **FIXED** | `perform_desk_action` requires `asset_id` / `listing_id` — `operations.py:791-807` (blame `cf087bc5` #272). Ancestor of `6711a545`. |

---

## Top P0 / P1 candidates (this map)

### P0
1. **Live club-sale settlement surfaces without remount review** — `instant-sell` + `transfer` HTTP are mounted and Flutter-callable (`club_sale_market/router.py`). Ownership checks exist, but this is real money movement of clubs; treat as production settlement risk until certified.
2. **Turnstile production honesty / bypass path** (FND-001) — hardcoded client bypass + optional secret no-op can leave signup unprotected while advertising a check; if secret is set with current Flutter, signup breaks. Either way P0 for auth integrity.

### P1
3. **FND-005 multi-type public signup** vs normal-account product rule — creator/trader still mint privileged `account_type` at signup.
4. **FND-002 prestige buy/gift** — backend market routes ready; Flutter/desk never call them → catalogue dead in product UI.
5. **Jackpot funding ops** (FND-007) — triggers are contribution/admin/in-process only; no Render cron; failsafe/min-drops only run when `evaluate_trigger` is invoked.
6. **Webhook signature optional flags** — if `*_WEBHOOK_SIGNATURE_OPTIONAL=true` in any env, unsigned webhooks accepted (`admin_finance/service.py:535-541`).
7. **Auth middleware narrowness** — many sensitive routes outside middleware force list; regression risk if a handler forgets `Depends`.
8. **Staff dual systems** (FND-009 class) — club_growth `evaluate_staff_role` vs club_legacy executives; desk `hire` writes legacy executives, not growth contracts.

### Downgraded / closed from prior audit narrative
- FND-003 “unmounted” → **not accurate** at this commit (indirect mount).
- FND-016 → **FIXED** on this ancestry.
- FND-004 (React `/console`) → this commit **is** #265; out of backend scope but status changed upstream.

---

## Quick reference: focus routers

```
auth                          app.auth.router
wallets (+ orders/portfolio)  app.wallets.router
economy                       app.economy.router
gift_engine*                  app.gift_engine.router (api_only)
club_legacy*                  app.club_legacy.router (api_only; includes phase1–9)
owner_console*                app.owner_console.router (api_only; /sign)
transfer_market               app.transfer_market.router
market / marketplace          share + listing lanes
player_cards                  app.player_cards.router
hosted_competition_engine*    app.hosted_competition_engine.router
national_team_engine*         app.national_team_engine.router
club_growth*                  app.club_growth.router
manager_market                app.manager_market.router
canonical_clubs               app.routes.clubs  ← sale + dynasty + reputation + trophies
competitions                  app.routes.competitions
gtex                          app.gtex.router (jackpot)
```

`*` = `api_only` (`/api` + `/api/v2` only).
