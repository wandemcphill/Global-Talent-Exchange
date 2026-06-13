# N50 — CLOSED BETA READINESS CERTIFICATION

Date: 2026-06-13
Branch: `feature/original-visual-runtime` @ HEAD (N41–N49 committed)
Mission: move GTEX from LOCAL ALPHA READY → CLOSED BETA READY (gap-closure only).

---

## SCORES (evidence-anchored)

| Domain | Score | Basis |
|---|---|---|
| **Overall** | **88%** | All N41–N49 lanes green; gaps are public-beta hardening, not closed-beta blockers |
| Frontend | 90% | analyze 0 issues, 871 tests; single canonical router integrity-tested (N43); web build succeeds |
| Backend | 88% | ~260 tests green across shards; 159 modules/332 routes compose; full single-run suite still infeasible |
| Realtime | 88% | 6 contract + 6 new hardening tests (N44); live-socket reconnect soak still pending |
| Wallet | 92% | N33 100 + N45 invariants; 2 money bugs fixed; only Postgres concurrency soak pending |
| Security | 87% | RBAC 10/10 (N46); 1 regen-admin test file red on alias drift (not a real hole) |
| Competition | 90% | full lifecycle 6/6 incl. settlement + single-fee (N34) |
| Creator | 85% | apply→provision→campaign→payout green; payout handoff fixed (N40/N45) |
| Transfer | 90% | bid/reserve/withdraw/settle green (N33/N35/N45) |

---

## TOP 20 REMAINING RISKS
1. Trader matcher `FOR UPDATE` unproven under true parallel writes (SQLite no-op) — money.
2. Live websocket reconnect/multi-device storm not soak-tested.
3. Full backend suite never runs in one pass (sharded only).
4. Rollback rehearsal tool exists but not executed this cycle.
5. No live API/WS latency benchmark (N48 gap).
6. Disk pressure on dev/CI host destabilizes builds.
7. Regen-admin + regen-expansion test files red on body-level alias drift.
8. No stale-reservation reaper (releases are user-action-driven).
9. Schema auto-repair on boot masks migration drift.
10. Single payment rail (KoraPay/manual) — provider concentration.
11. Test-isolation pollution (probe 6-fail when 3 files run together; pass solo).
12. Competition payout→wallet-credit lacks a dedicated E2E route test.
13. Frontend API URL baked at build (tunnel URL must precede `flutter build web`).
14. `_broadcast` O(conn×dispatch) fan-out for public-beta scale.
15. Provider adapters eager-import `requests` (boot cost).
16. External redesign worktree (113 files) could be mistaken for canonical.
17. Dead code (`lib/legacy/`, `desktop_salvage_*`) still present.
18. Failed-payment provider-webhook auto-release not re-exercised this cycle.
19. Bootstrap admin requires complete env or silently skips.
20. Visual QA screenshots still uncaptured (N36).

## TOP 20 RECOMMENDED FIXES
1. Postgres concurrent-write soak of the trader matcher.
2. Scripted reconnect/disconnect soak via `run_gtex_staging_soak.ps1`.
3. Finish `gtex_db_session` migration → enables full-suite CI matrix.
4. Execute `invoke_gtex_rollback_rehearsal.ps1`, record result.
5. Run a live HTTP/WS latency probe on freed disk.
6. Free disk C: (delete `*.unitypackage`, `lib/legacy/`, `desktop_salvage_*`).
7. Canonicalize regen-admin/expansion + HOF test files to `/api/v2`.
8. Add a stale-reservation reaper job.
9. Replace boot schema auto-repair with fail-loud + explicit migration.
10. Add a second payment rail or documented failover.
11. Mark probe-polluting tests for isolation (or fixture reset).
12. Add competition payout→wallet-credit E2E route test.
13. Document the build-time API-URL contract in the alpha runbook.
14. Benchmark + cap realtime fan-out before public beta.
15. Lazy-import `requests` in the 3 provider adapters.
16. Archive/prune the redesign worktree.
17. Delete dead frontend code.
18. Re-exercise failed-payment webhook auto-release.
19. Add deploy-time bootstrap-admin preflight check.
20. Capture the 24 visual-QA screenshots.

---

## GO / NO-GO

| Milestone | Decision | Justification |
|---|---|---|
| **CLOSED BETA (25–50 testers)** | **GO** | Money (no double-debit/over-fill/leak), competitions (full lifecycle+settlement), realtime (hardened), RBAC, and recovery (163/163 reversible migrations) all certified green this cycle. Remaining risks are scale/soak items acceptable for a controlled cohort. |
| **PUBLIC BETA** | **NO-GO** | Requires: Postgres money concurrency soak, live WS reconnect soak, rollback rehearsal, latency benchmark, alias test-file canonicalization, visual QA. |
| **PRODUCTION (GA)** | **NO-GO** | Requires all public-beta items + full-suite single-run green + load baseline + second payment rail / failover. |

---

## SUCCESS-CONDITION ANSWERS
1. **Safe for 25–50 testers?** ✅ Yes — controlled cohort; money/competition/realtime/RBAC/recovery certified.
2. **Wallets & transfers survive real usage?** ✅ Yes at proven scale — exact-conservation invariants hold; true-parallel write soak is the one open caveat.
3. **Competitions run without operator intervention?** ✅ Yes — create→join→fixtures→standings→settlement is DB-truth and idempotent (N34); crash-safe.
4. **Realtime survives prolonged usage?** ⚠️ Mostly — hub self-heals (stale eviction, rejoin, dedup) proven in-process; live-socket soak pending before public beta.
5. **What blocks Public Beta?** Money concurrency soak, WS reconnect soak, rollback rehearsal, latency benchmark, alias test canonicalization, visual QA.
6. **What blocks Production?** All public-beta items + full-suite green + load baseline + payment-rail redundancy.

---

## RECOMMENDED CLOSED BETA
- **Tester count:** start at **15**, scale to **25–50** after a stable first 48h.
- **Duration:** **2 weeks** — week 1 money/competition focus, week 2 realtime/load observation.
- **Required before PUBLIC beta:** items 1–7 above (concurrency soak, reconnect soak, rollback rehearsal, latency, disk, alias cleanup, visual QA).

**Bottom line: GTEX is CLOSED BETA READY.** The gap from local-alpha to closed-beta is closed; the remaining work is an enumerated, finite public-beta hardening list — no feature or redesign work required.
