# Phase A: Claude Continuation Handoff

## Branch

`phase/a-economic-foundation`

## Continue from

Use the current branch head. PR #3 remains the containment PR against `main`.

## Work already established

- `GTEX_ECONOMIC_CONSTITUTION.md`
- `PHASE_A_ECONOMIC_FOUNDATION.md`
- `PHASE_A_CROSS_CURRENCY_CONVERSION.md`
- `PHASE_A_WITHDRAWAL_CONTRACT.md`
- `backend/app/economy/currency_policy.py`
- `backend/app/economy/conversion_service.py`
- `backend/app/economy/competition_funding_policy.py`
- `backend/app/models/economic_conversion.py`
- explicit gift source/destination currency fields on `GiftTransaction`
- migration `20260821_0107_economic_conversions`
- migration `20260821_0108_gift_currency_semantics`
- migration `20260822_0109_competition_fee_policy_default`
- migration `20260822_0110_agent_wallet_fail_closed`
- migration `20260822_0111_hosted_competition_template_fee_default`
- backend payout guard that rejects FanCoin at the `PayoutRequest` ORM boundary
- currency-policy tests
- conversion-reconciliation tests
- withdrawal-currency guard tests
- competition funding-policy tests
- Gift Engine runtime adapter and DB-backed conversion regressions
- Agent Wallet fail-closed defaults and state-store regression coverage

## Important ledger correction

`WalletService.append_transaction()` supports multiple ledger units in one transaction provided each currency independently nets to zero. Do not create separate transactions merely because a gift crosses currencies.

The intended FanCoin gift conversion is one atomic economic event:

```text
CREDIT:
  sender                 -gross
  platform fee           +fee
  conversion bridge      +(recipient_net)
  burn                   +burn, when configured

COIN:
  Coin bridge            -(recipient_net)
  recipient              +(recipient_net)
```

The `EconomicConversion` record provides durable provenance.

## Current state

### Gift Engine

Runtime integration is now routed through `CanonicalGiftEngineService`.

The canonical path deliberately forces every gift through the legacy FanCoin spend path first, regardless of `source_scope`, then converts only the recipient net amount into GTEX Coin in the same database transaction.

`source_scope` is contextual metadata only. It must never select the currency.

Additional GTEX-context rate limiting is preserved before the normalized legacy path executes.

This integration now has tests for both:

- user-hosted gifts
- GTEX-hosted gifts

The remaining requirement is fresh CI/runtime certification against the actual branch head.

### Withdrawal

The backend payout boundary rejects `LedgerUnit.CREDIT`. GTEX Coin remains the withdrawable economic unit.

### Competition

A constitutional funding policy exists and maps to the existing `entry_funded` / `host_funded_fixed` vocabulary.

The legacy hosted-competition service still contains an obsolete host-prepaid FanCoin path. Do not expose or extend that path. A withdrawable host-funded prize must be implemented as a separate GTEX Coin contract, with Coin escrow before the competition opens.

The template model/defaults have been aligned to the current 30% Admin policy, but the old service still contains legacy constants and needs runtime consolidation.

### Agent Wallet

The compatibility wallet now defaults to:

- balance = `0`
- payout eligibility = `false`

The persisted model defaults and state-store fallbacks are aligned. Existing historical Agent Wallet balances have intentionally not been mass-zeroed because their provenance has not yet been proven. The full ledger migration is still required.

## Next implementation priorities

### 1. Finish hosted-competition runtime enforcement

Create the proper two-mode contract:

- `FANCOIN_ENTRY_POOL` = CREDIT/FanCoin, participant-funded, non-withdrawable payout
- `HOST_FUNDED_GTEX_COIN_PRIZE` = COIN/GTEX Coin, host-funded, participant Coin contribution forbidden, withdrawable payout

Before a competition opens, verify the selected contract, currency, entry amount, and required host prize amount. Reject the obsolete host-prepaid FanCoin mode before any ledger mutation.

### 2. Centralize economic fees

Refactor feature services to use one Admin-configured fee policy. The current intended competition rate is 30%, but it must never be hardcoded.

Support separate platform and processor fees and retain historical policy/version data on settlement.

### 3. Finish Agent Wallet ledger migration

Move all agent monetary mutations to canonical ledger accounts. The current projection may continue to describe agent economics, but it must not be the monetary authority.

Add concurrency and idempotency tests.

### 4. Withdrawal execution certification

Prove the complete production path:

`COIN balance → withdrawal request → fee → provider payout → confirmation → reconciliation`.

Do not certify withdrawal readiness from the ORM guard alone.

## After Phase A

Do not start:

- League
- Club Season Shares
- National Qualification
- AI
- UX redesign

until Phase A has been independently audited and signed off.

## Required completion report

When you finish, report:

- exact files changed
- migration IDs
- tests added
- commands run and their results
- commit SHA
- blocked items
- any assumptions that still require product confirmation
