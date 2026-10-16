# GTEX Economic Constitution

Status: **Phase A architecture lock**

This document is the authoritative product/engineering rule set for GTEX currency and economic flows. Feature code must not invent conflicting currency, fee, withdrawal, or settlement semantics.

## 1. Currency model

### GTEX FanCoin

FanCoin is the non-withdrawable platform consumption currency.

Allowed uses include:

- gifting
- eligible user-hosted competition participation
- Fast Match / platform gameplay
- other explicitly approved non-withdrawable consumption flows

A user may purchase FanCoin, but purchased FanCoin is not withdrawable.

### GTEX Coin

GTEX Coin is the withdrawable economic currency.

GTEX Coin may originate from:

- direct purchase
- competition winnings/rewards
- club share proceeds
- club-season settlement
- player/asset economic activity where explicitly approved
- receipt of a FanCoin gift
- other approved economic rewards

GTEX Coin is withdrawable subject to the account's ordinary withdrawal eligibility, compliance, risk, and provider controls.

### Currency invariants

1. FanCoin is never directly withdrawable.
2. GTEX Coin is withdrawable.
3. GTEX Coin cannot be gifted.
4. Gift input currency is always FanCoin.
5. A successful gift converts the recipient leg to GTEX Coin, regardless of whether the gift occurs in a GTEX-hosted competition, user-hosted competition, match, club, or other approved context.
6. Competition context must never determine whether the recipient receives FanCoin or GTEX Coin.

## 2. Gifting

The canonical gift flow is:

```text
Sender FanCoin debit
        +
GTEX platform rake/fee
        ↓
Recipient GTEX Coin credit
```

Every gift must retain provenance identifying:

- sender
- recipient
- gift item
- FanCoin gross amount
- platform rake
- GTEX Coin recipient net amount
- source context
- match/competition ID where applicable
- fee/revenue rule version
- ledger transaction ID

No API may accept GTEX Coin as a gift funding currency.

## 3. Competition funding modes

### Mode A: FanCoin participant pool

Participants may contribute FanCoin to a user-hosted competition purse.

Rules:

- entry contribution is FanCoin
- FanCoin enters competition escrow
- platform fee applies
- winner receives FanCoin
- FanCoin winnings remain non-withdrawable

This mode is intended for social/friendly/community rivalry play.

### Mode B: Host-funded GTEX Coin prize

A host may create a competition with a withdrawable GTEX Coin prize.

Rules:

- the prize is funded by the host
- the host's GTEX Coin is escrowed before the competition opens
- participants do not contribute GTEX Coin to the prize purse
- platform fee applies according to the active competition fee policy
- winner receives GTEX Coin
- winner's GTEX Coin is withdrawable

Participant-funded pools of withdrawable GTEX Coin are not permitted under this model.

## 4. Competition booking

The competition creator/host pays the competition booking/creation charge from one source.

Participants do not split the booking fee.

The host must be a participant in competitions where the competition type requires host participation.

The host may win their own competition if they satisfy the same competition rules as every other participant.

Competition rules become immutable once the first participant has committed, including:

- funding mode
- currency
- prize amount
- fee policy snapshot
- eligibility rules
- GSI bounds
- format
- start time
- payout rules

## 5. Platform fees

GTEX must never hide fees. Fees are a first-class product concept and must be visible to the affected user before commitment.

The platform fee is configurable by Admin through a central economic policy. It must not be hardcoded in individual services.

The current intended competition platform cut is **30%**, but the implementation must read the active Admin policy rather than hard-code 30%.

The same central policy architecture must support separate configurable rates for:

- FanCoin purchase
- GTEX Coin purchase
- gifts
- Fast Match
- user-hosted competition booking
- user-hosted competition purse
- GTEX-hosted competition settlement
- player rental
- player transfer/market fees
- club share purchase
- club share settlement
- club sale
- Coin Trader operations
- normal-user withdrawal
- Coin Trader withdrawal
- external payment processing

