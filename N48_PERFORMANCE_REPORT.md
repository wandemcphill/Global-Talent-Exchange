# N48 — PERFORMANCE BASELINE

Date: 2026-06-13
Branch: `feature/original-visual-runtime` @ `18a49f74`
Verdict: **Baseline captured from real evidence. Closed-beta-adequate; CI/test-DB cost is the dominant bottleneck, not runtime app latency.**

## Measured (evidence-backed)

| Metric | Measurement | Source |
|---|---|---|
| Backend app composition (cold) | **159 modules / 332 routes**, ~18.7s `app.modules.register.complete` | `.runtime/local_alpha_backend.err.log`, N37 |
| Backend standalone compose (warm-ish) | ~24.9s (`backend_app_composes` gate check) | `.runtime/n37_gate2.log` |
| Backend boot incl. migrations (fresh SQLite) | >90s first boot (alembic applies 95 migrations on empty DB) | N40 boot probe |
| Flutter web build | **479.2s** (`flutter build web --no-pub`) | N38, N40 |
| Flutter analyze | 881s (0 issues) | `.runtime/n31_analyze.log` |
| Realtime hub ops (in-proc) | 6 hardening tests in 48.4s incl. cold import | `.runtime/n44_hardening.log` |
| Money invariants (incl. matching) | 3 tests, 68.8s incl. cold import | `.runtime/n45_money.log` |

## Per-shard test latency (CI planning signal)
| Shard | Tests | Wall |
|---|---|---|
| core/startup | 21 | 426s |
| money lane | 100 | 813s |
| realtime+transfer | 77 | 417s |
| competition lifecycle | 6 | 175s |
| auth router (solo) | 13 | 933s |
| probe (3 files) | 24 | 1567s |

## Top bottlenecks (ranked, evidence-based)

| # | Bottleneck | Evidence | Severity |
|---|---|---|---|
| 1 | **Per-test DB schema build** — 567-table `create_all` ~25–32s; dominates every cold test | project memory; shard times | P1 (CI) |
| 2 | Cold Python import of `app.main` (159 modules) ~18–30s | boot logs | P1 (CI/boot) |
| 3 | Fresh-DB migration boot (95 alembic revisions) >90s | N40 | P2 (first-boot only) |
| 4 | Flutter web build ~8min | N38 | P2 (build, not runtime) |
| 5 | Disk C: ~97–80% full → slow I/O on imports/builds | memory, N38 | P2 (ops) |
| 6 | `flutter analyze` ~15min | N31 | P3 (CI) |
| 7 | `requests` eager import in 3 provider adapters | memory | P3 (boot) |
| 8 | OTel imports (already made lazy) | memory `43ffca58` | resolved |
| 9 | Realtime `_broadcast` O(connections×dispatches) | `service.py` | P3 (scale) |
| 10 | No HTTP-latency benchmark harness exists | — | P2 (gap) |
| 11–20 | Per-endpoint API latency, competition/wallet/transfer query latency, websocket message latency | **NOT MEASURED** — no live load probe run this cycle | gap |

## Honest gaps
- **Live API latency, query latency, and websocket latency were NOT measured** — no running-server load probe was executed (would require a stable local server + `tools/load/` harness on freed disk). Reporting these as estimates would violate "evidence only," so they are marked NOT MEASURED.
- The measured bottlenecks are overwhelmingly **CI/build/boot** costs, not user-facing runtime latency. For closed beta (25–50 users) this is acceptable; the app, once booted, serves 332 routes normally.

## Recommendations
1. **Finish `gtex_db_session` rollback-fixture migration** (keystone CI win — eliminates per-test `create_all`).
2. Run a real HTTP/WS latency probe against a booted local server on freed disk before public beta (fills the gap rows 11–20).
3. Keep the app warm in alpha (don't cold-boot per session — migration cost is one-time).
