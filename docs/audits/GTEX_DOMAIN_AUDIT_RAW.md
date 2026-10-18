# GTEX High-Risk Domain Audit

**Commit:** `6711a545f06ec6bda28a03379028fb8d63c50a3c` (`Publish the React shell at /console beside Flutter. (#265)`)  
**Method:** Read-only file evidence only. No financial transactions, webhooks, or live provider calls were executed.  
**Date:** 2026-10-18

---

## 1. Wallets / deposits / withdrawals

**Status:** PARTIAL

### Canonical services
| Layer | Path | Role |
|---|---|---|
| Ledger authority | `backend/app/wallets/service.py` (`WalletService`) | Double-entry postings, balance projections, payout holds, idempotent `append_transaction` |
| Funding / top-up | `backend/app/wallets/funding_service.py` (`WalletFundingService`) | KoraPay/Paystack checkout initiation + verify; syncs `UserWallet` from ledger |
| Rails | `backend/app/wallets/rail_service.py` (`WalletRailService`) | Provider rail commission / settlement glue |
| HTTP surface | `backend/app/wallets/router.py` | `/wallets`, `/wallet`, `/api`, deposits/withdrawals, top-up initiate/verify |
| Treasury | `backend/app/treasury/service.py` | Deposit requests + withdrawal quotes/requests with optional `idempotency_key` |
| Provider registry | `backend/app/wallets/providers/registry.py` | Live adapters: `korapay`, `paystack`; stubs: cards/apple/google/regional/crypto |
| Webhooks | `backend/app/admin_finance/service.py` + `backend/app/admin_finance/router.py` | Signature-verified Paystack/KoraPay event handling |
| Parallel owner money path | `backend/app/owner_console/money.py` | Separate owner-console Paystack webhook (`/owner/deposits/webhook`) |

### Provider hooks
- **Supported top-up keys:** `("korapay", "paystack")` in `backend/app/wallets/constants.py`.
- **KoraPay readiness:** secret + webhook secret required (`provider_live_deposit_ready("korapay")`).
- **Paystack readiness:** `GTE_ENABLE_PAYSTACK` **and** secret **and** webhook secret (`paystack_enabled()`).
- **`render.yaml`:** `GTE_ENABLE_PAYSTACK=true`; KoraPay + Paystack secrets `sync: false`; notification URL points at `https://gtex-api-opea.onrender.com/integrations/payments/korapay/webhook`. Secret population in Render was **not** verified from this environment.
- Webhook routes: `/integrations/payments/{paystack,korapay}/webhook` and alias `/api/webhooks/korapay`.

### Idempotency
- Ledger: unique `LedgerTransaction.idempotency_key`; replay via `_resolve_idempotent_entries` / `IntegrityError` handling in `WalletService.append_transaction`.
- Withdrawals: `PayoutRequest.idempotency_key` + hold keys `withdrawal-hold:{key}`; treasury schemas require `idempotency_key` (1–80 chars).
- Top-up orders use provider references; duplicate-reference monitoring lives in `AdminFinanceService.wallet_protection_summary`.

### `payout_eligible` defaults
| Surface | Default | Evidence |
|---|---|---|
| Agent wallet projection | **false** (fail-closed) | `backend/app/agents/agent_wallet.py` (`payout_eligible: bool = False`); model `server_default=expression.false()`; migration `20260822_0110_agent_wallet_fail_closed` sets `payout_default="false"` |
| Agent spend/settle | raises | `AgentWalletService.apply_spend` / `settle` refuse monetary authority |
| Hosted competition **participant** | **true** | `UserHostedCompetitionParticipant.payout_eligible` default `True` in `backend/app/models/hosted_competition.py` |

Agent fail-closed matches constitution intent; hosted-participant default **true** is a separate economic footgun (see §3).

### Key test files
- `backend/tests/wallets/test_wallet_service.py`
- `backend/tests/wallets/test_wallet_http.py`
- `backend/tests/wallets/test_wallet_router.py`
- `backend/tests/wallets/test_wallet_rail_service.py`
- `backend/tests/wallets/test_wallet_payments_treasury_release_gate.py`
- `backend/tests/treasury/test_withdrawal_idempotency_contract.py`
- `backend/tests/treasury/test_withdrawal_policy_snapshot_and_idempotency.py`
- `backend/tests/treasury/test_withdrawal_reviews.py`
- `backend/tests/economy/test_withdrawal_currency_guard.py`
- `backend/tests/agents/test_agent_wallet_economic_safety.py`
- `backend/tests/agents/test_agent_state_store_fail_closed.py`

