# Phase A: Economic Foundation

Branch: `phase/a-economic-foundation`

This phase establishes the canonical currency, fee, gifting, ledger, and economic-account rules before Competition Core, Club Economy, National Qualification, League, AI, or UX work is allowed to depend on them.

## Status

Architecture lock complete. The first reusable currency-policy primitive and the cross-currency conversion design are now on the branch. Runtime integration remains deliberately pending because FanCoin→GTEX Coin is a true multi-currency conversion and must not be faked inside one single-unit ledger transaction.

See `docs/implementation/PHASE_A_CROSS_CURRENCY_CONVERSION.md` before modifying Gift Engine accounting.

## Current confirmed defects / gaps

1. Gift currency is currently selected from `source_scope` and therefore user-hosted gifts can remain in FanCoin/CREDIT while GTEX-hosted gifts use COIN. This conflicts with the product rule that every successful gift debits FanCoin and credits withdrawable GTEX Coin to the recipient.
2. The hosted competition model is primarily FanCoin-funded today. A first-class host-funded GTEX Coin prize mode is required.
3. Competition fee seeds currently contain 10%/20% values; the intended current product policy is 30%, but the rate must come from Admin-configurable policy rather than code constants.
4. Agent Wallet remains a separate monetary authority and must be migrated to the canonical ledger.
5. KYC/compliance must not be derived from wallet-created status.
6. Withdrawal eligibility must be enforced from the currency authority, not only by the UI.

## Implementation order

### A1. Currency invariants

Implement explicit semantics:

- `CREDIT` = FanCoin = non-withdrawable.
- `COIN` = GTEX Coin = withdrawable.
- Gift input currency = FanCoin only.
- Gift output currency = GTEX Coin.
- GTEX Coin gifting is rejected.
- Currency semantics are never inferred from competition context.

The reusable primitive is `backend/app/economy/currency_policy.py`.

### A2. Gift conversion

Refactor Gift Engine accounting so a gift is a cross-currency economic transaction. Do not place CREDIT and COIN postings into one single ledger transaction if the ledger enforces unit consistency.

The required economic sequence is:

```text
Sender CREDIT debit
        ↓
platform fee/rake + conversion amount
        ↓
recipient COIN credit
```

Implement this as two balanced, atomically-linked unit transactions tied to one conversion identity. See the dedicated cross-currency design document for the ledger bridge and treasury implications.

The gift record must preserve source and destination currency semantics, not a single overloaded `ledger_unit` field.

Add regression tests for:

- user-hosted competition gift
- GTEX-hosted competition gift
- normal social gift
- attempted GTEX Coin gift
- withdrawal of gifted Coin
- duplicate/retry safety

### A3. Central economic fee policy

Create/use one authoritative fee policy service. At minimum the policy must support:

- gift rake
- competition fee
- competition booking fee
- share purchase fee
- share settlement fee
- withdrawal fee
- processing fee
- Coin Trader fee

Admin controls the active rate. Effective dating and versioning are required. Settled transactions retain the exact policy/rate applied.

Current competition cut: **30%** as Admin-configured policy. Do not hardcode 3000 bps in feature services.

### A4. Competition economic contracts

Add first-class competition funding mode:

- `FANCOIN_ENTRY_POOL`
- `HOST_FUNDED_GTEX_COIN_PRIZE`

For FanCoin mode:

- participants contribute FanCoin
- purse is FanCoin
- platform cut applies
- payout remains FanCoin/non-withdrawable

For GTEX Coin prize mode:

- host deposits GTEX Coin before competition opens
- Coin is escrowed
- participants do not contribute GTEX Coin
- platform cut applies
- winner receives withdrawable GTEX Coin

The host booking fee remains a separate single-payer transaction.

### A5. Agent Wallet migration

Do not allow an in-memory/dataclass balance to create or destroy monetary value.

Map agent economics to ledger accounts and use ledger transactions for:

- seed balance
- spend
- earnings
- boosts
- settlement
- payout

Default payout eligibility must be false until explicitly authorized.

### A6. Economic provenance

All economic transactions must preserve:

- currency/unit
- gross
- platform fee
- processing fee where applicable
- net
- source domain object
- fee policy ID/version
- ledger transaction ID
- idempotency key where applicable

Cross-currency conversions must additionally preserve:

- conversion ID
- source unit
- destination unit
- conversion rate/version
- source ledger transaction
- destination ledger transaction

### A7. Withdrawal contract

GTEX Coin is withdrawable subject to ordinary account/compliance/risk/provider controls. FanCoin is never withdrawable.

The withdrawal authority must reject CREDIT/FanCoin directly at the backend boundary.

Verify the external payout provider execution path before enabling automatic withdrawals in production.

## Required test matrix

### Currency

- FanCoin purchase -> CREDIT
- GTEX Coin purchase -> COIN
- unused COIN -> withdrawable
- unused CREDIT -> not withdrawable
- direct CREDIT withdrawal -> reject

### Gifts

- FanCoin gift -> COIN recipient
- user-hosted gift -> COIN recipient
- GTEX-hosted gift -> COIN recipient
- normal social gift -> COIN recipient
- GTEX Coin gift -> reject
- idempotent repeat gift -> no duplicate credit
- fee policy applied exactly once
- source/destination units are both recorded

### Competition

- FanCoin entry -> CREDIT escrow
- FanCoin purse payout -> CREDIT
- Coin prize -> COIN escrow
- Coin prize payout -> COIN and withdrawable
- participant-funded COIN purse -> reject
- 30% fee comes from policy, not hardcoded service logic

### Agent

- agent balance is ledger-derived
- concurrent spend cannot overspend
- duplicate settlement is idempotent
- payout eligibility false by default

### Withdrawal

- CREDIT withdrawal rejected
- COIN withdrawal accepted when ordinary controls pass
- platform fee and processor fee are explicit
- historical withdrawal retains applied fee policy

## Claude handoff

Claude should implement only Phase A on this branch until the Phase A audit is signed off. Do not start League, Club Shares, National Qualification, AI, or UX work from this branch before the economic foundation passes the matrix above.

Before handoff completion, report:

- files changed
- migrations added
- tests added/updated
- commands run
- commit SHA
- any blocked item
