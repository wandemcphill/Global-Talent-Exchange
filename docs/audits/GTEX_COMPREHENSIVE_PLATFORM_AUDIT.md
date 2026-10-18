# GTEX comprehensive platform audit (refresh)

**Status of the platform: not complete.** No screen is certified `VERIFIED COMPLETE` end-to-end in a production settlement sense. Several high-risk paths are `PARTIAL` with code and automated tests, but deposits, withdrawals, jackpot funding, and live payouts were **not** executed.

| Item | Value |
| --- | --- |
| Repository | `wandemcphill/Global-Talent-Exchange` |
| Branch audited (baseline) | `main` |
| Commit | `6711a545f06ec6bda28a03379028fb8d63c50a3c` |
| Commit subject | Publish the React shell at `/console` beside Flutter (#265) |
| Audit refresh date | 2026-10-18 |
| Working branch for this refresh | `cursor/gtex-platform-audit-refresh-eeeb` |
| Environment | Cursor cloud agent, Linux. Flutter 3.47.7 present. `.venv` with pytest/FastAPI. No production DB, no payment credentials, no authenticated browser session against seeded API. |
| Umbrella issue | [#267](https://github.com/wandemcphill/Global-Talent-Exchange/issues/267) |
| Inventories | `docs/audits/GTEX_SCREEN_INVENTORY.csv` (185 rows), `docs/audits/GTEX_ROLE_FEATURE_MATRIX.csv` |
| Raw reconnaissance | `GTEX_FLUTTER_ROUTE_INVENTORY_RAW.md`, `GTEX_REACT_ROUTE_INVENTORY_RAW.md`, `GTEX_BACKEND_DOMAIN_MAP_RAW.md`, `GTEX_DOMAIN_AUDIT_RAW.md` |
| Roadmap | `docs/audits/GTEX_REMEDIATION_ROADMAP.md` |
| Prior baseline | Audit docs from #271 at `3e2e94b` — **superseded** by this refresh |

## Executive summary

GTEX is one FastAPI backend with two frontends that do not cover the same product.

Flutter web remains the primary product surface at `/`. React (Emergent owner console) is now published beside it at `/console/` via merged PR [#265](https://github.com/wandemcphill/Global-Talent-Exchange/pull/265). Issue [#263](https://github.com/wandemcphill/Global-Talent-Exchange/issues/263) is still open because **Render Blueprint sync / live URL verification** was not performed from this agent.

Relative to the #271 audit (`3e2e94b`):

| Finding | Prior | Now on `6711a545` + this refresh |
| --- | --- | --- |
| FND-016 desk auction without ids | Open (#272) | **FIXED** — merged #272 |
| FND-004 React `/console` | Open (#265) | **CODE MERGED** — live deploy still **NOT VERIFIED** |
| FND-003 unmounted sale/identity routers | Open | **CHANGED** — mounted via `canonical_clubs` → `routes/clubs.py`. Instant-sell/transfer still need settlement review |
| FND-002 prestige buy/gift | Open (#273) | **PARTIAL** — HTTP existed under phase4; Flutter showroom Buy/Gift wired in this refresh. React still unwired |
| FND-001 Turnstile `dev-bypass` | Open (#274) | **PARTIAL** — hardcoded bypass removed from Flutter user signup. Real Turnstile widget still missing when secret is set |
| FND-005 multi-type / Nigeria signup | Open (#274/#228) | **PARTIAL** — React signup is normal-account-first; Flutter still has user/creator/trader lanes |

Highest remaining confidence defects:

1. **FND-005 / #228** — Flutter still presents creator and trader signup as separate registration products. Product rule is normal account first.
2. **FND-001 remainder** — Production with `GTE_TURNSTILE_SECRET_KEY` will reject signup until a real widget exists. `render.yaml` still does not declare Turnstile secrets.
3. **FND-009 / #276** — Four staff hire surfaces; GM/HYD are legacy executives, not `evaluate_staff_role` keys. Product decision required.
4. **FND-007 / FND-014** — Jackpot routes exist without a funding cron; payment rails **NOT VERIFIED** (no sandbox run).
5. **FND-008 / #176** — Legacy `api_v1` national rent remains mounted behind a demo-fixture flag.
6. **Club sale instant-sell / transfer** — Mounted and money-moving; treat as settlement-sensitive (P0 review), not as proof of product completeness.

## Commands run (this refresh)

| Command | Result |
| --- | --- |
| `git fetch origin main` | `main` = `6711a545…` |
| `gh issue/pr view` #2 #169 #176 #228 #263 #267 #260 #265 #272 | Issues mostly open; #260/#265/#272 merged |
| Static inventories (Flutter 167, React 18) | Written under `docs/audits/*_RAW.md` |
| `.venv` `pytest backend/tests/club_legacy/test_full_desk.py` + security console publish + deployment contract | **25 passed** |
| `pytest backend/tests/club_legacy/test_phase4_full.py` | **6 passed** |
| `pytest backend/tests/auth/ -k 'signup or turnstile'` | **5 passed, 1 failed** (`test_trader_signup_requires_proof_of_address` — pre-existing expectation mismatch, not introduced here) |
| `flutter test` showroom + owner console | **25 passed** (includes new catalogue purchase widget test) |
| `npm ci` + React `npm run build` with `PUBLIC_URL=/console` | **Compiled successfully** |
| Browser / Playwright 390×844, 768×1024, 1440×900 | **Not run** — no authenticated seeded session |
| Live deposits / withdrawals / jackpots / payouts | **Not performed** |

Evidence logs: `/opt/cursor/artifacts/audit/`.

## Linked issue status

| Issue | State | This refresh |
| --- | --- | --- |
| [#2](https://github.com/wandemcphill/Global-Talent-Exchange/issues/2) Economic foundation | Open | Code still matches constitution for ledger authority, gift conversion, agent non-authority. Not production-certified. |
| [#169](https://github.com/wandemcphill/Global-Talent-Exchange/issues/169) / [#176](https://github.com/wandemcphill/Global-Talent-Exchange/issues/176) Lifecycle | Open | Still authoritative for staff, academy, national rental, competition lanes. |
| [#228](https://github.com/wandemcphill/Global-Talent-Exchange/issues/228) Browser verification | Open | No authenticated browser pass here. React signup aligned closer to normal-account rule; Flutter multi-type remains. |
| [#263](https://github.com/wandemcphill/Global-Talent-Exchange/issues/263) React `/console` | Open | Implementation merged (#265). Live Render check still required. |
| [#267](https://github.com/wandemcphill/Global-Talent-Exchange/issues/267) Umbrella audit | Open | This document refreshes the baseline. |
| [#273](https://github.com/wandemcphill/Global-Talent-Exchange/issues/273) Prestige wire-up | Open | Flutter showroom path started; React + end-to-end club_legacy flag in prod still open. |
| [#274](https://github.com/wandemcphill/Global-Talent-Exchange/issues/274) Signup / Turnstile | Open | Bypass removed; multi-type Flutter lanes and Turnstile widget remain. |
| [#275](https://github.com/wandemcphill/Global-Talent-Exchange/issues/275) Unmounted routes | Open | Largely **stale as framed** — routers are mounted via aggregator. Retarget to settlement review of club-sale money paths. |
| [#276](https://github.com/wandemcphill/Global-Talent-Exchange/issues/276) Staff authority | Open | Unchanged; needs product decision on GM/HYD. |

## Inventory totals

Source: `GTEX_SCREEN_INVENTORY.csv` after regenerating from route tables on `6711a545`. Status means end-to-end product status, not “a widget file exists”.

| Shell | VERIFIED COMPLETE | PARTIAL | BROKEN | NOT IMPLEMENTED | DUPLICATED | NOT VERIFIED | Rows |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Flutter | 0 | 31 | 0 | 8 | 54 | 74 | 167 |
| React | 0 | 18 | 0 | 0 | 0 | 0 | 18 |
| Total | 0 | 49 | 0 | 8 | 54 | 74 | 185 |

Role matrix: 30 rows. None `VERIFIED COMPLETE`. Counts approximately PARTIAL 17, NOT VERIFIABLE 9, NOT IMPLEMENTED 3, DUPLICATED 1.

`DUPLICATED` still includes intentional redirects (`/wallet` → `/app/capital`) and true parallel products (staff markets, competition engines, news feeds).

## Canonical sources (unchanged architecture, refreshed mount notes)

| Domain | Canonical code | Parallel / note |
| --- | --- | --- |
| Ledger | `backend/app/wallets/service.py` | `UserWallet` / `AgentWalletRecord` projections |
| Currencies | `economy/currency_policy.py` | FanCoin=`CREDIT`, GTEX Coin=`COIN` |
| Gifts (FanCoin→Coin) | `gift_engine/canonical_service.py` | Legacy gift body still present |
| Prestige assets | `club_legacy` phase4 HTTP `/owner/legacy/{club}/market/purchases|gifts` | Catalogue SKUs only; Flutter showroom now calls these |
| Hosted comps | `hosted_competition_engine/coin_aware_service.py` | Templates `user-hosted-cup-8`, `user-hosted-league-10`, `queue-cup` |
| National team | `national_team_engine` | `api_v1` `/rent` demo-gated |
| Transfers | `transfer_market` | Distinct from owner `/sign`, share `market`, `player_cards` |
| Staff | `club_growth` + `evaluate_staff_role` | Parallel: manager_market, owner `manager_json`, club_legacy executives |
| Club sale / dynasty / trophies / reputation | Mounted via `canonical_clubs` → `routes/clubs.py` | Not absent; money paths need review |
| News | story-feed vs legend_layer vs viral | UI not unified |
| Inbox | `GET /owner/inbox` | Flutter `/inbox` still community redirect |
| Auth roles | `UserRole` + `PublicAccountType` | No GM / moderator login role |

## Domain traces (high risk)

### Registration — PARTIAL

Flutter: `/account/select` → user/creator/trader. User signup no longer sends `dev-bypass`. Creator/trader lanes remain. React: normal account signup with user-entered country; club create deferred to onboarding / My Clubs with user-entered geography.

### Prestige — PARTIAL

Catalogue: Harbour Jet, Lagoon Coach, Icon Watch. Phase4 HTTP + ledger debit + idempotency tested (`test_phase4_full.py`). Flutter showroom Buy/Gift wired. React has no prestige desk. Depends on `club_legacy` feature flag in the target environment.

### Wallets — NOT VERIFIED (settlement)

Code paths and webhook handlers exist. Paystack/Kora secrets are dashboard-managed (`sync: false`). No sandbox deposit/withdrawal executed.

### Competitions — PARTIAL

Hosted escrow idempotency keys exist. Platform wrappers (fast cups, infinite league, etc.) remain separate UI products. React competition detail still has scheduled fixture `to="#"`.

### National rentals — PARTIAL

Canonical engine vs demo-gated v1 rent. React auto-build is suggestion-only.

### Jackpots — NOT VERIFIED / deploy gap

Routes present; no jackpot cron in `render.yaml`.

### Staff — DUPLICATED

See FND-009 / #276.

### News / inbox — PARTIAL

Flutter `/inbox` ≠ owner inbox. React `/app/inbox` is owner inbox.

### Admin — NOT VERIFIED in browser

Capability packs via godmode; screen-level checks still inconsistent.

## Shell architecture recommendation

**Keep Flutter as the primary product at `/`. Keep React as the owner-operations console at `/console/`.** Do not rewrite Flutter into React for cosmetic parity.

| URL | Shell | Job |
| --- | --- | --- |
| `/` and existing Flutter paths | Flutter | Fans, matchday, markets, regen world, newsroom, admin command center |
| `/console/*` | React | Owner control center, clubs, finance, inbox decisions, academy, national entry |
| `/api`, `/api/v2` | Backend | Mounted canonical routers only |

Rollout: #265 already merged in code. Confirm Render Blueprint rewrites and that `/console/login` refresh serves React. Rollback: remove `/console` rewrites and stop copying the React build; Flutter stays up.

Source of truth: one API OpenAPI surface + ledger. Generate typed clients later so shells cannot call unmounted or deprecated paths unnoticed.

## UI/UX proposals

Unchanged in substance from the #271 audit design section (Club HQ hierarchy, owner public profile, newsroom bound to story-feed, four labeled market lanes, shared player/regen card header, owner inbox on both shells). Prioritize binding Flutter `/inbox` to `GET /owner/inbox` and labeling market lanes before visual polish.

## Findings table (refresh)

| ID | Sev | Status | Notes |
| --- | --- | --- | --- |
| FND-001 | P1 | Partial repair in this PR; #274 open | Bypass removed; widget still needed |
| FND-002 | P1 | Partial repair in this PR; #273 open | Flutter showroom wired; React + prod flag open |
| FND-003 | P1 | Reframed; #275 retarget | Mounted via aggregator; review instant-sell/transfer |
| FND-004 | P1 | Code done (#265); deploy NOT VERIFIED | Close #263 after live checks |
| FND-005 | P1 | Partial; #274/#228 | React fixed; Flutter multi-type remains |
| FND-006 | P2 | Open (#2) | Ledger tests green on subsets only |
| FND-007 | P1 | Open | Jackpot funding decision + cron |
| FND-008 | P1 | Open (#176) | Remove or 410 v1 rent |
| FND-009 | P1 | Open (#276) | Staff authority + GM/HYD decision |
| FND-010 | P1 | Open | Label market/competition lanes |
| FND-011 | P1 | Open (#228) | Shared cards; `/player-cards` marketplace |
| FND-012 | P2 | Open | Flutter owner inbox route |
| FND-013 | P2 | Open | Admin gate consistency |
| FND-014 | P1 | NOT VERIFIED | Sandbox payments only |
| FND-015 | P2 | Open | Club HQ / profile structure |
| FND-016 | P1 | **FIXED** (#272) | Explicit auction/bid targets |

## Blockers

| Blocker | Classification |
| --- | --- |
| No authenticated browser against seeded API | #228 remains open |
| Payment secrets must not be used for live charges | Deposits/withdrawals/payouts **NOT VERIFIED** |
| Jackpot funding not triggered | **NOT VERIFIED** |
| Render live `/console` and worker health | **NOT VERIFIED** from this agent |
| `club_legacy` flag in production | Showroom may 404 if disabled |
| Pre-existing `test_trader_signup_requires_proof_of_address` failure | Auth suite not fully green |

## What improved since #271

- React `/console` publish path is on `main` with docs and contract tests.
- Club-legacy desk no longer silently auctions/bids the first asset/listing.
- Prestige purchase/gift HTTP is reachable from Flutter showroom with widget coverage.
- Flutter no longer advertises an automatic security check while sending `dev-bypass`.
- React signup no longer hardcodes Nigeria or creates a club during registration.
- This environment could run Flutter and pytest (the prior audit could not).
