# V1 to V2 Change Report

This file reports every intentional change from V1 to V2.

## Unchanged from V1
- core football product idea
- player pool size and competition arrangement
- league rating ladder
- base valuation logic concept
- demand-driven market movement
- real-life performances, stats, transfers, and awards affecting player value
- squad size rules and competition entry concept

## Changed in V2

### 1. Product naming
- **Old:** Football Talent Exchange
- **New:** Global Talent Exchange

### 2. Regulation-sensitive terms
- **Removed or de-emphasized:** wallet, token, investment, financial exchange, guaranteed returns
- **Preferred:** balance ledger, platform credits, collectibles, player cards, scouting competitions, talent discovery

### 3. Currency model
- **Removed:** `1 coin = 1 euro`
- **Kept:** `100M real-life player value = 1000 in-app credits`
- **New split:**
  - **Coins** = platform activity units for entries, packs, listings, boosts
  - **Credits** = player card valuation unit shown in the market

### 4. Payment system
- **Primary:** Monnify
- **Backup:** Flutterwave, Paystack

### 5. Admin controls
Admin can edit:
- competition entry fees
- bonuses and win payouts
- category settings per competition
- leaderboard reward rules

### 6. Fairness scoring
Added squad-efficiency normalization so smaller squads are not unfairly punished when close to larger squads.

### 7. Scouting product depth
Added:
- Global Scouting Index
- Follow
- Watchlist
- Shortlist
- Transfer Room

### 8. Value engine updates
Extended the engine to account for:
- major competitions
- finals moments
- man of the match and season awards
- World Cup / AFCON / Copa América / UEFA club competition impacts
- Ballon d'Or and nomination impacts

### 9. UI/UX requirement
V2 explicitly requires a world-class, futuristic, premium interface.