### Recommendations
- **P0:** Confirm production Render secrets for KoraPay/Paystack are populated; without them deposits stay `unavailable` despite `GTE_ENABLE_PAYSTACK=true`.
- **P1:** Reconcile dual Paystack webhook paths (`admin_finance` vs `owner_console/money.paystack_webhook`) so one signed handler owns credit.
- **P2:** Document that agent `payout_eligible=false` is intentional and distinct from hosted-participant default.

---

## 2. Transfer market vs owner sign vs share market vs player cards

**Status:** PARTIAL (systems are **separate**, with overlapping UX vocabulary)

| Domain | Module / routes | What it moves | Ledger / money |
|---|---|---|---|
| **Transfer market** | `backend/app/transfer_market/` — `/api/transfer-market/*`, `/api/transfer-hub/*` | Club-to-club player/coach listings, bids, private negotiation, contract offers | Club access via `_require_actor_club_access` / ownership + org roles |
| **Owner sign** | `POST /owner/clubs/{club_id}/sign` → `sign_market_player` in `owner_console/service.py` | Buys a player from the **owner world market** into `OwnerSquadPlayer` | Owner-console ledger (`transfer_purchase` → `WORLD_MARKET`), **not** transfer-market service |
| **Share market** | `backend/app/players/router.py` — `/players/.../shares/*`; issuer + buy/sell | Fungible player **shares** / holdings | Canonical wallet ledger (`PLAYER_SHARE_*` source tags in `WalletService`) |
| **Player cards** | `backend/app/player_cards/` — `/player-cards` | Collectible card supply, listings, marketplace | Separate card marketplace services; distinct from share buy/sell |

### Conflation risks
- Naming: “market”, “sign”, “transfer”, “buy” appear in Flutter/owner UI and multiple backends.
- Owner sign and transfer market both move “players onto clubs” but use different models (`OwnerSquadPlayer` vs transfer listings / hub offers).
- Share market and player cards are economically distinct; both can appear near player detail surfaces.

### Key tests
- `backend/tests/players/test_transfer_market.py`
- `backend/tests/players/test_private_negotiation_lifecycle.py`
- `backend/tests/players/test_player_share_market_routes.py`
- `backend/tests/players/test_player_share_trade_idempotency_audit.py`
- (player cards covered under player_cards / marketplace tests elsewhere)

### Recommendations
- **P1:** Product copy + API docs must label the four rails explicitly; avoid a single “Market” nav that mixes sign + shares + cards + transfers.
- **P2:** Add a contract matrix test that asserts route prefixes do not share handlers.

---

## 3. Hosted competition funding / settlement / templates

**Status:** PARTIAL

### Templates (seeded)
`HostedCompetitionService.DEFAULT_TEMPLATES` in `backend/app/hosted_competition_engine/__init__.py` (also mirrored in `service.py` usage via `seed_defaults`):
1. `user-hosted-cup-8` — 8-team cup, entry 250 FanCoin, reward 1600, fee 1000 bps  
2. `user-hosted-league-10` — 10-team league, entry 300 / reward 2400, fee 1000 bps  
3. `queue-cup` — 4-team queue cup, entry 100 / reward 320, fee 2000 bps  

Startup seed: `backend/app/modules.py` → `_seed_hosted_competitions`.

### Funding path
- Policy: `backend/app/economy/competition_funding_policy.py`  
  - `FANCOIN_ENTRY_POOL` (CREDIT)  
  - `HOST_FUNDED_GTEX_COIN_PRIZE` (COIN; host prepaid; participants must not fund Coin prizes)
- Coin-aware wrapper: `backend/app/hosted_competition_engine/coin_aware_service.py` enforces the constitution on create.
- Escrow: competition ledger account `competition:{id}:credit:escrow`; host prepaid prize posted into escrow.
- Settlement idempotency reference: `hosted-settlement:{competition.id}` on ledger transaction.

### `payout_eligible`
Participant rows default **`payout_eligible=True`** (`models/hosted_competition.py`). That is looser than agent fail-closed.

### Key tests
- `backend/tests/economy/test_hosted_competition_coin_escrow.py`
- `backend/tests/economy/test_hosted_competition_funding_contract.py`
- `backend/tests/economy/test_hosted_competition_fee_fail_closed.py`
- `backend/tests/economy/test_phase_a_hosted_competition_db_roundtrip.py`
- `backend/tests/economy/test_competition_funding_policy.py`

### Recommendations
- **P0:** Decide whether participant `payout_eligible` should default false until KYC/settlement gate (align with agent policy).
- **P1:** Keep host-funded Coin vs FanCoin entry-pool paths covered in CI on every release.
- **P2:** Surface template keys in Flutter/React create flows so hosts cannot invent unsupported modes.

