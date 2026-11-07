# GTEX Remediation Roadmap

**Current Review Baseline:** `main` `a19893d44e3e3742dd7932880935a68cd2577d92` (2026-11-06).  
**Historical Baselines:** `bb6d82a9` (2026-10-27) and `45e29ef6` (2026-10-18).  
**Primary Reference:** `docs/audits/GTEX_COMPREHENSIVE_PLATFORM_AUDIT.md` (Version 3.0.0).  
**Player Universe Protection Policy:** STRICTLY ENFORCED & LOCKED (Zero player/regen/legend records altered, synthetic records created, or imports executed).

Nothing here is permission to merge without review. Each repair is an independent, reviewable pull request. Do not initiate broad rewrites. Do not run live deposits, withdrawals, jackpot funding, or payouts to close a row.

---

## 1. Current-Main Checkpoint (2026-11-06, `a19893d4`)

- **453 Commits Landed Since Baseline `bb6d82a9`:** Major additions include PR #343 (owner inbox & showroom desk actions), PR #344 (transfer hub & cash offer settlement), PR #345 (living world & narrative events), PR #346 (staff qualification policy & sister-club rules), PR #352 (canonical competition engine mapping), PR #377 (Cloudflare Pages frontend deployment), and PR #384 (Unit 2A Milestone 2 stadium arena & humanoid match gameplay).
- **Authentication & Turnstile (FND-001, NEW-AUTH-1):** Fully resolved in code. `verify_turnstile_token` is enforced across `/auth/signup`, `/auth/signup-creator`, and `/auth/signup-trader` in `backend/app/auth/router.py`. Flutter signup renders `GtexTurnstileChallengeWidget` (dev-bypass removed).
- **Showroom Purchase & Gifting (FND-002):** Fully resolved in code. `POST /owner/clubs/{id}/showroom/purchase` and `POST /owner/clubs/{id}/showroom/gift` exist in `backend/app/routes/owner_console/router.py` with idempotency key protection.
- **Owner Inbox Parity (FND-012):** Resolved. Flutter `/inbox` redirects directly to `/app/inbox` (`GtexOwnerInboxScreen`), matching React `/app/inbox` (`InboxPage.tsx`).
- **Unmounted Routes (FND-003):** Resolved. `club_sale_market` and identity routes are mounted via `backend/app/routes/clubs.py`.
- **Frontend Console Deployment (FND-004):** Resolved. Cloudflare Pages configuration for `playgtex.app` with Render `/console/` reverse-proxy rewrites is merged and operational.
- **Club Geography (FND-005):** Partially resolved. React `MyClubs.tsx` now uses `useClubLocation()` for dynamic country, region, and city selection. Signup lane unification (Issue #228) remains open.

---

## 2. Revised Dependency Order & Active Priorities

```text
0. Player Universe Data Protection — PERMANENT FREEZE: real players, regens, legends locked (NON-NEGOTIABLE)
1. Critical Routing Architecture — ARCH-001: strip /api/api/ route prefix doubling in backend/app/modules.py
2. State Persistence — NEW-STF-001: migrate ClubOpsStore in-memory singleton to SQLite/PostgreSQL
3. Settlement Correctness:
   - NEW-002: bind transfer hub offer settlement to persistent database offer price
   - NAT-NEW-1: enforce squad rental provenance on national team registrations
   - NEW-JRW-001: database uniqueness & idempotency on daily challenge reward settlements
4. Multi-Agent Integration Alignment:
   - Agent A (Issue #352): canonical competition engine integration & economic contract
   - Agent B (Issue #2): double-entry financial ledger idempotency certification
   - Agent C (Issue #136): ingestion worker recovery definition in render.yaml
   - Agent D: recovered remote branch is available in draft PR #390; run CI, authorization review, and migration checks before considering integration.
   - Agent I (PR #378): merge Campus GLB integrity reconciliation
5. Account Flow Unification (Issue #228):
   - Unify React signup into single user flow, deferring creator/trader roles to post-signup capabilities
```

---

## 3. Repair PR Groups & Status

### PR-A — Club Desk Must Name Its Target (FND-016)
- **Status:** **RESOLVED** via merged PR [#272](https://github.com/wandemcphill/Global-Talent-Exchange/pull/272).
- **Verification:** `perform_desk_action` strictly enforces `asset_id` on auctions and `listing_id` on bids.

### PR-B — Unmounted Routes (FND-003)
- **Status:** **RESOLVED**.
- **Verification:** `club_sale_market`, dynasty, and identity routes are mounted via `backend/app/routes/clubs.py`.

### PR-C — Turnstile Enforcement & Signup Unification (FND-001, FND-005, NEW-AUTH-1)
- **Status:** **PARTIALLY RESOLVED** (Security enforced; UI unification pending).
- **Completed:** Server-side Turnstile verification is enforced on all signup paths; Flutter client renders Turnstile challenge widget; `MyClubs.tsx` supports dynamic geography.
- **Remaining:** Unify React `AuthPage.tsx` into a single normal-user registration form per Issue #228.

### PR-D — One Staff Record & Club Ops Persistence (FND-009, NEW-STF-001)
- **Status:** **PARTIAL**.
- **Completed:** PR #346 separated qualifications for First Team Managers, Coaches, Analysts, and Medical staff in `staff_role_policy.py`.
- **Remaining Blocker (NEW-STF-001):** Migrate `ClubOpsStore` in `backend/app/services/club_ops_store.py` from an in-memory dictionary to persistent storage.

### PR-E — Prestige Buy and Gift (FND-002, NEW-PRESTIGE-1, NEW-PRESTIGE-2)
- **Status:** **RESOLVED IN CODE**.
- **Completed:** `POST /owner/clubs/{id}/showroom/purchase` and `POST /owner/clubs/{id}/showroom/gift` implemented with idempotency keys in `owner_console/router.py`.

### PR-F — Market Lanes & Transfer Hub (FND-010, FND-011, NEW-002, NEW-003)
- **Status:** **PARTIAL**.
- **Completed:** PR #344 added `/app/transfer-hub` (`TransferHub.tsx`), wire cash offer settlement, and seller listing validation.
- **Remaining Blocker (NEW-002):** In `backend/app/routes/transfers.py` (`accept_hub_offer`), ensure transfer settlement amounts cannot be overridden by caller payload parameters.

### PR-G — Inbox, Newsroom, Club HQ (FND-012, FND-015)
- **Status:** **RESOLVED**.
- **Completed:** PR #343 redirected Flutter `/inbox` to `/app/inbox` (`GtexOwnerInboxScreen`), matching React `/app/inbox` (`InboxPage.tsx`). Story feed active via `GET /api/story-feed`.

### PR-H — React Shell Deployment (FND-004)
- **Status:** **RESOLVED**.
- **Completed:** Cloudflare Pages deployment for `playgtex.app` and Render `/console/` reverse-proxy rewrites merged via PR #377.

### PR-I — Financial Ledger & Provider Sandbox (FND-006, FND-007, FND-014)
- **Status:** **IN PROGRESS (Agent B / Issue #2)**.
- **Notes:** Double-entry ledger architecture active. Production charges strictly forbidden. Sandbox webhook certification underway.

### PR-J — Admin Capability Gates (FND-013)
- **Status:** **PARTIAL**.
- **Completed:** Admin godmode capability enforcement active in `backend/app/services/admin_godmode/service.py`; brand advertising moderation screen added at `/app/admin/advertising`.

---

## 4. Multi-Agent Integration Coordination

| Workstream | PR / Issue | Immediate Dependency | Integration Action |
|---|---|---|---|
| **Agent A (Competitions)** | Issue #352 | Agent B financial contract | Align competition entry fees and prize escrow with double-entry ledger |
| **Agent B (Financial Ledger)** | Issue #2 | Paystack sandbox | Complete idempotency test suite for ledger entries |
| **Agent C (Ingestion Worker)** | Issue #136 | render.yaml | Deploy worker recovery spec; test exclusively against sandbox fixtures |
| **Agent D (Delegation Engine)** | Draft PR #390 | Current branch head `1057ba61` (original `53ef7331`) | Verify authorization boundaries, shared event backbone use, audit immutability, migration behavior, and PR CI |
| **Agent G (Windows Demo Package)** | Draft PR #393 (`1a4618ec`) | Interactive Windows desktop | Obtain genuine screenshot/recording evidence; visual acceptance remains blocked after Session 0 capture failure |
| **Agent H (Comprehensive Audit)** | Draft PR #392 (`e4306cf6`) | Status reconciliation | Review original audit and dated reconciliation separately before merging documentation |
| **M2 Match Experience** | Draft PR #391 (`7b2af23d`) | PR CI and event-order regression | Verify 3D/2D lifecycle, large-gap chronology, isolated SQLite fixtures, and authoritative clock |
| **Agent I (Campus GLB)** | PR #378 closed, not merged | Redundancy review | No merge required; work was found redundant against current `main` |

---

## 5. Explicitly Not in Scope

- Modifications of any kind to canonical player, regen, or legend records.
- Ingestion of synthetic players into the real database.
- Production real-money deposits, withdrawals, or payouts.
- Broad rewrites of the Flutter or React shells.
- Bypassing or disabling access controls and security checks.

---

## 6. How a Remediation Row Reaches VERIFIED COMPLETE

1. The client action calls a mounted and active route (no `/api/api/` doubling).
2. Server-side authorization rejects any actor without explicit authority.
3. The canonical service persists changes to PostgreSQL/SQLite, not volatile memory.
4. Subsequent reads return the persisted state with zero mock/sample fallbacks.
5. Automated pytest and client tests pass with assertions against actual responses.
6. Financial workflows are validated exclusively in sandbox environments with idempotency keys.


---

## 7. Remote Recovery Checkpoint — 2026-11-07

Canonical `main` remains `a19893d44e3e3742dd7932880935a68cd2577d92`. Recovery branches and draft PRs are proposals only; none is merged.

- **Agent D:** recovered original commit `53ef7331`; current branch head `87b7cdf8`, draft PR #390. CI and endpoint/migration review pending.
- **Agent G:** recovered Windows demo commit `1a4618ec`, draft PR #393. Genuine interactive Windows capture evidence remains outstanding.
- **Agent H:** four audit deliverables recovered and reconciled; current branch head `e4306cf6`, draft PR #392.
- **M2:** current branch head `7b2af23d`, draft PR #391. The jump-to-tail was removed, event-frame ordering regression added, and test lint fixed; current CI pending.

Do not treat agent-reported local tests as CI results. Do not merge until the respective review gates pass. Player, regen, and legend data remain protected.
