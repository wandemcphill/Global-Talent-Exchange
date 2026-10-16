# Payments and Coin Model

## Coin rules
- 1 coin = 1 euro
- user may display value in local currency
- display currency can only be changed once per year

## Wallets
- one real wallet
- one demo wallet
- demo wallet starts with 5000 demo coins

## Payment providers
Use:
- Paystack
- Moniepoint
- Stripe

Wrap them behind one internal payment provider interface.

## Deposit flow
local currency
-> payment provider
-> coins credited

## Withdrawal flow
coins debited
-> payout provider called
-> local payout sent

## App rule
Users cannot send raw money directly to each other.
Money only moves between users through player trades.

## User-to-user trade
- buyer pays from wallet
- seller receives coins instantly
- seller pays 5% fee instantly

## Platform revenue
- trade fee
- withdrawal fee
- FX spread
