# Economy, Payments, and Ledger

## Core economy split
### Coins
Coins are used for:
- competition entry
- card packs
- shortlist boosts
- transfer room premium placement
- listing fees
- scouting submissions or special actions if enabled

### Credits
Credits express player card value in the market.

## Kept rule
`100M real-life value = 1000 credits`

Examples:
- 100M = 1000 credits
- 50M = 500 credits
- 10M = 100 credits
- 1M = 10 credits
- 500K = 5 credits

## Payment rails
### Primary: Monnify
Use for:
- Nigerian cards
- local bank transfers
- virtual account collections where approved and appropriate
- webhook payment confirmation

### Backup rails
- Flutterwave
- Paystack

## Suggested starter coin packs
- 50 coins
- 120 coins
- 300 coins
- 800 coins

Exact consumer pricing can be adjusted by admin and market tests.

## Ledger rules
Never use wallet-style mutable balances without entries.

Use:
- ledger_accounts
- ledger_entries
- payment_events
- payout_requests
- marketplace_settlements

## Deposit flow
1. User chooses coin pack
2. Payment intent created
3. Monnify checkout or transfer instruction shown
4. Verified webhook arrives
5. Ledger entry written
6. Coins credited

## Payout flow
1. User requests withdrawal where supported by policy
2. Fraud and KYC checks run
3. Hold is placed
4. Payout attempt made via supported rail or approved admin flow
5. Ledger finalized
