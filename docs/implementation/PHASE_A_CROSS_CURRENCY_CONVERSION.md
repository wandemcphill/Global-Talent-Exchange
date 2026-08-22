# Phase A: FanCoin → GTEX Coin Conversion Accounting

## Purpose

FanCoin gifting is a cross-currency economic event. It must not be implemented by simply changing the recipient currency label or by treating the recipient as still holding FanCoin.

The GTEX ledger supports multiple units within one transaction, but it requires each unit to net to zero independently. Therefore a FanCoin→GTEX Coin gift can be represented as **one atomic ledger transaction with two balanced currency legs**, connected by a durable conversion record.

## Canonical gift economics

For a gift with gross FanCoin amount `G` and active platform fee `F`:

```text
CREDIT leg
Sender FanCoin debit          -G
Platform FanCoin fee           +F
Conversion bridge FanCoin     +(G-F)
--------------------------------
CREDIT net                      0

COIN leg
Conversion bridge GTEX Coin    -(G-F)
Recipient GTEX Coin credit     +(G-F)
--------------------------------
COIN net                        0
```

The result is:

```text
sender loses G FanCoin
platform receives F FanCoin economics
recipient receives G-F GTEX Coin
```

The exact fee/bonus calculation remains subject to the active Admin economic policy, but the currency direction is fixed:

```text
input  = FanCoin / CREDIT
output = GTEX Coin / COIN
```

## Ledger implementation requirement

Use the existing `WalletService.append_transaction()` unit-balanced ledger behavior.

Do **not** create a same-unit recipient credit in FanCoin.

Do **not** create an unbalanced cross-currency transaction.

The transaction must contain:

### CREDIT leg

- sender debit
- platform FanCoin fee revenue credit
- FanCoin conversion bridge credit

### COIN leg

- GTEX Coin conversion bridge debit
- recipient GTEX Coin credit

The ledger already validates each unit independently. The conversion bridge is a system account that connects the two balanced unit legs inside the same atomic database transaction.

## Durable conversion record

`EconomicConversion` links the economic event to the ledger transaction and stores:

- conversion ID/key
- type
- status
- source user
- recipient user
- gift transaction
- source unit
- destination unit
- source amount
- platform fee amount
- destination amount
- conversion rate/version
- ledger transaction ID / conversion reference
- fee policy ID/version
- idempotency key
- metadata

The `GiftTransaction` record should additionally retain source and destination currency semantics. Do not overload its existing single `ledger_unit` field to mean both currencies.

## Treasury implication

The FanCoin gift conversion creates a withdrawable GTEX Coin liability. The bridge account is intentionally permitted to reflect that economic liability, while treasury/reconciliation systems must separately track whether the resulting Coin liability is backed and settled according to the platform's economic policy.

This is not a reason to keep the recipient in FanCoin. It is a reason to make the conversion explicit and auditable.

A later treasury phase must reconcile:

```text
FanCoin consumed through conversion
vs
GTEX Coin issued through conversion
vs
platform liquidity / Coin liabilities
```

## Idempotency

A retry must never create a second Coin credit.

Use a canonical conversion idempotency identity, for example:

```text
fan-gift-conversion:{gift_transaction_id}
```

The ledger transaction itself should be idempotent and the `EconomicConversion` record should have a unique conversion key/idempotency key.

## Reversal/refund semantics

A settled gift conversion cannot simply be deleted.

A valid reversal must create a compensating multi-unit ledger transaction linked to the original conversion. The exact treatment of already-withdrawn Coin must be governed by a future explicit recovery policy and must not be invented inside the gift service.

## User-visible semantics

The recipient should see:

```text
Gift received
+70 GTEX Coin

Source: FanCoin gift
Withdrawable: Yes
```

The sender should see:

```text
Gift sent
-100 FanCoin
```

Do not describe the recipient amount as FanCoin.

## Test invariants

1. User-hosted gift consumes CREDIT and creates COIN.
2. GTEX-hosted gift consumes CREDIT and creates COIN.
3. Normal social gift consumes CREDIT and creates COIN.
4. Attempted COIN gift is rejected before any ledger mutation.
5. CREDIT postings net to zero.
6. COIN postings net to zero.
7. Platform fee is applied exactly once.
8. Recipient Coin amount equals the configured post-fee conversion amount.
9. Retrying the same gift does not create another Coin credit.
10. Source and destination unit semantics are persisted.
11. The ledger transaction and `EconomicConversion` record share one conversion identity.
12. Both currency legs commit atomically or neither commits.
13. Existing gift abuse/collusion controls remain active.
14. Gift context never changes currency semantics.

## Non-goals for Phase A

Do not add dynamic exchange rates, market pricing, or trader pricing to gifting. Gift conversion uses the fixed platform-defined 1:1 Coin/FanCoin unit relationship unless a later approved product policy explicitly changes it.
