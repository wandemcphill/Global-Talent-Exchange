# Phase A Latest Handoff Addendum

## Current state

1. The Treasury withdrawal request path now resolves withdrawal fees from the persisted Admin commission policy. The old 10% fallback at the Treasury call site is removed and covered by resolver tests. `WalletService.request_payout()` still exposes a legacy default parameter of 1000 bps for defensive compatibility; direct application callers were scanned and Treasury is the only production caller outside the WalletService itself. This low-level default should eventually be removed or made mandatory once downstream compatibility is proven.

2. Hosted Coin-prize competitions now freeze the competition fee basis at creation in competition metadata. Settlement must use that frozen value, not the current Admin rate.

3. Hosted Coin-prize runtime is routed through `CoinAwareHostedCompetitionService`, with dedicated GTEX Coin escrow and Coin settlement. DB-backed end-to-end create/escrow/settlement/withdrawal proof is still required before certification.

4. FanCoin gifting now uses the canonical conversion adapter across contexts: sender spends FanCoin and recipient receives GTEX Coin. GTEX Coin cannot be gifted. The conversion carries durable provenance in `EconomicConversion`.

5. Agent Wallet defaults now fail closed. A new canonical `AgentLedgerService` provides deterministic system-owned agent Coin accounts and ledger-backed spend/earn primitives. Full migration of `AgentStateStore.save_agent()` and `AgentManager.record_performance()` away from projection mutation is still required.

6. The Phase A migration chain is linear from `20260724_0106_player_potential` through `20260822_0112_hosted_competition_funding_contract`.

7. Current remote Quality Gates have already passed runtime alignment, API contract, strict-live reality, and dependency audits on earlier Phase A heads. Fresh runs are being queued against the latest head. The remaining known quality-work is formatter/lint certification plus runtime tests.

8. Vercel has reported a separate frontend deployment failure in the broad CI status. Treat it as a deployment investigation, not an economic-logic verdict.

## Required next work

- run and pass fresh branch-head Black/Ruff/pytest quality gates
- finish DB-backed Coin competition create/escrow/settlement/withdrawal tests
- integrate AgentLedgerService into AgentStateStore/AgentManager monetary mutations
- reconcile any historical Agent Wallet projection balances before removing their monetary authority
- independently audit Phase A before starting Club Shares or League work
