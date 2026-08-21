# Phase A: Claude Continuation Handoff

## Branch

`phase/a-economic-foundation`

## Continue from

Current head is the same branch used by PR #3.

## Work already established

- `GTEX_ECONOMIC_CONSTITUTION.md`
- `PHASE_A_ECONOMIC_FOUNDATION.md`
- `PHASE_A_CROSS_CURRENCY_CONVERSION.md`
- `PHASE_A_WITHDRAWAL_CONTRACT.md`
- `backend/app/economy/currency_policy.py`
- `backend/app/economy/conversion_service.py`
- `backend/app/models/economic_conversion.py`
- explicit gift source/destination currency fields on `GiftTransaction`
- migration `20260821_0107_economic_conversions`
- migration `20260821_0108_gift_currency_semantics`
- backend payout guard that rejects FanCoin at the `PayoutRequest` ORM boundary
- currency-policy tests
- conversion-reconciliation tests
- withdrawal-currency guard tests

## Important implementation correction

`WalletService.append_transaction()` already supports multiple ledger units in one transaction provided each unit independently nets to zero. Do not introduce two separate ledger transactions just because the conversion crosses currencies.

The intended FanCoin gift conversion is one atomic multi-unit transaction:

```text
CREDIT:
  sender                 -gross
  platform fee           +fee
  conversion bridge      +(gross-fee-burn)
  burn                   +burn

COIN:
  Coin bridge            -(gross-fee-burn)
  recipient              +(gross-fee-burn)
```

The `EconomicConversion` record provides durable provenance.

## Current state

The currency model and withdrawal boundary are implemented. Gift Engine runtime integration is the remaining P0 within the gifting slice.

Do not reintroduce context-dependent currency selection. `source_scope` is contextual metadata only. It must never select FanCoin versus GTEX Coin.

## Next implementation priorities

### 1. Integrate Gift Engine

Replace the current context-dependent `ledger_unit` behavior with the canonical gift path:

- input must always be FanCoin
- GTEX Coin cannot be gifted
- recipient always receives GTEX Coin
- user-hosted/GTEX-hosted context must not alter currency semantics
- preserve gift abuse/collusion controls
- preserve idempotency
- populate `source_ledger_unit = CREDIT`
- populate `destination_ledger_unit = COIN`
- populate `economic_conversion_id`, `conversion_rate`, and shared ledger transaction reference

The legacy `GiftTransaction.ledger_unit` field is compatibility-only and must not drive new accounting.

### 2. Add actual integration tests

Do not stop at pure policy tests. Add DB-backed tests that prove:

- user-hosted gift: CREDIT debited, COIN credited
- GTEX-hosted gift: CREDIT debited, COIN credited
- normal social gift: CREDIT debited, COIN credited
- GTEX Coin gifting rejected before ledger mutation
- platform fee applied once
- retry is idempotent
- ledger transaction balances independently by unit
- recipient Coin is visible to withdrawal logic
- conversion record links to the same ledger transaction

### 3. Keep the backend withdrawal currency guard

Withdrawal authority rejects `LedgerUnit.CREDIT` directly at the payout model boundary. Do not rely on frontend visibility. Preserve ordinary compliance/risk/provider checks for COIN.

### 4. Centralize economic fees

Refactor feature services to use one Admin-configured fee policy. The current intended competition rate is 30%, but it must never be hardcoded.

The policy must support separate platform and processor fees and retain historical policy/version data on settlement.

### 5. Add first-class competition funding modes

Implement:

- `FANCOIN_ENTRY_POOL`
- `HOST_FUNDED_GTEX_COIN_PRIZE`

For host-funded Coin prizes, escrow the host's Coin before the competition opens. Participant-funded withdrawable Coin pools are prohibited.

### 6. Agent Wallet migration

Move all agent monetary mutations to ledger accounts. Default payout eligibility must be false. Add concurrency and idempotency tests.

## Do not do yet

Do not start:

- League
- Club Season Shares
- National Qualification
- AI
- UX redesign

until Phase A is audited and signed off.

## Required completion report

When you finish, report:

- exact files changed
- migration IDs
- tests added
- commands run and their results
- commit SHA
- blocked items
- any assumptions that still require product confirmation
