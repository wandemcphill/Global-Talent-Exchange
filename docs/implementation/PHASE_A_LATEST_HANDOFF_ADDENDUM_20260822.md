# Phase A Latest Handoff Addendum

## Current state

1. The Treasury withdrawal request path resolves withdrawal fees from the persisted Admin commission policy. The old 10% fallback at the Treasury call site is removed and covered by resolver tests. `WalletService.request_payout()` still exposes a legacy default parameter of 1000 bps for defensive compatibility; direct application callers were scanned and Treasury is the only production caller outside the WalletService itself. This low-level default should eventually be removed or made mandatory once downstream compatibility is proven.

2. Hosted Coin-prize competitions freeze the competition fee basis at creation in competition metadata. Settlement must use that frozen value, not the current Admin rate.

3. Hosted competition routing uses `CoinAwareHostedCompetitionService`. Participant-funded FanCoin mode is compatibility-only and freezes its Admin fee policy at creation.

4. FanCoin gifting uses the canonical conversion adapter: sender spends FanCoin and recipient receives GTEX Coin. GTEX Coin cannot be gifted. The conversion carries durable provenance in `EconomicConversion`.

5. Agent Wallet is ledger-authoritative. The compatibility `AgentWallet` is a projection only, Agent spend/earn flows use deterministic system-owned Coin ledger accounts with idempotency keys, and performance rewards are funded from the non-negative Rewards Pool so unfunded rewards fail closed.

6. The Phase A migration chain is linear from `20260724_0106_player_potential` through `20260822_0112_hosted_competition_funding_contract`.

7. Runtime alignment, API contract, strict-live reality, and dependency audits pass on the current branch family. Fresh Quality Gates still need a clean branch-head run after the autofix commits.

8. Vercel has reported a separate frontend deployment issue in the broad CI. Treat that independently from the Phase A economic proof.

9. Agent ledger source tags `agent_boost_spend` and `agent_performance_earnings` are string-backed and require no native enum migration.

## Closure checklist

- [x] Admin-authoritative withdrawal fee
- [x] Coin/FanCoin currency separation
- [x] Durable FanCoin -> GTEX Coin conversion provenance
- [x] GTEX Coin non-giftability guard
- [x] Coin-hosted competition escrow and frozen fees
- [x] Agent Wallet zero/default fail-closed behavior
- [x] Agent Wallet ledger-authoritative spend/earn boundary
- [ ] DB-backed end-to-end hosted competition settlement proof
- [ ] Clean final branch-head Quality Gates
- [ ] Restore Quality Gates workflow to normal read-only configuration and remove temporary closure workflows
- [ ] Independent Phase A red-team sign-off
