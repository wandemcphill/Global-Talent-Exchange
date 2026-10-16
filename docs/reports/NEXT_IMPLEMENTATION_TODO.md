# GTEX Next Implementation TODO

## Expansion execution map
- See `docs/EXPANSION_EXECUTION_WAR_MAP.md` for the repo-anchored backlog across infra, payments, economy, gameplay, AI, security, admin, and growth.
- Default order: `Tranche 1` money safety and operator controls, `Tranche 2` live scale and integrity, `Tranche 3` gameplay and growth loops, `Tranche 4` economy governance and ML.

## Withdrawal rules to implement
- Allow users to withdraw **e-game winnings and rewards** from the app wallet.
- Apply a **10% platform fee** on every withdrawal.
- The 10% withdrawal fee should apply to both:
  - trade withdrawal requests
  - e-game winnings or reward withdrawal requests
- Show users the gross amount, 10% platform fee, and net payout before confirmation.
- Reflect the fee clearly in wallet ledger history and withdrawal receipts.
- Ensure admin/audit surfaces can review withdrawal fee deductions separately from principal payouts.

## Validation still required locally
- Run `flutter analyze`
- Run `flutter test`
- Run backend test suite
- Verify all major app routes manually
