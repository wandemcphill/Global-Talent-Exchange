# GTEX remediation roadmap

Baseline: `main` `3e2e94b661c060dbd67512756923d0b4eecc0b8a`, audit date 2026-10-18. Findings are defined in `docs/audits/GTEX_COMPREHENSIVE_PLATFORM_AUDIT.md`. Screen and role rows cite those ids.

Nothing here is permission to merge. Each repair is a reviewable pull request. Do not start a shell rewrite. Do not run live deposits, withdrawals, jackpot funding, or payouts to close a row.

## Dependency order

```text
1. Stop unsafe implicit money actions (FND-016)
2. Stop advertising unmounted financial routes (FND-003) without mounting them blindly
3. Signup honesty (FND-001, FND-005) — product rules already written on #228
4. One staff authority (FND-009) — continues #169 / #176
5. Prestige purchase and gift on the existing catalogue (FND-002)
6. Market and card lanes (FND-010, FND-011)
7. Inbox and newsroom route honesty (FND-012, FND-015)
8. Publish React only at /console (FND-004, existing PR #265)
9. Provider and jackpot certification in sandbox (FND-006, FND-007, FND-014)
10. Admin capability alignment (FND-013)
```

Steps 1–2 are safe without new economics. Steps 3 and 4 need the product rules already written on #228 and #176; they do not need new prices. Step 5 uses prices and caps already in `CATALOGUE`. Steps 9–10 need credentials or an admin policy decision.

## PR groups

### PR-A — Club desk must name its target (FND-016)

**Severity:** P1. **Depends on:** nothing. **Do not merge from the audit branch.**

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
| [#272](https://github.com/wandemcphill/Global-Talent-Exchange/pull/272) Explicit desk auction and bid targets | FND-016 | PR-A acceptance. Draft PR open, not merged |

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
