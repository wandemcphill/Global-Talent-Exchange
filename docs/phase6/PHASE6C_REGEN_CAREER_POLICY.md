# Phase 6C: Regen Career Clock and Retirement Policy

Phase 6C replaces the fixed wall-clock retirement concept with a GTEX-season-native career policy.

## What changes

The career engine now distinguishes:

- GTEX season chronology from wall-clock time.
- virtual age from real calendar age.
- career stage from retirement pressure.
- retirement watch from an actual retirement decision.
- position longevity from a fixed retirement age.

The engine consumes an explicit GTEX season timeline. Each `RegenSeason` may publish a `virtual_age_month_index` in `metadata_json`. The engine refuses to guess a season-to-age conversion when the mapping is incomplete.

This intentionally leaves the final global age-conversion schedule as a product decision. The platform can later define how quickly a regen moves from, for example, game age 15 to 22 without rewriting the career policy itself.

## Retirement pressure

Pressure combines, where data exists:

- virtual age;
- position longevity profile;
- injury burden;
- playing time;
- performance trajectory;
- contract security;
- market demand;
- salary burden;
- willingness to continue;
- ambition, resilience and loyalty;
- achievements;
- club opportunity.

Goalkeepers and defenders receive a longevity advantage in the pressure calculation, but no position is assigned a deterministic retirement date.

Nationality is not used as a crude deterministic retirement rule. Future football-background effects must enter as evidence-based career-profile inputs rather than stereotypes.

## Safety boundary

This PR introduces the policy engine and tests without changing the existing lifecycle service's production retirement behavior. The next integration PR will wire the policy into the existing lifecycle/regen state machine, season progression, retirement event, and legacy transition.

That sequencing protects the already-merged platform while giving the new retirement rules a standalone, testable contract first.
