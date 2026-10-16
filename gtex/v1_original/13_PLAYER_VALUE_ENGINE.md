# Player Value Engine

## Three price layers
### RMV
Reference Market Value — official app market value

### BVF
Base Value Floor — minimum trade value

Recommended floor:
- superstar = 75% of RMV
- elite = 70%
- prospect = 60%

### PSP
Platform Sell Price — platform sells above RMV while supply remains

Recommended default:
- PSP = RMV × 1.15

## Rules
- users cannot list below BVF
- platform buyback pays BVF
- user-to-user trades can go above RMV
- emotional overpay does not change RMV

## Inputs
- match rating
- goals
- assists
- minutes
- league strength
- competition strength
- giant-killing bonus
- contract years
- injury status
- transfer events
- market demand premium

## Initial scaling
Use:
- €100m real-world value -> 1000 coins
- €75m -> 750
- €20m -> 200

Use that only as the initial baseline.
After launch, the app economy and football data drive values.

## Free transfer auction
- one hidden bid per user
- users only see bid count and assets available
- top N win
- all winners pay lowest winning bid
- reduce supply by 60% on free transfer
