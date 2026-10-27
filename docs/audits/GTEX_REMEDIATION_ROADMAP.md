# GTEX remediation roadmap

Current review baseline: `main` `bb6d82a9b8b5867318f9a0baf19789cef5b25637` (2026-10-27). The 2026-10-18 evidence at `45e29ef6` is retained as historical, not current-main certification. Findings are defined in `docs/audits/GTEX_COMPREHENSIVE_PLATFORM_AUDIT.md`; this roadmap records the current deltas below.

**Historical second pass (2026-10-18, `45e29ef6`)**: on that snapshot, backend CI slices were green, `flutter analyze` had 0 errors, `flutter test` reported 1259 pass/20 fail, and seeded API + HTTP checks ran. These totals are historical; current-main outcomes are tracked in the checkpoint below. Corrected FND-003 (routers mounted), FND-004 (#265 merged), FND-016 (#272 merged), FND-008 (route lives at `/api/v2`).

Nothing here is permission to merge. Each repair is a reviewable pull request. Do not start a shell rewrite. Do not run live deposits, withdrawals, jackpot funding, or payouts to close a row.


## Current-main checkpoint (2026-10-27, `bb6d82a9`)

- Current `main` Quality Gates and Phase A Economic Regressions passed; the Android debug build passed. Final Platform Certification and the wider CI/staging workflow were still running when checked. See the linked current-run table in `GTEX_COMPREHENSIVE_PLATFORM_AUDIT.md`; do not carry forward the 2026-10-18 test totals as current results.
- The Club HQ/squad spec is consolidated in `qa/playwright/tests/p7_fe_extended.spec.mjs`: squad at `/app/club`, Club HQ at `/app`, truthful live/no-club states and horizontal-overflow assertions. CI config covers mobile, tablet (768×1024) and desktop (1440×900). The matrix was still running on #337's branch and that branch used an older helper copy, so a green result must be confirmed against the current-main revision before calling this complete.
- Flutter signup no longer sends `dev-bypass`; it uses the Turnstile widget. Keep server-side challenge enforcement/configuration under review rather than marking the entire auth finding production-certified.
- Showroom purchase and gift interactions are now wired in the main Flutter owner console; PR #299 merged. Continue to require current tests and economic/ledger certification before certifying the path end-to-end.
- React `/console` and explicit desk auction/bid target changes landed via #265 and #272. Remaining concrete signup/onboarding defect: React add-club and first-club creation still hardcode NG/Lagos rather than collecting geography.
- Lifecycle implementation PRs #337, #338 and #339 are merged, and issues #169/#176 are closed. That is a code/issue status, not a blanket test sign-off.
- PR #334 is closed as redundant because its one-line `enableAccessibility` import is already on current main.

## Dependency order (revised, second pass)

```text
0. Authorization on money/competition writes — CMP-NEW-01 fixed in PR #280; remaining: CMP-NEW-04, NEW-PRESTIGE-2, NAT-NEW-1, NEW-003
1. Settlement correctness — NEW-001 (unbacked bids), CMP-NEW-03 (fees never paid), NEW-002 (caller-supplied price), CMP-NEW-02 (double-settle race), NEW-JRW-001 (double-credit), NEW-JRW-003 (FanCoin→COIN mint)
2. Re-check server-side signup enforcement/configuration (NEW-AUTH-1) and remove React first-club/add-club NG/Lagos defaults; Flutter client no longer sends `dev-bypass`
3. One staff/club-ops authority (FND-009, NEW-STF-001, NEW-STF-002/003/004) — continues #169 / #176
4. Prestige purchase/gift on the existing catalogue (FND-002, NEW-PRESTIGE-1, NEW-PRESTIGE-4/5)
5. Market and card lanes (FND-010, FND-011)
6. Inbox, newsroom, chat route honesty (FND-012, FND-015, NEWS-001, MSG-001, JNY-001)
7. React /console deploy verification (FND-004 → #263 close-out)
8. Provider and jackpot certification in sandbox (FND-006, FND-007, FND-014, NEW-JRW-002, WAL-NEW-01/03/04)
9. Admin capability alignment (FND-013, NEW-004)
10. API contract reconciliation (CONTRACT-001)
11. Re-run the historical test-rot suites against current main; 20 Flutter failures and ~34 domain failures were recorded only on the `45e29ef6` snapshot
```

The listed settlement/authentication findings are historical candidates and must be individually revalidated on the current code before creating a repair PR. Do not infer a current defect only because it appears in the 2026-10-18 snapshot. Changes involving provider rails, payouts, or policy still require sandbox credentials or an explicit product/admin decision.

## Second-pass repair PRs

### PR-280 — Authorization on competition match writes (CMP-NEW-01) — **merged 2026-10-19**

**Severity:** P0. PR [#280](https://github.com/wandemcphill/Global-Talent-Exchange/pull/280) is merged. Keep the regression test and re-run it on current main; do not track it as an open repair.

**Change:** `record_match_event` and `complete_match` in `backend/app/segments/competitions/segment_competitions.py` now load the `Competition` and call `_require_manage_competitions_or_creator(request, actor, competition)` — the same guard `cancel_competition`/`settle_competition_payouts` already use. Previously any authenticated user could write events/results to any competition, feeding `ranking_integrity_service.record_match_result` and corrupting standings/settlement input.

**Regression test:** `test_match_writes_require_host_or_admin` in `backend/tests/competitions/test_competition_lifecycle.py` — outsider gets 403 on both endpoints; host succeeds (201/200).

### Remaining P0/P1 candidates from the 2026-10-18 snapshot (revalidate before opening a repair PR)

| Finding | Sev | Historical shape (not yet reconfirmed on current main) |
| --- | --- | --- |
| CMP-NEW-04 (#282) | P1 | `GET /api/fast-cups/{cup_id}/result-summary` has no `get_current_user` and settles payouts via `FastCupFinanceService.settle_result_summary` + `session.commit()`. Add auth + move settlement to POST/admin path. |
| NEW-001 (#281) | P0 | Transfer market accepts unbacked bids — no settlement moves coins on acceptance. Needs a settlement path or bid locking; product-owner decision on which. |
| NEW-PRESTIGE-2 (#283) | P1 | Gift accept/decline has no authorization — any authenticated user can resolve anyone's gift. Same pattern as CMP-NEW-01. |
| NAT-NEW-1 (#284) | high | National lifecycle squad submit accepts fabricated players; rental provenance unenforced. |
| CMP-NEW-03 (#285) | P1 | `/api/tournaments` collects entry fees but never pays winners — prize pool locked. |
| CMP-NEW-02 (#285) | P1 | FanCoin-pool hosted finalize has no row lock/idempotency — double-settle race. |
| NEW-JRW-001 (#286) | high | Reward settlements double-credit: no DB unique constraint, no ledger idempotency. |
| NEW-JRW-003 (#286) | medium-high | FanCoin ticket revenue mints withdrawable GTEX Coin jackpot pool — cross-unit leak. |
| NEW-002 | P1 | Club-sale transfer settles at caller-supplied price, not accepted offer price. |
| NEW-003 | P1 | Free-agent transfer listings creatable by any club (seller hijack). |
| NEW-STF-001 (#288) | high | Club ops API served from in-memory `ClubOpsStore` singleton — data resets on restart. |
| NEW-PRESTIGE-1 | P1 | Desk Sponsor/Manager/Governance buttons 404 — Flutter action names don't match `perform_desk_action` verbs. |
| NEW-AUTH-1 (#287) | P1 | Turnstile enforced only on `/signup/user`; creator/trader signups skip `verify_turnstile_token`. |
| WAL-NEW-01 | high | Admin coin-trader liquidity issue broken on migrated DBs (migration `20260914_0122`). |

## PR groups

### PR-A — Club desk must name its target (FND-016)

**Status:** Resolved by merged PR [#272](https://github.com/wandemcphill/Global-Talent-Exchange/pull/272) on 2026-10-18. Do not reintroduce implicit first-asset/first-listing selection from the older audit branch.

**Change:** `perform_desk_action` rejects `list_auction` without `asset_id` and `place_bid` without `listing_id`. Remove the query that picks the first owned asset or the first other auction. Flutter sends the id from the desk snapshot. Add `auctionable_assets` (owned, unlisted) and `can_bid` on market rows so the client has a real target.

**Tests:**

- `backend/tests/club_legacy/test_full_desk.py` asserts `asset_required` and `listing_required`, and the existing auction flow passes `asset_id`.
- `frontend/test/owner_console/club_legacy_desk_test.dart` taps per-asset auction and per-listing bid and records the ids.

**Acceptance:** A desk request with `{"action":"place_bid","payload":{"amount":"2000"}}` returns `listing_required` and creates no bid. A request with a listing id still bids on that listing only.

**Certification:** Run `pytest backend/tests/club_legacy/test_full_desk.py -q` and the Flutter desk widget test. This agent’s environment had neither pytest nor Flutter; the repair PR must record the actual result.

**Status:** Open as draft PR #272. `pytest backend/tests/club_legacy/test_full_desk.py` passed (1 test) in the audit environment. Flutter widget tests were not run because the Flutter SDK is not installed.

### PR-B — Unmounted routes the Flutter client already calls (FND-003)

**Severity:** P1. **Depends on:** a settlement read of `club_sale_market` before any mount. **Issue:** file a child issue; do not mount in the audit PR.

**Choice, pick one per router:**

| Router | Safe default until reviewed |
| --- | --- |
| `club_sale_market` including instant-sell and transfer | Hide Flutter entry points and return a single “not available” state. Mounting moves club ownership and money. |
| Dynasty, reputation, trophies | Remove or gate the Flutter routes until the routers are mounted. Jersey identity can stay; that router is mounted. |

**Acceptance:** No Flutter screen issues a request whose path is absent from the mounted route table. A CI check compares client paths to `DOMAIN_MODULES` for these prefixes.

**Certification:** A test that builds the app route table and fails if `/api/clubs/sale-market/listings` is called while the module is unmounted, or succeeds after a reviewed mount.

### PR-C — Signup matches the normal-account rule (FND-001, FND-005)

**Severity:** P1. **Depends on:** issue #228 comments, which already state the rule. **Do not invent KYC fields.**

**Change:**

- One signup form: identity and credentials. No account-type picker, no trader country, no preferred currency, no club name.
- Flutter stops sending `dev-bypass`. If `turnstile_required` is true, the client obtains a real token. If it is false, the client omits the token and does not tell the user a check ran.
- React stops hardcoding Nigeria and stops creating a club inside signup. Club creation stays on the post-login onboarding already at `/onboarding` and Flutter `CreateClubScreen`.
- Collapse claim versus `POST /api/clubs` only after naming which service is canonical. Until then, document both and stop adding a third.

**Tests:** Auth router tests for user signup without `club_name`. A test that `dev-bypass` is rejected when `GTE_APP_ENV=production` and a secret is set (already true in `turnstile.py`; add a client test that the signup request does not contain `dev-bypass`).

**Acceptance:** New users receive a GTEX ID and a normal account. Club ID appears only after a post-login create or claim. Creator and trader tools are reachable later without a second registration.

**Certification:** `backend/tests/auth/test_auth_router.py` plus the Flutter signup widget test. Browser check at 390x844 and 1440x900 under #228.

### PR-D — One staff record (FND-009)

**Severity:** P1. **Depends on:** #169 and #176. **Do not add wages or roles.**

**Change:** Club-growth `ClubStaffContract` plus `evaluate_staff_role` is the staff authority. Owner-console manager assignment writes that contract (or reads it) instead of only `manager_json`. Legacy `gm` and `hoyd` executives are either mapped onto existing role keys with an explicit decision (`first_team_manager` is not automatically a GM) or the desk stops hiring them. Personal manager stays the non-salary path in `evaluate_staff_role`.

**Decision required before coding the GM button:** Is “General Manager” `first_team_manager`, a new role key, or retired? The code does not say. Do not guess a new role.

**Acceptance:** Accepting a staff offer creates one contract and one assignment. A second accept is a no-op. A different user cannot accept it. Tactical or training reads that already consult staff effects see that assignment.

**Certification:** `backend/tests/club_growth/test_club_growth_router.py` extended for the owner-console bridge, plus the forbidden-actor case.

### PR-E — Prestige buy and gift (FND-002)

**Severity:** P1. **Depends on:** `club_legacy` flag behavior and PR-A so desk actions stay explicit. **Prices stay the catalogue.**

**Change:** Desk or showroom actions `purchase` and `gift` call `purchase_asset` and `offer_gift` with sku or asset id, idempotency key, and recipient ref. Reject unknown actions. Show supply cap and sold-out from the catalogue. Flutter and React both call that action or both hide the catalogue.

**Acceptance:** Owner purchase debits club GTEX once, mints one edition, and repeats of the same idempotency key return the same asset. Gift to a non-owned asset is 403/409. A second gift of an offered asset does not duplicate ownership. Insufficient funds do not mint.

**Certification:** New tests beside `test_full_desk.py`. No production purchase.

### PR-F — Market lanes and cards (FND-010, FND-011)

**Severity:** P1. **Depends on:** #176 for transfer versus platform purchase, #228 for card hierarchy.

**Change:** Label the four lanes in Flutter market and React market. `/player-cards` opens the card marketplace, not the transfer hub. Extract a shared identity header used by both card widgets and the React card. Do not merge share trades into player contracts.

**Acceptance:** A share purchase does not create a `PlayerContract`. A club-to-club accept does not run platform-sale termination. Card hero shows club or free-agent from the same field the market uses.

**Certification:** Existing transfer authorization tests plus a widget test for the shared header. Regen seed repair stays on #228 and needs a database pass this environment did not have.

### PR-G — Inbox, newsroom, Club HQ (FND-012, FND-015)

**Severity:** P2. **Depends on:** no backend invention. Story-feed stays the newsroom source.

**Change:** Flutter route for owner inbox calls `GET /owner/inbox`. Community keeps its own path. Newsroom empty state has no placeholder copy. Club HQ layout follows the audit design section, reusing owner console and club dashboard data already loaded.

**Acceptance:** `/inbox` on Flutter and `/app/inbox` on React show the same item ids for one user. A stranger’s inbox id is rejected by the API (add a regression if missing).

**Certification:** Router test plus an owner inbox authorization test.

### PR-H — React at `/console` (FND-004)

**Severity:** P1 for deployment clarity, not a new feature. **Depends on:** PR #265. Do not open a second implementation.

**Acceptance:** Already written on #263. Flutter stays at `/`. Nested `/console/login` survives refresh. API origin is `https://gtex-api-opea.onrender.com`. Rollback documented.

**Certification:** Tests cited on #265, plus a manual check after Blueprint sync. This audit did not deploy.

### PR-I — Money certification, sandbox only (FND-006, FND-007, FND-014)

**Severity:** P1 unknown until run. **Depends on:** credentials the owner must supply. **Forbidden:** live charges, live withdrawals, live jackpot top-up.

**Work:** Run the existing wallet, webhook, hosted-competition escrow, and jackpot guard tests on current main. In a provider sandbox, walk one deposit to ledger credit and one withdrawal to a held payout request. Record whether Paystack and Kora secrets are present without printing them. Decide jackpot funding (admin trigger versus cron) from `gtex/config.py` rather than adding a schedule.

**Acceptance:** Test commands and pass/fail are pasted into #2 or #267. Sandbox evidence is labeled sandbox. Production settlement stays **NOT VERIFIED** until a separate production-readiness review.

### PR-J — Admin gates (FND-013)

**Severity:** P2. **Depends on:** the godmode role list, which is the authority.

**Change:** Admin screens use `gtexIsAdminRole` or `get_current_admin` consistently. React mobile nav includes admin for admin roles. Document that moderator is not a role.

**Acceptance:** A `scoped_admin` session that Flutter treats as admin is not shown a gift screen that then dead-ends, or the screen uses the same helper.

**Certification:** Widget tests for the role helper and one API 403 test for a normal user on an admin finance route (`test_endpoint_authorization.py` if it already covers this).

## Explicitly not in this programme

- Phase 6G from the comment on #176.
- New currencies, fees, prize amounts, card rarities, or catalogue SKUs.
- Replacing Flutter.
- Merging any of these PRs from the agent.
- Editing historical migrations to hide failures.
- Triggering ingestion backfill, jackpot contribution, or payout release against production.

## Child issues to open

These are not duplicates of #2, #169, #176, #228, #263, or #136.

| Issue | Findings | Acceptance |
| --- | --- | --- |
| [#273](https://github.com/wandemcphill/Global-Talent-Exchange/issues/273) Prestige purchase and gift | FND-002 | PR-E acceptance |
| [#274](https://github.com/wandemcphill/Global-Talent-Exchange/issues/274) Normal-account signup and Turnstile bypass | FND-001, FND-005 | PR-C acceptance |
| [#275](https://github.com/wandemcphill/Global-Talent-Exchange/issues/275) Unmounted club-sale and identity routes | FND-003 | PR-B acceptance |
| [#276](https://github.com/wandemcphill/Global-Talent-Exchange/issues/276) One staff hire path; GM and HYD decision | FND-009 | PR-D acceptance, decision recorded in the PR |
| [#272](https://github.com/wandemcphill/Global-Talent-Exchange/pull/272) Explicit desk auction and bid targets | FND-016 | Resolved — PR #272 merged |

#228 already covers browser certification, regen seeds, and the card rebuild. #263 already covers `/console`. #176 already covers lifecycle bridges. Link those instead of filing them again.

## How a row becomes VERIFIED COMPLETE

All of the following, for that screen or flow:

1. The UI control calls a mounted route.
2. The route’s auth check rejects a different user.
3. The canonical service writes the canonical table or ledger.
4. A later read returns that write.
5. An automated test covers the success and the forbidden case.
6. For a screen, a browser check at 390x844 and 1440x900 shows loading, empty, and error without sample data.
7. For money, evidence is sandbox or test, never an unlabeled production charge.

Until then the status stays PARTIAL, BROKEN, NOT IMPLEMENTED, DUPLICATED, or NOT VERIFIABLE.
