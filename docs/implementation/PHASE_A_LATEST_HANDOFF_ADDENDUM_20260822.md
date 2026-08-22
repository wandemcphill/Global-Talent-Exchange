# Phase A Latest Handoff Addendum

## Current state

1. The Treasury withdrawal request path now resolves withdrawal fees from the persisted Admin commission policy. The old 10% fallback at the Treasury call site is removed and covered by resolver tests. `WalletService.request_payout()` still exposes a legacy default parameter of 1000 bps for defensive compatibility; direct application callers were scanned and Treasury is the only production caller outside the WalletService itself. This low-level default should eventually be removed or made mandatory once downstream compatibility is proven.

2. Hosted Coin-prize competitions now freeze the competition fee basis at creation in competition metadata. Settlement must use that frozen value, not the current Admin rate.

3. Hosted competition routing uses `CoinAwareHostedCompetitionService`. The participant-funded FanCoin mode is now being hardened to freeze its Admin fee policy at creation too, eliminating mutable settlement economics in the compatibility path.

4. FanCoin gifting now uses the canonical conversion adapter across contexts: sender spends FanCoin and recipient receives GTEX Coin. GTEX Coin cannot be gifted. The conversion carries durable provenance in `EconomicConversion`.

5. Agent Wallet defaults now fail closed. A new canonical `AgentLedgerService` provides deterministic system-owned agent Coin accounts and ledger-backed spend/earn primitives. The active monetary mutation paths are now being moved behind that ledger boundary.

6. The Phase A migration chain is linear from `20260724_0106_player_potential` through `20260822_0112_hosted_competition_funding_contract`.

7. Current remote Quality Gates have already passed runtime alignment, API contract, strict-live reality, and dependency audits on earlier Phase A heads. Fresh runs are being queued against the latest head. The remaining known quality-work is formatter/lint certification plus runtime tests.

8. Vercel has reported a separate frontend deployment failure in the broad CI status. Treat it as a deployment investigation, not an economic-logic verdict.

9. Added Agent ledger source tags `agent_boost_spend` and `agent_performance_earnings`; these are string-backed ledger tags and do not require a native enum migration.

## Required next work

- run and pass fresh branch-head Black/Ruff/pytest quality gates
- finish DB-backed Coin competition create/escrow/settlement/withdrawal tests
- complete AgentLedgerService integration into AgentStateStore/AgentManager monetary mutations
- reconcile any historical Agent Wallet projection balances before removing their monetary authority
- retire any remaining live path into the legacy hosted competition economic implementation
- independently audit Phase A before starting Club Shares or League work

Remote finalizer trigger: commit Agent Wallet ledger-authoritative closure and hosted competition fee freeze.
