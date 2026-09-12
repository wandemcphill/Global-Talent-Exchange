# Phase 6D Staff Role Policy

## Purpose

Extend the existing club staff system without creating a second staff architecture.

Canonical records remain `ClubStaffProfile`, `ClubStaffContract`, and `ClubStaffAssignment`.

## Role model

A staff record represents one unique person. Their specialisation describes what they are qualified to do. Their club assignment describes the job they currently hold.

`first_team_manager` is an appointment, not a mandatory separate staff person type. A qualified coach can be appointed manager, and a retired regen can enter the manager pathway.

`head coach` is an alias for the same first-team-manager appointment. GTEX must not create a second economic asset merely because the UI uses the phrase Head Coach.

## Qualification boundaries

Coaching and youth-coaching appointments require coaching capability.

Medical appointments require explicit medical qualification. Retiring from football never grants medical qualification automatically.

Scout, agent, and performance-analysis roles likewise require explicit capability signals.

## Economics

Normal club staff contracts consume their configured salary path and therefore Fan Coin payroll. A personal manager is different: exactly one may exist per GTEX profile, it is permanent and non-transferable, and it does not draw a club salary.

This policy does not set final salary tables, staff transfer prices, or personal-manager creation prices. Those remain separate economic configuration work.

## Safety boundary

This phase adds pure role-policy logic and tests only. It does not change existing staff assignments, wallets, club payroll, player shares, router/navigation, or production database state.
