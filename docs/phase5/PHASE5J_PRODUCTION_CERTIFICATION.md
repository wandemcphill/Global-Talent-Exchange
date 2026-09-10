# Phase 5J — Production Certification Boundary

## Certification date

2026-09-10

## Current repository state

- Canonical production branch: `main`.
- Phase 5G realized P/L accounting is merged.
- Phase 5H admin-buyback boundary is documented and intentionally blocks executable System A buyback until authoritative platform-liquidity funding semantics are proven.
- Phase 5I historical-repair boundary is merged as a read-only, no-write contract.

## Production deployment evidence

Render production is configured around the `gtex-api` web service and `gtex-web` static site. Both follow `main` with auto-deploy enabled. The API is `gtex-api-opea.onrender.com`; the web origin is `gtex-web-tw6c.onrender.com`.

At the start of this certification pass, the API deployment for commit `529984bbf397cebb31fe21fab7a0b4a833606588` was live. The subsequent Phase 5H and Phase 5I documentation merges triggered new Render deployments, so the latest deployment must reach `live` before this pass can certify the current main revision in production.

A live Render signal also shows the `gtex-player-ingestion-worker` is suspended with `stuck_crashlooping`. This is a production-readiness blocker because player data freshness and downstream market/economic surfaces depend on real ingestion continuity.

## What is verified by repository and deployment configuration

1. The frontend production configuration points at the canonical Render API and explicitly uses live backend mode.
2. The backend production service runs migrations through the Render pre-deploy command.
3. Player-share trading is routed through System A rather than the retired System B order-book path.
4. Matchday performance changes published player valuation, while tradable `share_price_coin` remains economically separate.
5. Lifecycle freshness and historical-accounting paths fail closed when evidence is missing.
6. Phase 5H explicitly prohibits synthetic System B orders and unbalanced credit-only buybacks.
7. Phase 5I explicitly prohibits historical cost-basis reconstruction from present-day holdings, current share price, or current valuation.

## Certification gates

### Gate A — System A buy settlement

Must be demonstrated against the production database with a controlled account: authenticated buy -> balanced ledger settlement -> `PlayerShareHolding` update -> canonical `PlayerShareEvent` -> idempotent replay behavior.

**Status: BLOCKED**. The production GTEX Supabase project/database is not exposed through the currently available Supabase connection, so a database-backed certification cannot be honestly executed from this environment.

### Gate B — System A sell and realized P/L

Must be demonstrated with a controlled position: sell -> ledger settlement -> holding reduction -> canonical event -> weighted-average realized P/L calculation and reconciliation.

**Status: BLOCKED** for the same production-database access reason.

### Gate C — Price/value separation

Repository contracts and release gates enforce that matchday valuation changes do not rewrite tradable share price.

**Status: CODE VERIFIED; production mutation smoke test pending.**

### Gate D — Lifecycle and freshness

The current code requires evidence before a stream is marked LIVE and preserves UNKNOWN when evidence is unavailable.

**Status: CODE VERIFIED; live provider/worker continuity remains a deployment concern.**

### Gate E — Historical repair

The first Phase 5I implementation is explicitly read-only and classifies evidence quality without mutating holdings or ledger data.

**Status: CONTRACT VERIFIED; production audit execution pending database access.**

### Gate F — Admin buyback

Executable System A buyback is not certified. Funding must be a named, balanced Coin-denominated liquidity account before implementation.

**Status: BLOCKED by accounting policy/funding-source proof.**

### Gate G — Production worker continuity

All production workers that feed product freshness must be healthy and running.

**Status: FAIL.** `gtex-player-ingestion-worker` is currently suspended by Render with `stuck_crashlooping`.

### Gate H — Automated release certification

The repository contains Quality Gates, Phase A Economic Regressions, Final Platform Certification, and a manual Production Deploy workflow. Recent PR workflow runs in this environment returned failures, and job logs were not retrievable through the available GitHub connector. Therefore the failures cannot be safely reclassified as code, infrastructure, or configuration without further evidence.

**Status: NOT CERTIFIED.**

## Required evidence before a final production-ready declaration

- Current `main` Render API and web deployments confirmed `live` after the latest merge.
- Production GTEX database access through the real Supabase/Postgres project or an equivalent audited production connection.
- Controlled authenticated buy/sell smoke transaction with before/after ledger, event and holding evidence.
- Confirmed realized P/L output for a position with complete historical settlement evidence.
- Healthy player ingestion worker with a successful fresh ingestion cycle.
- Production certification of the KoraPay/payment callback surface where applicable.
- Resolution or explicit classification of the current GitHub release-gate failures.
- A named, balanced admin-buyback liquidity account before Phase 5H runtime implementation.

## Final decision

**GTEX is not yet production-certified.**

The software architecture and major Phase 5 economic contracts are materially hardened, but certification stops at the boundary where production database evidence, worker health, and authoritative admin-liquidity semantics are required. No data mutation, historical repair, or synthetic trading path should be introduced merely to manufacture a green certification result.
