# Player Value Engine V2

## Do not replace the original engine
V2 updates the valuation engine. It does not replace the original logic.

## Baseline rule
`100M real-life player value = 1000 credits`

## Core drivers
Player value should react to:
- real-life match performances and stats
- real-life transfers
- user demand in the app
- league strength
- major competition importance
- awards and nominations
- iconic moments in major finals

## Major competition impact
Major competitions should carry impact equal to or greater than League A when appropriate.

Recommended importance ladder:
- World Cup: very high
- UEFA Club Championship: very high
- AFCON: high
- Copa América: high
- Euros: high
- League A: high
- League B: medium
- League C: lower

## Example competition multipliers
These are guidance values and should remain configurable:
- World Cup: 1.35
- UEFA Club Championship: 1.30
- AFCON: 1.25
- Copa América: 1.25
- Euros: 1.25
- League A: 1.20
- League B: 1.10
- League C: 1.05

## Big-moment rules
Huge moments should move value before transfer confirmation.
Examples:
- scoring in a World Cup final
- scoring in a major continental final
- dominant tournament breakout
- final-winning goal

## Awards impact layer
Awards should have major influence.
Suggested scale:
- Ballon d'Or winner: very large impact
- Ballon d'Or top 3: large impact
- Ballon d'Or top 10: strong impact
- Ballon d'Or top 20 nomination: noticeable impact
- player of the season: strong impact
- young player of the season: strong impact
- world tournament Golden Ball / Golden Shoe: strong impact
- U20/U17 Golden, Silver, Bronze awards: meaningful prospect boosts
- man of the match: small but stackable impact

## Demand impact
Demand should remain part of the value system.
Weight hierarchy:
- completed purchases and sales: strongest
- shortlist adds: medium
- watchlist adds: light
- follows: weakest

## Smoothing and anti-manipulation
- max daily movement caps
- trade cooldowns
- whale ownership limits
- suspicious behavior excluded from demand scoring
