# Thorough Withdrawal Controls Pass

This pass revisited the withdrawal-controls implementation and hardened it in four ways:

1. **Policy enforcement**
   - Manual bank-transfer mode now blocks the gateway deposit endpoint.
   - Manual bank-transfer payouts now require `destination_reference` values beginning with `bank:`.
   - Withdrawal requests now carry explicit `processing_mode` and `payout_channel` metadata.

2. **Wallet-policy visibility**
   - `GET /api/wallets/adaptive-overview` now surfaces the active processor mode, bank-transfer toggles, and whether e-game winnings are withdrawable.
   - The adaptive insights list now includes deposit rail, withdrawal rail, and e-game cash-out status.

3. **Admin UX wording**
   - The god-mode admin screen now explains the operational difference between automatic gateway and manual bank-transfer payout handling more clearly.

4. **Tests**
   - Added focused backend tests for admin control updates, gateway/manual payment behavior, competition withdrawal enablement, bank-reference validation, and adaptive overview policy surfacing.

## Important note
Competition pool top-up control remains an admin control and audit surface in this pass. It is persisted and exposed, but this pass does not thread the percentage into competition fee-summary math globally because that requires a deeper service-context integration across competition creation/preview flows.
