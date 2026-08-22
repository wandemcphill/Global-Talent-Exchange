# Phase A Latest Handoff Addendum

## Newly confirmed P0s

1. `WalletService.request_payout()` still carries a baked-in `withdrawal_fee_bps=1000` default. The active Admin reward policy already exposes `withdrawal_fee_bps`; the live path must resolve that policy instead of silently defaulting to 10%.

2. Hosted Coin-prize competitions now freeze the competition fee basis at creation in competition metadata. Settlement must use that frozen value, not the current Admin rate.

3. Hosted Coin-prize runtime is now routed through `CoinAwareHostedCompetitionService`, with dedicated GTEX Coin escrow and Coin settlement. Add DB-backed end-to-end tests before certification.

4. Quality Gates has passed runtime alignment, API contract, strict-live reality, and dependency audits. The remaining failure is Black formatting on 14 changed Phase A files.

5. Vercel is currently failing separately from the backend Quality Gates result. Treat it as a deployment investigation, not an economic-logic verdict.

## Required next work

- remove/route around the WalletService withdrawal fee default through Admin policy
- finish DB-backed Coin competition create/escrow/settlement/withdrawal tests
- format the Phase A changed files with the repository's pinned Black version
- run fresh branch-head Quality Gates after formatting
- complete Agent Wallet monetary migration to the canonical ledger
- independently audit Phase A before starting Club Shares or League work
