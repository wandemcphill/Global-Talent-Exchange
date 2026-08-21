# Phase A: FanCoin → GTEX Coin Conversion Accounting

## Purpose

FanCoin gifting is a cross-currency economic event. It must not be implemented by changing the recipient ledger unit on an otherwise single-currency ledger transaction.

The wallet ledger is unit-specific. `CREDIT` and `COIN` are separate economic units, so the gifting flow must preserve both legs and connect them with a common conversion reference.

## Canonical gift economics

For a gift with gross FanCoin amount `G` and active platform fee `F`:

```text
Sender FanCoin debit          G
Platform FanCoin revenue      F
Conversion amount             G - F

Recipient GTEX Coin credit    G - F
```

The exact amount may be further adjusted by an explicitly approved gift rule/bonus policy, but the source and destination currencies remain fixed:

```text
input  = FanCoin / CREDIT
output = GTEX Coin / COIN
```

## Ledger implementation requirement

Do **not** create one ledger transaction containing both CREDIT and COIN entries.

The current ledger model is unit-specific. Implement the conversion as two balanced unit transactions tied to one immutable conversion reference:

### Conversion leg A: FanCoin

```text
Sender CREDIT           -G
Platform CREDIT revenue +F
Conversion/issuance     +(G-F)
```

### Conversion leg B: GTEX Coin

```text
Conversion/issuance     -(G-F)
Recipient COIN          +(G-F)
```

Both transactions share:

- `conversion_id`
- `gift_transaction_id`
- source user
- recipient user
- gross FanCoin amount
- platform fee
- destination Coin amount
- fee-policy ID/version
- conversion rate/version
- idempotency key lineage

The conversion/issuance account is a system economic bridge. It must never become an unexplained user balance or a manually editable wallet amount.

## Treasury implication

The FanCoin gift conversion creates a withdrawable GTEX Coin liability. This is intentional product behavior, but it must be visible to Treasury and reconciliation systems.

A later treasury phase must be able to reconcile:

```text
FanCoin consumed through conversion
vs
GTEX Coin issued through conversion
vs
platform treasury backing / Coin liabilities
```

Do not paper over this by assigning the recipient the same `CREDIT` unit.

## Required data provenance

`GiftTransaction` should retain both:

- `source_ledger_unit = CREDIT`
- `destination_ledger_unit = COIN`

and ideally:

- `conversion_id`
- `conversion_rate`
- `platform_fee_amount`
- `recipient_coin_amount`
- `source_ledger_transaction_id`
- `destination_ledger_transaction_id`
- `fee_policy_id`
- `fee_policy_version`

The existing `ledger_unit` field is insufficient for the new cross-currency semantics and should not be overloaded to mean both currencies.

## Idempotency

A retry must never create a second Coin credit.

The canonical idempotency identity should cover the conversion, not merely the UI request. For example:

```text
fan-gift-conversion:{gift_transaction_id}
```

The source and destination ledger transactions must be linked to the same conversion identity and be committed atomically at the database transaction boundary.

## Reversal/refund semantics

A settled gift conversion cannot simply be deleted.

A valid reversal must create compensating ledger transactions linked to the original conversion:

```text
Recipient COIN debit
Conversion bridge COIN credit

Conversion bridge CREDIT debit
Platform/source-side CREDIT compensation
```

Any reversal policy must explicitly state whether already-withdrawn Coin can be clawed back, held, or recovered through a treasury/negative-liability workflow. Do not invent this inside the gift service.

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
5. Source and destination unit fields remain explicit.
6. Platform fee is applied exactly once.
7. Recipient Coin amount equals the configured post-fee conversion amount.
8. Retrying the same gift does not create another Coin credit.
9. Source and destination ledger transactions share one conversion ID.
10. Both currency legs commit atomically or neither commits.
11. Existing gift abuse/collusion controls remain active.
12. Gift context never changes the currency semantics.

## Non-goals for Phase A

Do not add dynamic exchange rates, market pricing, or trader pricing to gifting. Gift conversion is a fixed platform-defined conversion unless a later approved policy explicitly changes it.
