# Phase A: Withdrawal Contract

## Canonical rule

Only GTEX Coin (`LedgerUnit.COIN`) is a withdrawal asset.

GTEX FanCoin (`LedgerUnit.CREDIT`) is never withdrawable.

This rule is enforced by the backend withdrawal authority, not by frontend visibility.

## Current repository gap

The existing withdrawal control/reporting layer is policy-driven and currently contains a separate competition-withdrawal enable/disable switch plus a 10% seeded/default withdrawal fee. That does not by itself establish the new canonical rule that all GTEX Coin is withdrawal-eligible while FanCoin is never withdrawal-eligible.

Phase A must establish currency as the first gate:

```text
withdrawal request
    ↓
source ledger account
    ↓
unit == COIN ? continue : reject
    ↓
ordinary compliance/risk/settlement/provider controls
```

The feature-specific source (trade, competition, gift, share settlement, purchase, etc.) must not turn an otherwise valid COIN balance into a non-withdrawable balance.

## Fee policy

Withdrawal fees are separate from currency eligibility.

Admin may configure:

- normal-user platform withdrawal fee
- Coin Trader platform withdrawal fee
- external processing/provider fee
- minimum fee where applicable

The exact current rate is configuration, not business logic.

Every withdrawal request must snapshot:

- platform fee policy ID/version
- platform fee rate
- processor fee policy/rate if known
- gross requested amount
- total debit
- net payout amount

## Important distinction

A user may withdraw purchased GTEX Coin that has never been spent.

A user may withdraw earned GTEX Coin where the ordinary account/compliance/risk/settlement controls pass.

A user may not withdraw FanCoin, including purchased FanCoin or FanCoin winnings.

A FanCoin gift is not an exception because the recipient receives GTEX Coin through the gift conversion process. Once conversion completes, the resulting Coin follows normal withdrawal rules.

## Acceptance tests

1. CREDIT withdrawal rejected at API/service layer.
2. COIN withdrawal accepted when ordinary controls pass.
3. Purchased unused COIN withdrawal accepted.
4. Competition reward COIN withdrawal accepted.
5. Gifted COIN withdrawal accepted.
6. Share proceeds COIN withdrawal accepted.
7. User-hosted FanCoin prize withdrawal rejected.
8. Normal user fee and Coin Trader fee are distinct Admin policies.
9. Changing a future fee policy does not mutate historical withdrawal records.
10. Withdrawal request is idempotent and cannot double-debit.
