# CODEX Competition Discovery Performance Report

Verified on March 30, 2026.

## Scope

- GTEX-hosted discovery family: `GET /api/competitions`
- Hosted-competition discovery family: `GET /hosted-competitions`

## Baseline Failures

Source: [docs/CODEX_RUNTIME_PROOF_REPORT.md](/Users/ayomc/Desktop/GLOBAL%20TALENT%20EXCHANGE/docs/CODEX_RUNTIME_PROOF_REPORT.md)

- March 29, 2026 proof run:
  - `GET /api/competitions` timed out at the proof runner's ~20s budget.
  - `GET /hosted-competitions` timed out at the proof runner's ~20s budget.

## Profiling Method

- Runtime probe:
  - Local app boot against `gte_backend.db`
  - SQLAlchemy statement timing listeners
  - `fastapi.testclient.TestClient`
- Isolated list benchmark:
  - Temp SQLite DB
  - Only the tables required by the discovery paths
  - 12 seeded rows per family
  - Query count and total SQL time captured per list call

## Findings

### GTEX-hosted Discovery

- The timeout was not primarily caused by the list SQL itself.
- The first non-core request hit `LazyModuleMiddleware.ensure_modules_loaded()` and blocked on full module hydration.
- Pre-fix local first-request trace for `GET /api/competitions`:
  - `57,488.26ms` end-to-end
  - `233` SQL statements observed before response
  - only `214.54ms` of that was SQL execution time
  - app log recorded `app.modules.hydrate.complete` at `51,075.34ms`
- The list builder itself still had an avoidable N+1 pattern:
  - one `Competition` query
  - then per-competition queries for participant counts, rule sets, prize rules, and visibility rules
  - dynamic prize pool snapshots were also recomputed per competition when enabled
- Isolated pre-fix benchmark on 12 seeded competitions:
  - `61` SQL statements
  - `93.89ms` wall time

### Hosted-Competition Discovery

- The hosted list SQL path was already a single-pass query.
- The timeout symptom came from the same lazy module hydration wall when the endpoint was the first non-core request after readiness.
- Separate from the timeout, the hosted table family lacked discovery-oriented indexes for:
  - `visibility + created_at`
  - `host_user_id + created_at`
- Isolated post-fix hosted benchmark on 12 seeded hosted competitions still resolves in one query, so no N+1 fix was needed there.

## Changes Made

### GTEX-hosted Discovery

- Made the competition discovery family eager-loadable and bypass full lazy hydration on request entry:
  - [backend/app/modules.py](/Users/ayomc/Desktop/GLOBAL%20TALENT%20EXCHANGE/backend/app/modules.py)
- Batched list support data for `GET /api/competitions`:
  - participant counts grouped by `competition_id`
  - rule sets loaded in one query
  - prize rules loaded in one query
  - visibility rules loaded in one query
  - dynamic prize pool global context computed once for the list when needed
  - response contract preserved
  - [backend/app/services/competition_orchestrator.py](/Users/ayomc/Desktop/GLOBAL%20TALENT%20EXCHANGE/backend/app/services/competition_orchestrator.py)
- Added list-oriented dynamic prize pool context helpers:
  - [backend/app/services/dynamic_prize_pool_service.py](/Users/ayomc/Desktop/GLOBAL%20TALENT%20EXCHANGE/backend/app/services/dynamic_prize_pool_service.py)
- Added composite discovery indexes:
  - [backend/app/models/competition.py](/Users/ayomc/Desktop/GLOBAL%20TALENT%20EXCHANGE/backend/app/models/competition.py)
  - [backend/migrations/versions/20260330_0075_competition_discovery_perf_indexes.py](/Users/ayomc/Desktop/GLOBAL%20TALENT%20EXCHANGE/backend/migrations/versions/20260330_0075_competition_discovery_perf_indexes.py)

### Hosted-Competition Discovery

- Made the hosted discovery family eager-loadable and bypass full lazy hydration on request entry:
  - [backend/app/modules.py](/Users/ayomc/Desktop/GLOBAL%20TALENT%20EXCHANGE/backend/app/modules.py)
- Added composite hosted discovery indexes:
  - [backend/app/models/hosted_competition.py](/Users/ayomc/Desktop/GLOBAL%20TALENT%20EXCHANGE/backend/app/models/hosted_competition.py)
  - [backend/migrations/versions/20260330_0075_competition_discovery_perf_indexes.py](/Users/ayomc/Desktop/GLOBAL%20TALENT%20EXCHANGE/backend/migrations/versions/20260330_0075_competition_discovery_perf_indexes.py)

## Regression Coverage

- Added lazy-hydration bypass and GTEX list query-budget coverage:
  - [backend/tests/competitions/test_api_discovery.py](/Users/ayomc/Desktop/GLOBAL%20TALENT%20EXCHANGE/backend/tests/competitions/test_api_discovery.py)
- Added hosted discovery bypass and single-pass query-budget coverage:
  - [backend/tests/hosted_competitions/test_api_discovery.py](/Users/ayomc/Desktop/GLOBAL%20TALENT%20EXCHANGE/backend/tests/hosted_competitions/test_api_discovery.py)

## Before / After

### GTEX-hosted Discovery

| Probe | Before | After |
| --- | ---: | ---: |
| First request on local shipped runtime DB | `57,488.26ms` | `530.02ms` |
| Lazy module hydration on request path | yes | no |
| `app.state.modules_hydrated` after request | `True` | `False` |
| Isolated 12-row list benchmark SQL count | `61` | `5` |
| Isolated 12-row list benchmark wall time | `93.89ms` | `22.87ms` |

### Hosted-Competition Discovery

| Probe | Before | After |
| --- | ---: | ---: |
| March 29, 2026 proof result | timeout at ~20s | n/a |
| Fresh local request on shipped runtime DB | blocked by lazy hydration path in proof run | `242.77ms` |
| `app.state.modules_hydrated` after request | not preserved in proof run | `False` |
| Isolated 12-row list benchmark SQL count | single-pass path already | `1` |
| Isolated 12-row list benchmark wall time | not materially SQL-bound | `6.80ms` |

## Notes

- No visible response shape changes were introduced for either endpoint.
- The GTEX discovery family got the substantial ORM rewrite.
- The hosted family fix is primarily runtime access-path plus index coverage, because its list query was already cheap.
- `python -m py_compile` succeeded on all touched backend files.
- Targeted `python -m pytest` invocations did not complete in this environment, so the added tests were not executed end-to-end here.
