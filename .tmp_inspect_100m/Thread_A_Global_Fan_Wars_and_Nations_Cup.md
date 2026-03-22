# THREAD A — GLOBAL FAN WARS AND GTEX NATIONS CUP

Build GTEX's large-scale fan and country rivalry systems.

## 1. Global Fan Wars
Implement a system where fans compete as:
- club fanbases
- country fanbases
- creator fanbases

Examples:
- Nigeria fans vs Brazil fans
- Arsenal fans vs Chelsea fans
- Speed United fans vs KSI FC fans

### Fan war point sources
Fans earn points through:
- watching matches
- gifting
- predictions
- tournament participation
- creator support actions
- club support actions

### Rankings
Support:
- Top Global Fanbases
- Top Club Fanbases
- Top Country Fanbases
- Weekly / Monthly / Seasonal rankings

### Presentation
Build:
- fan war dashboards
- rivalry leaderboards
- event banners
- fan war summaries

## 2. GTEX Nations Cup
Creators represent countries in a creator-national competition.

### Format
Default example:
- 32 creators
- group stage
- knockout stage

### Country mapping
Creators should be linked to a represented country or eligible country set under admin rules.

### Fan engagement
Country fans should:
- support their creator
- watch matches
- gift
- contribute to country ranking energy

### Reward surfaces
Support:
- country prestige
- creator prestige
- fanbase prestige
- seasonal/cycle-based records

## 3. Data / Models
Add or extend:
- fan_war_profiles
- fan_war_points
- country_creator_assignments
- nations_cup_entries
- nations_cup_fan_metrics
- fanbase_rankings

## 4. Tests
Write tests for:
- fan war point accumulation
- fanbase rankings
- creator-country assignment
- Nations Cup progression
- fan contribution weighting

## 5. Non-trample rules
- Do not rewrite existing creator league systems unnecessarily
- Keep fan war scoring configurable
- Avoid pay-to-win domination by pure spending only