---

## 4. National team rental vs `api_v1` /rent demo fixtures

**Status:** PARTIAL (two/three parallel rental concepts)

### Canonical national rental
- Module: `backend/app/national_team_engine/`
- Routes (examples):  
  - `POST .../competitions/{id}/rental-entry`  
  - `GET .../competitions/{id}/rental-pool`  
  - `POST .../entries/{id}/rentals`  
  - Admin cleanup: `.../rentals/cleanup`  
- Mounted via `modules.py` as `national_team_engine`, `_admin`, and `national_router` aliases.

### `api_v1` demo rent
- `POST /tournaments/{tournament_id}/rent` in `backend/app/api_v1/router.py` → `GlobalApiV1Service.rent_player`.
- Demo gate: `_demo_fixtures_enabled` requires **non**-production/staging **and** `GTE_ENABLE_API_V1_DEMO_FIXTURES` truthy (`api_v1/service.py`).
- In protected envs, demo fixtures are **forced off**; `rent_player` calls `_require_demo_fixture_support("tournament rentals")` — demo-only facade, not national-team engine.

### Additional rental surface
- `POST /rent` on `backend/app/global_memory/router.py` (`GlobalMemoryService.rent_player`) — yet another rental model (`GlobalPlayerRental`).

### Key tests
- `backend/tests/national_team_engine/test_national_team_router.py`
- `backend/tests/national_team_engine/test_legendary_player_national_team.py`

### Recommendations
- **P0:** Treat `national_team_engine` as the only production national rental; keep `api_v1` rent demo-flagged (already true in prod).
- **P1:** Document or hide `global_memory` `/rent` vs national rental to avoid client confusion.
- **P2:** Contract tests that production rejects `GTE_ENABLE_API_V1_DEMO_FIXTURES` effective paths.

---

## 5. Jackpot: routes, workers, `render.yaml` crons — is auto-funding real?

**Status:** PARTIAL / BROKEN for deployed auto-trigger

### Routes (real in code)
`backend/app/gtex/router.py`:
- `GET` jackpot state / history  
- `POST /jackpot/contribute` → `contribute_from_wallet` (user debits → lottery pool)  
- Admin: runtime get/update, balance patch, `POST /admin/jackpot/trigger`

### Funding mechanics
- User contributions: wallet → lottery pool (`contribute_from_wallet`).
- **Platform auto-fund:** `record_contribution` with `GtexContributionSourceType.PLATFORM_ACTIVITY` calls `_fund_lottery_pool_for_contribution` (platform clearing → lottery pool, idempotent key `gtex-jackpot-fund:...`).
- Caller found: `TicketingService._record_jackpot_contribution` when ticketing posts activity (`backend/app/ticketing/service.py`) — **conditional** on `app.state.gtex_runtime` existing.
- Trigger evaluation / scheduled drops: `evaluate_trigger`, `_scheduled_drop_due`, `process_due_round` in `gtex/service.py`.

### Workers
- Code: `backend/app/gtex/worker_main.py` (kinds include `jackpot`), `worker_runtime.JackpotWorker` → `process_due_round`.
- Thin entry: `backend/workers/jackpot_worker.py`.
- README documents `python -m app.gtex.worker_main` and `GTE_GTEX_WORKERS`.

### `render.yaml`
- Workers present: `gtex-rq-worker`, `gtex-simulation-worker`.
- Crons present: ingest, sofifa, reprice, value-snapshots, regen, squad-tier, share-issuance, etc.
- **No** `gtex` / jackpot worker service and **no** jackpot cron.

### Verdict on “is auto-funding real?”
| Mechanism | In code? | Deployed on Render blueprint? |
|---|---|---|
| User `contribute` | Yes | API service can serve it |
| Platform activity → lottery fund | Yes (ticketing + `PLATFORM_ACTIVITY`) | Only if API has `gtex_runtime` bound and ticketing path runs |
| Automatic round trigger / failsafe drops | Yes (`JackpotWorker.process_due_round`) | **No** — worker not in `render.yaml` |
| Admin manual trigger | Yes | Yes (if admin hits API) |

**Auto-trigger of jackpot rounds is not production-wired via Render.** Platform-side lottery top-ups exist as code paths but are not the same as a continuous auto-funding cron.

### Key tests
- `backend/tests/gtex/test_gtex_system.py` (includes platform contribution funding)
- `backend/tests/gtex/test_jackpot_database_guards.py`

