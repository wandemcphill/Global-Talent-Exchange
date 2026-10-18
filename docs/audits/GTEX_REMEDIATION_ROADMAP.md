# GTEX remediation roadmap (refresh)

Baseline: `main` `6711a545f06ec6bda28a03379028fb8d63c50a3c`, audit refresh 2026-10-18 on branch `cursor/gtex-platform-audit-refresh-eeeb`. Findings: `docs/audits/GTEX_COMPREHENSIVE_PLATFORM_AUDIT.md`.

Nothing here is permission to merge without review. Do not start a shell rewrite. Do not run live deposits, withdrawals, jackpot funding, or payouts to close a row.

## Dependency order

```text
1. [DONE on main] Stop unsafe implicit desk money actions (FND-016 / #272)
2. [DONE in code] Publish React at /console (FND-004 / #265) — live Render check still open (#263)
3. [PARTIAL this PR] Turnstile honesty + React normal-account signup (FND-001 / FND-005 / #274)
4. [PARTIAL this PR] Prestige purchase/gift UI on existing catalogue (FND-002 / #273)
5. Reframe #275: settlement review of mounted club-sale instant-sell/transfer (was “unmounted”)
6. Flutter signup collapses to one normal account (#228 / #274 remainder)
7. One staff authority (FND-009 / #276 / #169 / #176) — product decision on GM/HYD first
8. Market and card lanes (FND-010, FND-011)
9. Inbox and newsroom route honesty (FND-012, FND-015)
10. Provider and jackpot certification in sandbox (FND-006, FND-007, FND-014)
11. Admin capability alignment (FND-013)
```

## PR groups

### PR-A — Club desk targets (FND-016) — DONE

Merged [#272](https://github.com/wandemcphill/Global-Talent-Exchange/pull/272). Re-verified: `pytest backend/tests/club_legacy/test_full_desk.py` passed in this refresh.

### PR-H — React at `/console` (FND-004) — CODE DONE

Merged [#265](https://github.com/wandemcphill/Global-Talent-Exchange/pull/265). Remaining acceptance is operational: Blueprint sync, `/` still Flutter, `/console/` React, refresh `/console/login`, API calls hit `gtex-api`. Track on [#263](https://github.com/wandemcphill/Global-Talent-Exchange/issues/263).

### PR-C′ — Signup honesty (FND-001, FND-005) — PARTIAL IN THIS REFRESH

**Shipped in audit refresh PR:**

- Flutter user signup no longer sends `turnstileToken: 'dev-bypass'`.
- Copy no longer claims a security check “runs automatically”.
- React `/signup` is normal-account-first (no club fields, no hardcoded Nigeria).
- React club create collects country code and city.

**Still open (#274 / #228):**

- Flutter `/account/select` still offers creator and trader registration products.
- Real Turnstile widget when `GTE_TURNSTILE_SECRET_KEY` is set.
- Collapse claim vs `POST /api/clubs` documentation without inventing a third path.

**Tests:** Flutter widget coverage for showroom/owner console green; auth suite has a pre-existing trader proof-of-address failure unrelated to this change.

### PR-E′ — Prestige buy and gift (FND-002) — PARTIAL IN THIS REFRESH

**Shipped:**

- Flutter `OwnerConsoleApi.purchaseCatalogueSku` / `offerShowroomGift` → `/owner/legacy/{club}/market/purchases|gifts`.
- Showroom Buy/Gift controls for catalogue and owned exhibits.
- Widget test: catalogue buy sends sku.
- Backend phase4 suite: 6 passed.

**Still open (#273):**

- React prestige UI.
- Production `club_legacy` flag confirmation.
- Gift recipient UX beyond free-text ref (product decision).

### PR-B′ — Club-sale settlement review (was FND-003 / #275)

**Do not treat as “unmounted”.** `club_sale_market`, dynasty, reputation, and trophies are included from `backend/app/routes/clubs.py`.

**Work:** Review instant-sell and transfer settlement against the economic constitution. Add IDOR/ownership tests if missing. Hide or gate UI only if product decides the market is not shipping.

### PR-D — One staff record (FND-009 / #276)

Unchanged. **Decision required:** Is General Manager a new `evaluate_staff_role` key, an alias of `first_team_manager`, or retired? Do not invent wages.

### PR-F — Market lanes and cards (FND-010, FND-011)

Unchanged. Label four lanes; fix `/player-cards` redirect; shared card header. Regen seed integrity stays on #228.

### PR-G — Inbox / newsroom / Club HQ (FND-012, FND-015)

Flutter owner inbox must call `GET /owner/inbox`. Newsroom stays on story-feed.

### PR-I — Money certification, sandbox only (FND-006, FND-007, FND-014)

Owner-supplied sandbox credentials. Forbidden: live charges. Decide jackpot funding (admin vs cron) without inventing schedules that mint money.

### PR-J — Admin gates (FND-013)

Align Flutter/React admin helpers with `get_current_admin` / capability packs.

## Explicitly not in this programme

- Phase 6G from #176 comments.
- New currencies, fees, prize amounts, card rarities, or catalogue SKUs.
- Replacing Flutter.
- Merging PRs from the agent.
- Editing historical migrations to hide failures.
- Triggering ingestion backfill, jackpot contribution, or payout release against production.

## Certification log (this refresh)

| Check | Result |
| --- | --- |
| Desk + console publish + deployment contract pytest | 25 passed |
| Phase4 prestige pytest | 6 passed |
| Auth signup/turnstile subset | 5 passed, 1 pre-existing fail |
| Flutter showroom + owner console tests | 25 passed |
| React production build `PUBLIC_URL=/console` | success |
| Authenticated browser matrix | not run |
| Live payment / jackpot / Render `/console` URL | not verified |
