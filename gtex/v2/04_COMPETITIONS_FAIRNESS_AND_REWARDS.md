# Competitions, Fairness, and Rewards

## Admin-editable controls
Admin can edit:
- entry fee in coins
- win payouts
- bonus payouts
- competition availability
- leaderboard categories

## Default entry fee suggestions
### League ladder
- Tier D: 0.5 coins
- Tier C: 1 coin
- Tier B: 2 coins
- Tier A: 4 coins
- Tier S: 6 coins

### Major club / international events
- African Club Championship: 2 coins
- South American Club Championship: 2 coins
- Asian Club Championship: 2 coins
- UEFA Club Championship: 4 coins
- Club World Cup: 5 coins
- U17 World Cup: 1 coin
- U20 World Cup: 1 coin
- AFCON: 1.5 coins
- Copa América: 1.5 to 2 coins
- Euros: 2 coins
- World Cup: 3 coins

These are defaults only. Admin must be able to change them.

## Competition leaderboard categories
Each competition should display:
- highest scoring squad
- highest assists squad
- highest rated squad
- best goalkeeper squad

## Squad metric definitions
- **Goals tally** = sum of goals across the entered squad
- **Assists tally** = sum of assists across the entered squad
- **Ratings tally** = combined overall ratings logic across the entered squad
- **Goalkeeper score** = saves, clean sheets, and goalkeeper contribution formula

## Fairness normalization
Problem: 18-player squads should not be unfairly beaten by 25-30 player squads when the difference is tiny.

### Recommended fairness formula
For a scoring category:
1. Compute raw total
2. Divide by players entered for efficiency score
3. Multiply by squad-size fairness factor relative to the competition max

Example:
- raw_goals = 45
- players_entered = 18
- max_players = 30
- efficiency = 45 / 18 = 2.5
- fairness_factor = 30 / 18 = 1.6667
- adjusted_score = efficiency × fairness_factor

This strongly rewards efficient squads.

### Practical safeguard
To avoid overcorrection, cap the fairness factor.
Recommended cap: **1.35**

### Final scoring pattern
For each leaderboard category, use:
`final_score = (raw_total / players_entered) × min(max_players / players_entered, 1.35)`

This means a smaller squad with only a very small deficit can beat a bloated squad.

## Bonuses
Admin should be able to assign bonus coins or rewards for:
- highest goals
- highest assists
- highest ratings
- best goalkeeper
- overall winner