### Recommendations
- **P0:** Either add a Render worker for `app.gtex.worker_main` (jackpot kind) or remove product claims of automatic jackpot drops.
- **P1:** Trace ticketing → `PLATFORM_ACTIVITY` in production logs before calling auto-funding “live”.
- **P2:** Add a blueprint audit assert that jackpot worker presence matches product flag.

---

## 6. Staff: `evaluate_staff_role` vs club_legacy gm/hoyd vs owner `manager_json`

**Status:** DUPLICATED

| System | Keys / storage | Authority |
|---|---|---|
| **club_growth** | `evaluate_staff_role` / `normalise_staff_role` — `first_team_manager`, `youth_coach`, `first_team_coach`, `scout`, `agent`, `medical`, `performance_analyst` | `backend/app/club_growth/staff_role_policy.py`; used by `club_growth/service.py` + `ClubStaffAssignment` |
| **club_legacy phase2** | Executive roles `gm`, `hoyd`, `football_manager` with separate attribute schemas | `backend/app/club_legacy/full/phase2.py` (`ROLE_AUTHORITY`, `hire_executive`) |
| **owner_console** | `OwnerClubState.manager_json` profile blob (appoint/fire, mood, transfer prefs) | `owner_console/service.py`, `models.py` — not the same table as club_growth assignments |

These three are **not unified**: hiring a legacy GM does not write `first_team_manager` via `evaluate_staff_role`, and owner `manager_json` is a parallel narrative/ops manager.

### Key tests
- `backend/tests/club_growth/test_staff_role_policy.py`
- club_legacy phase2 tests under `backend/tests/club_legacy/`

### Recommendations
- **P1:** Pick one staff authority for “who manages the first team”; map aliases explicitly or deprecate two of the three.
- **P2:** Add a cross-system read model so UI does not show conflicting manager names.

---

## 7. News / inbox: story-feed vs legend_layer vs owner inbox; Flutter `/inbox` redirect

**Status:** PARTIAL / DUPLICATED (news) + BROKEN (Flutter `/inbox` as owner inbox)

| Surface | Backend | Frontend consumer |
|---|---|---|
| **Story feed** | `story_feed_engine` → `/story-feed`, `/story-feed/digest`, admin schedule/reject | Flutter `StoryFeedApi` / News Agency V2, admin newsroom |
| **legend_layer** | `/news/feed`, rankings, personality, interviews; projection on match-completed | **No verified Flutter route consumer**; backend + projection only (`legend_layer/router.py`, `backbone/projection_runtime.py`) |
| **Owner inbox** | `GET/POST /owner/inbox`, `/owner/inbox/{id}/decide` | Flutter owner console widgets; React shell `Inbox.tsx` → `/owner/inbox` |

### Flutter `/inbox` redirect
```dart
// frontend/lib/router/app_router.dart
path: '/inbox',
redirect: ... => const GteNavigationRoute.community().path,
```
`/inbox` redirects to **community**, not owner inbox. Owner decisions stay under owner-console screens / React `/app/inbox`.

### Recommendations
- **P1:** Ship or hide `legend_layer` news; today it duplicates story-feed conceptually without a client.
- **P1:** If product wants a global inbox URL, point Flutter `/inbox` at owner inbox (or rename community redirect).
- **P2:** Keep React `/app/inbox` and Flutter owner console as the decision surface; document the split.

### Key tests
- `backend/tests/story_feed_engine/test_story_feed_router.py`
- `backend/tests/story_feed_engine/test_story_feed_publish_idempotent.py`
- `backend/tests/legend_layer/test_legend_layer_router.py`

---

## 8. Security: AuthEnforcement, IDOR patterns, webhook signatures

**Status:** PARTIAL

### AuthEnforcementMiddleware scope
File: `backend/app/auth/middleware.py`.

**Protected prefixes** (plus derived `/api/v2/...` aliases):  
`/api/admin`, `/api/profile`, `/api/session`, `/api/wallet`, `/api/wallets`, `/wallets`, `/wallet`, `/policies/me`, `/users/me`, `/internal`, and exact auth me/logout/change-password.

**Not middleware-protected** (rely on per-route `Depends(get_current_user)` / admin deps):  
`/owner/*`, `/owner/legacy/*`, `/api/transfer-market/*`, `/jackpot/*`, `/story-feed`, `/national-team-engine/*`, player shares, etc.

Middleware is a belt for wallet/admin/session; most high-risk game economy routes depend on handler-level auth.

### IDOR patterns