Platform fees and payment-processor costs are separate accounting concepts.

Every settled transaction must retain the fee rule ID/version and the exact rate/basis used.

## 6. Club Season Shares

Club investment is a **seasonal economic participation contract**, not automatic permanent operational ownership.

A club owner may offer a configurable percentage of eligible seasonal economic performance, including up to 50% where product policy permits.

The owner sets:

- season
- investment window
- offered economic percentage
- share price
- eligible revenue types
- settlement rules

Once the first investment is accepted, those commercial terms are locked for the season.

Economic participation and operational control are distinct. A shareholder's economic percentage does not automatically grant operational control of the club.

Purchase proceeds paid to the club owner are GTEX Coin and are withdrawable subject to ordinary withdrawal controls, after the applicable purchase/platform fee.

At season closure:

```text
Gross eligible club revenue
        ↓
GTEX platform fee
        ↓
Net eligible revenue
        ↓
Shareholder economic percentage
        ↓
Individual shareholder settlements
        ↓
Owner retained amount
```

Season Share contracts expire after their defined season closes and settles.

Valid existing Season Share obligations survive a club sale unless the contract explicitly provides otherwise.

## 7. Coin Traders

Coin Trader is an exclusive account mode.

A Coin Trader account is a Coin Trader account and cannot simultaneously operate as an ordinary GTEX club/competition/creator account.

Coin Traders may:

- quote buy/sell rates
- provide Coin liquidity
- trade GTEX Coin with platform users
- use GTEX escrow/settlement
- withdraw through GTEX under the Coin Trader fee policy

Coin Traders may not:

- own/manage a club
- participate in GTEX competitions
- buy Club Season Shares
- enter national-team qualification pools
- operate as an ordinary competitive manager

Trader order matching must only expose traders able to cover the requested full order amount using authoritative effective liquidity.

Effective trader liquidity must be based on authoritative Coin balance minus reserved/escrowed amounts, not merely a manually editable snapshot.

## 8. Withdrawal

All GTEX Coin is eligible for withdrawal, subject to ordinary account, compliance, risk, settlement, and provider controls.

Withdrawal fees must be explicit before confirmation and must distinguish:

- GTEX platform withdrawal fee
- payment-provider/processing fee

Normal-user and Coin Trader withdrawal fees may differ and must be separately Admin-configurable.

FanCoin is never a withdrawal asset.

## 9. Ledger authority

The canonical ledger is the only monetary authority.

Wallet balances, Agent Wallet state, marketplace balances, trader liquidity snapshots, and other cached/projection objects must never become independent sources of monetary truth.

All economic mutations must be:

- ledger-backed
- balanced
- idempotent where retry is possible
- auditable
- attributable to a source domain object

## 10. Required acceptance invariants

The implementation is not considered Phase A complete until these invariants pass automated tests:

1. FanCoin purchase creates non-withdrawable FanCoin.
2. Unused purchased GTEX Coin can be withdrawn.
3. GTEX Coin cannot be gifted.
4. FanCoin can be gifted.
5. A gift during a user-hosted competition debits FanCoin and credits GTEX Coin to the recipient.
6. A gift during a GTEX-hosted competition debits FanCoin and credits GTEX Coin to the recipient.
7. Gift recipient Coin is withdrawable.
8. FanCoin competition entry never creates withdrawable Coin.
9. FanCoin competition payout remains FanCoin.
10. Host-funded GTEX Coin competition prize is escrowed before opening.
11. Participant-funded GTEX Coin purse is rejected.
12. Competition platform fee is read from Admin policy, not hardcoded.
13. Historical transactions preserve the fee policy/rate that was applied.
14. Club Season Share purchase proceeds are GTEX Coin and withdrawable subject to normal controls.
15. Club Season Share settlement applies platform fee before shareholder distribution.
16. Coin Trader liquidity cannot be oversold under concurrency.
17. Coin Trader cannot call ordinary club/competition/share capabilities.
