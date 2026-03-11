# Codex Master Prompt V2

You are the lead engineering system for **Global Talent Exchange**.

Build a production-ready platform that preserves the original product mechanics from V1 while applying the V2 upgrades described in this package.

## Product summary
Global Talent Exchange is a football talent discovery and collectible player card platform with:
- player value movement tied to real-life football and in-app demand
- fantasy and scouting competitions
- Global Scouting Index
- follow, watchlist, shortlist, and transfer room systems
- premium 22nd-century UI/UX
- Nigerian-first payments via Monnify with backups

## Hard constraints
- keep the `100M real-life value = 1000 credits` rule
- do not reintroduce `1 coin = 1 euro`
- coins are activity units, credits are player valuation units
- preserve the existing player pool size and competition arrangement from V1 unless explicitly changed later
- keep major competitions and awards heavily influential in value movement
- implement admin-editable competition fees and bonuses
- implement fairness normalization for small squads versus large squads

## Frontend requirements
- Flutter app
- dark luxury futuristic design
- strong onboarding and beautiful landing page
- clear back navigation everywhere
- player profile as premium intelligence screen
- transfer room as live market theater

## Backend requirements
- FastAPI
- PostgreSQL
- Redis
- background jobs
- immutable ledger
- webhook-driven payment confirmation

## Payment requirements
- integrate Monnify as primary rail
- integrate Flutterwave and Paystack as optional backups
- coin pack purchase flow
- webhook verification
- ledger posting on successful payment only

## Value engine requirements
Update, do not replace, the original value engine.
It must consider:
- real-life performances
- league strength
- World Cup, AFCON, Copa América, UEFA Club Championship, and other major competitions
- awards including Ballon d'Or outcomes and nominations
- big moments in finals
- transfer momentum
- in-app demand
- anti-manipulation caps and smoothing

## Competition requirements
- admin-editable fees and rewards
- leaderboards for highest goals, assists, ratings, and best goalkeeper
- fairness normalization for smaller squads
- category-specific results and bonuses

## Discovery requirements
- Global Scouting Index
- follow
- watchlist
- shortlist
- transfer room
- notifications for player development

## Delivery requirements
Output:
1. final project tree
2. all created files
3. setup instructions
4. migrations
5. run commands
6. test commands
7. any assumptions made