**Transfer market — generally guarded on mutating paths**
- Mutating handlers use `get_current_user` + `_resolve_actor_club_id` / `_require_actor_club_access`.
- Public-ish GETs: `list_transfer_market_listings` and get-by-id have **no** `get_current_user` (intentional catalogue read unless visibility filters fail closed — verify visibility filter on private listings).

**Owner console — ownership checks present on core paths**
- `require_profile` / `require_state`: `owner_user_id != user_id` → `not_club_owner` 403.
- Inbox decide: `resolve_item` requires `item.user_id == user_id` (404 otherwise) then `require_state` when `club_id` set.
- Residual risk: any owner route that accepts `club_id` without `require_state` (audit per-handler if extending).

### Webhook signature requirements
`AdminFinanceService`:
- Paystack: HMAC-SHA512 over raw body vs `x-paystack-signature`; secret required in production/staging (`_signature_optional` returns false in protected envs).
- KoraPay: HMAC-SHA256 over JS-canonical `payload.data`; `x-korapay-signature` required; same fail-closed in protected envs.
- Missing secret / bad signature → `ValueError` → HTTP reject on webhook router.

**Caveat:** `owner_console/money.paystack_webhook` implements a **separate** HMAC check against its own secret path — dual handlers increase misconfiguration risk.

### Recommendations
- **P0:** Ensure private transfer listings cannot leak via unauthenticated list/get (visibility filter audit + test).
- **P1:** Consider extending AuthEnforcement prefixes to `/owner` and `/api/transfer-market` mutating namespaces as defense-in-depth (handlers already auth).
- **P1:** Collapse to one Paystack webhook verifier.
- **P2:** Keep webhook signature optional **only** outside protected envs (already coded).

### Key tests
- `backend/tests/auth/test_auth_middleware.py`
- `backend/tests/auth/test_admin_versioned_auth_boundary.py`
- Transfer / player ownership tests under `backend/tests/players/`

---

## 9. Flutter ↔ club_legacy phase4 purchase/gift HTTP

**Status:** BROKEN (UI → desk) / backend HTTP exists unused by Flutter

### Backend HTTP (exists)
Mounted under `/owner/legacy` via `club_legacy/router.py` including `phase4_routes.py`:
- `POST /{club_id}/market/purchases` → `phase4.purchase_asset` (requires `idempotency_key`)
- `POST /{club_id}/market/gifts` (+ accept/decline)
- Also transfers, listings, buy listing, bids

### Flutter behavior
- Market panel buttons call desk actions `'buy'`, `'transfer'`, `'gift'` (`club_legacy_market_panel.dart`).
- Client posts `POST /owner/legacy/{club_id}/desk` with `{action, payload}` (`owner_console_api.dart` `performDesk`).
- `perform_desk_action` (`club_legacy/operations.py`) handles hire/preset/preseason/sponsor/manager/case/list_auction/place_bid only → **`unknown_action` 404** for `buy` / `gift` / `transfer` / `purchase`.
- Repo-wide search: **no** Flutter (or React-shell) calls to `market/purchases` or `market/gifts` outside generated contract maps.

### Recommendations
- **P0:** Wire desk actions `purchase`/`gift`/`buy` to phase4 ops **or** change Flutter to call phase4 HTTP with sku/asset_id/idempotency_key; until then showroom/market buys are non-functional.
- **P1:** Showroom remains display-only (no purchase CTA) — keep consistent with dead buttons or hide them.

---

## Summary matrix

| # | Domain | Status | Top priority |
|---|---|---|---|
| 1 | Wallets / deposits / withdrawals | PARTIAL | P0 verify Render provider secrets; P1 unify webhook handlers |
| 2 | Transfer vs sign vs shares vs cards | PARTIAL (separate) | P1 clarify product/API boundaries |
| 3 | Hosted competition funding | PARTIAL | P0 participant `payout_eligible` default |
| 4 | National rental vs api_v1 rent | PARTIAL | P0 keep demo rent out of prod (already gated) |
| 5 | Jackpot auto-funding / trigger | PARTIAL / BROKEN deploy | P0 add jackpot worker to Render or drop auto-drop claims |
| 6 | Staff role systems | DUPLICATED | P1 single staff authority |
| 7 | News / inbox | PARTIAL / DUPLICATED | P1 legend_layer disposition; Flutter `/inbox` redirect |
| 8 | Security | PARTIAL | P0 private listing visibility; P1 middleware breadth + single webhook |
| 9 | Flutter phase4 purchase/gift | BROKEN client path | P0 wire desk or HTTP |

---

## Explicit non-actions
- No deposit, withdrawal, webhook, or provider API calls were made.
- No pytest suite was executed in this pass (evidence is static file review at `6711a545`).
)
