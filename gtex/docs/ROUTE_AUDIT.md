# GTEX Route Audit

Date: 2026-05-06

## Executive Summary

GTEX currently has two parallel routing systems in the Flutter frontend:

1. `frontend/lib/navigation/app_router.dart`
   - A `go_router` tree with `StatefulShellRoute`, top-level URLs like `/market`, `/world`, `/clips`, `/competitions`, `/profile/admin`.
   - This is the only real `go_router` source in the repo.
   - It is not the primary runtime entry for the live web/mobile shell.

2. `frontend/lib/app/gte_frontend_app.dart` plus the premium route stack:
   - `MaterialApp`
   - `home: GteExchangeShellScreen.fromPath(...)`
   - `onGenerateRoute`
   - `frontend/lib/features/app_routes/gte_app_route_registry.dart`
   - `frontend/lib/features/app_routes/gte_route_data.dart`
   - `frontend/lib/features/navigation/presentation/gte_navigation_shell_screen.dart`
   - This is the live GTEX shell path that production is actually using.

That means GTEX does not currently have a single source of truth for routing. It has:

- one legacy `go_router` tree
- one active custom route registry + shell system
- a large amount of direct `Navigator.push(...)` usage inside screens/features

## Active Runtime Spine

### Primary app entry

- `frontend/lib/main.dart`
- `frontend/lib/app/gte_frontend_app.dart`

The current runtime is built around `MaterialApp`, not `MaterialApp.router`.

### Active route sources

- `frontend/lib/features/navigation/routing/gte_navigation_route.dart`
  - Shell lane routing such as:
    - `/app/home`
    - `/app/market`
    - `/app/play/...`
    - `/app/club`
    - `/app/hub`
    - `/app/wallet`
- `frontend/lib/features/app_routes/gte_route_data.dart`
  - Canonical deep-feature route catalog and parser
- `frontend/lib/features/app_routes/gte_app_route_registry.dart`
  - Builds route widgets and feature shells
- `frontend/lib/features/navigation_guards/gte_navigation_guards.dart`
  - Guard resolution and feature gating

### Deep-link behavior

The active shell now maps several legacy URLs back into the premium GTEX shell:

- `/market`
- `/player-cards`
- `/football/transfer-center`
- `/competitions`
- `/competitions/hosted`
- `/competitions/gtex`
- `/world/regens`
- `/news`
- `/clips`

This mapping is now partly centralized in:

- `frontend/lib/app/gte_frontend_app.dart`
- `frontend/lib/features/app_routes/gte_route_data.dart`

## Legacy / Parallel Router

### File

- `frontend/lib/navigation/app_router.dart`

### Findings

- Defines a full `GoRouter`.
- Declares many public-facing paths that overlap in intent with the active shell.
- Uses route builders that mount older screens like:
  - `TransferMarketScreen`
  - `LiveCompetitionsHubScreen`
  - `WorldScreen`
  - `ViralFeedScreen`
  - `ProfileScreen`
- This router is not the primary live runtime spine.

### Conflict

This means the same product concept often has two route systems:

| Product concept | Legacy `go_router` route | Active premium route/shell |
| --- | --- | --- |
| Market | `/market` | `/app/market`, premium shell market desk |
| Competitions | `/competitions`, `/competitions/:family/:id` | `/app/play/...` and premium hub routes |
| Regens | `/regens` | `/world/regens` and shell/hub world lanes |
| News / clips | `/clips` | `/news`, `/clips`, studio/hub lane |
| Profile/admin | `/profile`, `/profile/admin` | shell actions and admin command center |

## Route Inventory Sources

### Shell routes

File:
- `frontend/lib/features/navigation/routing/gte_navigation_route.dart`

Observed shell destinations:
- `home`
- `market`
- `competitions`
- `club`
- `hub`
- `wallet`

### Canonical deep-feature routes

File:
- `frontend/lib/features/app_routes/gte_route_data.dart`

Observed route families include:
- competitions
- streamer tournaments
- fan predictions
- player cards
- creator share market
- club sale market
- world
- regen universe
- news desk
- national team
- football transfer center
- broadcast
- jackpot
- club AI assistant
- creator stadium
- creator league admin
- gift stabilizer
- club identity

