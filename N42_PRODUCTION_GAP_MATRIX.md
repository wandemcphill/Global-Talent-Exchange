# N42 — PRODUCTION GAP MATRIX (Phase C)

Date: 2026-06-13 · Branch `feature/original-visual-runtime` @ `b5b19730`

Scoring is **evidence-weighted**, anchored to: this session’s live verification (analyze, trader, release gate, guardrails, contract), the N40 `LOCAL_ALPHA_READINESS_REPORT` status matrix (Auth/Wallet/Transfer/Competition/Creator/Realtime = PASS), the N39 certification set, and the 2026-06-04 `FEATURE_DEPTH_SCORECARD`. Percentages express **production readiness**, not feature ambition. “Operational” = monitoring/runbooks/load/rollback for *that* surface. “Prod risk” = residual likelihood×impact of a launch defect (higher = worse).

| Surface | Feature % | Backend % | Frontend % | Operational % | Prod risk % | Primary evidence / gap |
|---|---:|---:|---:|---:|---:|---|
| **Auth** | 90 | 90 | 85 | 65 | 25 | LOCAL_ALPHA PASS (backend 5 / frontend 4). Gap: bootstrap-admin env preflight, session-hydration soak. |
| **Wallet / Escrow** | 90 | 92 | 85 | 70 | 30 | N33 100 tests + release-gate money lane PASS; fee-policy config-driven (N40). Gap: fee misconfig risk in prod env; payout E2E. |
| **Build-a-Son** | 70 | 72 | 70 | 50 | 40 | Regen/build backend present; N32 mostly green. Gap: regen-universe expansion + admin RBAC route errors (BACKEND_VERIFICATION). |
| **Regen Universe** | 65 | 68 | 65 | 45 | 45 | Lineage map wired (`bb88c36a`). Gap: `test_regen_universe_expansion_api` (story-DNA/youth-tournament) + `test_regen_admin_rbac` failures open. |
| **Club HQ** | 75 | 80 | 75 | 55 | 30 | Deep surface (formation, identity, ownership, ops). Gap: club_identity quick-link routing; unreachable-switch warnings historically. |
| **Squad** | 75 | 78 | 75 | 55 | 30 | Squad management present. Gap: barrel-export dedupe; realtime squad proof thin. |
| **Formation** | 78 | 80 | 78 | 55 | 25 | Formation contracts tested (`test_formation_contracts`, `_db_contracts`). Gap: device-level visual proof. |
| **Transfer Market** | 80 | 82 | 78 | 60 | 30 | Transfer + reservation 60+ tests; N35 77 passed. Gap: two auth-message edge cases + reserved-balance-first settlement edge (BACKEND_VERIFICATION). |
| **Competitions** | 75 | 80 | 78 | 55 | 35 | Lifecycle certified (N34); discovery/financial v2 routes work (verified `201`). Gap: **2 sibling route-test files red** (alias+envelope, N42 Phase B); E2E payout→wallet route test missing. |
| **Match Center** | 80 | 80 | 82 | 70 | 25 | Strongest island: backend-authoritative realtime, WS truth guards, blocked/degraded states; **2D only, 3D quarantined (0 prod imports — verified)**. Gap: monetization tests historically stale; WS collision check absent. |
| **Creator** | 70 | 75 | 65 | 55 | 35 | Creator backend 10 / frontend 9 PASS; withdrawal-fee handoff fixed (N40). Gap: several creator/market/stadium/share flows blocked or duplicated; scope decision needed. |
| **Trader** | 72 | 78 | 65 | 50 | 45 | **Coin-trader order book has REAL automated matching+settlement** (`trader/matching.py`: escrow legs, `settle_reserved_funds`/`settle_reserved_position_units`); `tests/trader` **19 passed**. Gap: **no concurrency proof under load**; P2P offer path settles manually; disputes partly audit-row-backed. |
| **Community** | 55 | 60 | 60 | 40 | 40 | Route+UI presence, thinner depth. Gap: little realtime/ops evidence; overflow fixes noted not visually proven. |
| **Admin** | 75 | 85 | 78 | 60 | 30 | Strong audit/finance/role-guard backbone; god-mode payment-rails truth tested. Gap: export/artifact blockers; route duplication; migration churn on boot. |
| **Realtime** | 70 | 75 | 70 | 45 | 45 | N35 contract-green; realtime auth/wallet/regen 4 passed. Gap: **reconnect/stale-session/multi-device soak never run**; WS route-collision protection not evident; lazy-WS hydration risk. |

## Cross-cutting (not a single surface)

| Axis | State | Evidence |
|---|---|---|
| API contract / alias | ✅ enforced live; frontend src 0 violations | N42 Phase B |
| Guardrails (no Paystack/crypto/Unity/3D/fixture-fake) | ✅ exit 0 | guardrail scan |
| Build hygiene | ✅ improved this session (dead `lib/legacy/`, `desktop_salvage_*` removed) | commits `3adb9854`, `b5b19730` |
| Full-suite single-pass proof | ❌ never completed | N39 #4 |
| Load / concurrency baseline | ❌ none | N39 #5/#8 |
| Disaster recovery / rollback rehearsal | ❌ unrun | N39 #15 |

## Weighted readiness (this matrix)

- **Backend truth** is the strongest axis (mature 159-module surface, only 29 stub/TODO markers across `backend/app`).
- **Operational readiness** is the weakest axis across nearly every surface (monitoring/soak/load/rollback), and is the dominant drag on public-beta/GA scores.
- **Highest residual product risk:** Trader (concurrency-unproven money path) and Realtime (soak-unproven) — both money/availability-critical.

> These supersede the 2026-06-04 “68% feature readiness” snapshot for the green-certified lanes (wallet/competition/match/trader), which have materially advanced; they do **not** revise the operational axis, which is unchanged.