### Legacy go_router route families

File:
- `frontend/lib/navigation/app_router.dart`

Observed route families include:
- home
- matches
- market
- competitions
- profile
- world
- transfer center
- regens
- federations
- national teams
- tasks
- clips
- login/signup/admin
- competitions create/detail/family
- match viewer/broadcast/3d/spectate/simulate

## Navigation API Audit

### Current problem

The app still contains a large amount of direct imperative navigation.

Repository scan results:

- `Navigator.push` / `Navigator.of(context).push...` is still widely used across:
  - home dashboard
  - shell
  - competitions
  - wallets
  - club identity
  - support
  - admin
  - profile
  - tournaments
  - notifications

### Examples

- `frontend/lib/app/gte_frontend_app.dart`
- `frontend/lib/features/navigation/presentation/gte_navigation_shell_screen.dart`
- `frontend/lib/features/home_dashboard/home_dashboard_screen.dart`
- `frontend/lib/screens/wallet/...`
- `frontend/lib/screens/competitions/...`
- `frontend/lib/features/club_identity/...`

### Consequence

The current app does not satisfy:

- single router spine
- named-route-only navigation
- deterministic URL behavior across all surfaces

## Guard Audit

### Current guard sources

- `frontend/lib/features/navigation_guards/gte_navigation_guards.dart`
- per-screen auth checks
- per-widget fallback logic
- older `go_router` tree in `frontend/lib/navigation/app_router.dart` does not own all guards

### Current state

Guards are partially centralized for premium deep-feature routes via:

- `GteNavigationGuardResolver`
- `GteGuardResolution`

But auth/admin gating is still also implemented in screen-level logic and action handlers.

### Consequence

Guard behavior is not yet single-source or fully deterministic from one router redirect function.

## Test Audit

### Current test posture

Repository-wide frontend test scan counts:

- text-based widget assertions: `758`
- `find.byType(...)` / `find.byKey(...)` assertions: `209`

### Meaning

The test suite is still heavily dependent on UI copy and therefore fragile under product wording changes.

### Improved slices already in progress

The route-specific test work has started moving toward structural assertions in:

- `frontend/test/gte_frontend_app_test.dart`
- `frontend/test/gte_feature_routing_test.dart`
- `frontend/test/gte_controlled_merge_contract_test.dart`

But the suite overall is not yet converted.

## Issues

### P0

1. Two routing systems exist in parallel.
2. Live app runtime does not use `MaterialApp.router`.
3. Legacy `go_router` tree and active premium registry can disagree on the same product destination.

### P1

1. Deep links can land on older feature implementations instead of premium shell lanes.
2. Many screens still use `Navigator.push(...)`.
3. Guards are split across router helpers, guard resolvers, and widget code.

### P2

1. Route tests still overuse UI text.
2. Some route-like flows are actually action buttons opening raw `MaterialPageRoute`s, which are hard to reason about globally.

## Immediate Recommendations

1. Choose one router spine.
   - Recommended winner: the active premium GTEX shell and feature registry, migrated into a real `MaterialApp.router` / `GoRouter` setup.

2. Deprecate `frontend/lib/navigation/app_router.dart`.
   - Do not keep two top-level routing systems alive.

3. Create one centralized router module.
   - Proposed path:
     - `frontend/lib/router/app_router.dart`

4. Migrate shell destinations first.
   - home
   - market
   - matchday
   - club
   - studio
   - wallet

5. Migrate premium deep-feature routes second.
   - player cards
   - competitions
   - regen universe
   - news desk
   - club sale market
   - national team

6. Convert `Navigator.push(...)` feature flows incrementally behind named route helpers.

7. Replace text-based route assertions with:
   - `find.byType(...)`
   - `find.byKey(...)`

## Current Safe Conclusion

GTEX routing is now better aligned than before, but it is not yet a full router purge.

The repository currently contains:

- one active premium shell router model
- one older `go_router` tree
- many imperative route pushes

So the codebase has improved route unification, but it has not yet reached the end-state of:

- one router file
- no legacy navigation APIs
- all guards owned by one redirect function
- all tests asserting mounted widgets instead of text
