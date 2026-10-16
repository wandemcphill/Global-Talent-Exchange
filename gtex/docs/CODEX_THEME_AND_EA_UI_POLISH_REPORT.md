# GTEX Theme And EA UI Polish Report

## Executive summary

GTEX now ships a centralized 5-theme dark-first design system on the active runtime in `frontend/lib/main.dart`, without changing the canonical app entrypoint or route graph. The upgrade replaced the prior ad hoc shell styling with a token-driven theme registry, `ThemeExtension` support, persisted global theme selection, upgraded shell chrome, and premium reusable panel primitives that were then applied to the highest-priority shipped surfaces.

The result is materially closer to the requested product target: stronger command-center hierarchy, more depth, cleaner spacing, sharper CTA separation, more broadcast-grade sports presentation, and a more coherent premium shell across Home, Market, World, Competitions, Matches, Profile, Tasks, live Clips, Federations, National Teams, Transfer Center, and the main admin/profile control surface. Live truth handling was preserved; no fake data or fallback providers were introduced.

## Canonical runtime

- Kept active runtime on `frontend/lib/main.dart`
- Kept active router on `frontend/lib/navigation/app_router.dart`
- Injected the theme controller above `MaterialApp.router`
- Did not replace the active shell or alter the mounted route graph

## Theme system

### Core implementation

- `frontend/lib/theme/gte_theme_registry.dart`
- `frontend/lib/theme/gte_theme_extensions.dart`
- `frontend/lib/theme/gte_theme_controller.dart`
- `frontend/lib/theme/gte_theme_picker_sheet.dart`
- `frontend/lib/widgets/gte_shell_theme.dart`
- `frontend/lib/core/theme/app_theme.dart`
- `frontend/lib/core/theme/app_motion.dart`

### Persistence behavior

- Global theme selection is controlled by `GteThemeController`
- Startup bootstrap happens in `frontend/lib/main.dart`
- Persistence uses `GteSharedPreferencesThemeStore`
- Storage key: `gte_theme_id`
- Default theme: `Founders Black`
- Selected theme survives app restarts and immediately re-applies across the active app

## Five production themes

| Theme | Intent | Best-fit surfaces | Palette direction |
| --- | --- | --- | --- |
| Founders Black | Power-user market terminal | Home, Market, Admin, command surfaces | Deep graphite with electric lime and cyan support |
| Palo Alto Glass | Executive frosted shell | Profile, World, Competitions, premium broadcast wrappers | Dark glass with soft blue/cyan translucency |
| Sand Hill Gold | Luxury ownership finance | Wallet, portfolio, premium competitions, ownership contexts | Matte charcoal with restrained gold |
| Menlo Night Blue | Analytics command center | World, standings, tactical/data-heavy surfaces | Midnight blue with cobalt and icy white |
| AI Arena Crimson | Stadium-night intensity | Matches, clips, event-heavy moments | Black, crimson, and silver |

## Theme palette summary

Each theme defines:

- background, soft background, panel, elevated panel
- stroke, outline, highlight, shadow
- primary, secondary, arena, community, capital, club, and admin accents
- text primary, muted, inverse
- positive, warning, negative states
- typography scale
- button geometry and weight
- motion timing and curves
- shell glow, hero gradient, chart palette, and scorebug compatibility colors

## Component system changes

### Shared shell

- Rebuilt shell styling in `frontend/lib/shared/widgets/app_shell_scaffold.dart`
- Upgraded page framing in `frontend/lib/shared/widgets/app_page_layout.dart`
- Added richer atmospheric theming in `frontend/lib/shared/widgets/app_background.dart`
- Tightened section hierarchy in `frontend/lib/shared/widgets/section_heading.dart`
- Restyled truth badges in `frontend/lib/shared/widgets/data_source_badge.dart`
- Restyled route badges in `frontend/lib/shared/widgets/route_surface_badge.dart`

### Reusable premium primitives

- Added `frontend/lib/shared/widgets/gtex_premium_panels.dart`
- Standardized:
  - hero panels
  - section panels
  - stat tiles
  - pills/chips
  - premium list tiles
- Reused existing `GteSurfacePanel` and `GteStatePanel` with richer token usage

### Motion polish

- Upgraded route transition motion in `frontend/lib/core/theme/app_motion.dart`
- Theme changes propagate through animated rebuilds from the controller
- Premium bottom-sheet theme picker uses the live theme system
- Cards, pills, nav treatments, and panels now use quicker and more intentional visual state transitions

## Route and surface coverage

### Fully polished

- Home
- Market
- World
- Competitions hub
- Matches hub
- Broadcast package route interior
- Profile
- Tasks
- Clips live feed
- Profile admin surface
- Clips blocked surface
- Federations
- National teams
- Transfer Center
- Shared shell/nav/page/header/badge primitives used by those screens

### Partially polished

- Match route wrappers and capability surfaces are polished, but the deep 2D and 3D viewer interiors remain intentionally blocked by route-integrity work already present in the tree
- Admin coverage is strongest on the main profile-admin/control surface; deeper admin paths were not comprehensively reskinned here
- Broadcast-adjacent subwidgets beyond the shipped package lane can still be pushed further once the 2D/3D viewer runtime is reopened for premium styling work

## Changed files

### Theme and shell

- `frontend/lib/main.dart`
- `frontend/lib/core/theme/app_theme.dart`
- `frontend/lib/core/theme/app_motion.dart`
- `frontend/lib/theme/gte_theme_controller.dart`
- `frontend/lib/theme/gte_theme_metadata.dart`
- `frontend/lib/theme/gte_theme_extensions.dart`
- `frontend/lib/theme/gte_theme_registry.dart`
- `frontend/lib/theme/gte_theme_picker_sheet.dart`
- `frontend/lib/theme/app_theme.dart`
- `frontend/lib/theme/theme_extensions.dart`
- `frontend/lib/theme/theme_registry.dart`
- `frontend/lib/theme/theme_switcher.dart`
- `frontend/lib/theme/theme_tokens.dart`
- `frontend/lib/widgets/gte_shell_theme.dart`

### Shared widgets

- `frontend/lib/shared/widgets/app_background.dart`
- `frontend/lib/shared/widgets/app_page_layout.dart`
- `frontend/lib/shared/widgets/app_shell_scaffold.dart`
- `frontend/lib/shared/widgets/data_source_badge.dart`
- `frontend/lib/shared/widgets/route_surface_badge.dart`
- `frontend/lib/shared/widgets/section_heading.dart`
- `frontend/lib/shared/widgets/gtex_premium_panels.dart`

### Polished screens

- `frontend/lib/features/home/home_screen.dart`
- `frontend/lib/features/transfer_market/transfer_market_screen.dart`
- `frontend/lib/features/world/world_screen.dart`
- `frontend/lib/features/competitions/live_competitions_hub_screen.dart`
- `frontend/lib/features/match/match_screen.dart`
- `frontend/lib/features/match/live_match_viewer_route_support.dart`
- `frontend/lib/features/match/match_viewer_capability.dart`
- `frontend/lib/features/match/presentation/broadcast_package_screen.dart`
- `frontend/lib/features/federations/federations_hub_screen.dart`
- `frontend/lib/features/national_teams/national_teams_screen.dart`
- `frontend/lib/features/transfer_center/transfer_center_screen.dart`
- `frontend/lib/features/profile/profile_screen.dart`
- `frontend/lib/features/profile/profile_admin_screen.dart`
- `frontend/lib/features/tasks/tasks_screen.dart`
- `frontend/lib/features/viral_feed/presentation/viral_feed_screen.dart`
- `frontend/lib/features/viral_feed/presentation/clips_blocked_screen.dart`

### Tests

- `frontend/test/theme/gte_theme_controller_test.dart`
- `frontend/test/theme/gte_theme_registry_test.dart`
- `frontend/test/theme/theme_surface_application_test.dart`
- `frontend/test/active_shell_live_migration_smoke_test.dart`
- `frontend/test/surface_runtime_proof_test.dart`
- `frontend/test/transfer_market/transfer_market_screen_test.dart`
- `frontend/test/profile_admin_visibility_test.dart`
- `frontend/test/match/match_screen_broadcast_test.dart`
- `frontend/test/viral_feed/viral_feed_screen_test.dart`
- `frontend/test/match/broadcast_package_screen_golden_test.dart`
- `frontend/test/goldens/viral_feed_premium_surface.png`
- `frontend/test/goldens/broadcast_package_premium_surface.png`

## Before/after UX notes

### Before

- Shell hierarchy was flatter and less differentiated
- Cards often read as generic Flutter panels
- Section spacing and CTA grouping were inconsistent
- Theme support existed in fragments but was not the active system
- Primary surfaces lacked a unified premium sports-product identity

### After

- Hero sections establish clearer page intent and command-center framing
- Premium panel depth, stroke, glow, and radius logic are consistent across core screens
- Typography is more deliberate, tighter, and closer to sports/broadcast product styling
- Bottom nav and shell chrome feel more premium and route-consistent
- Match, market, world, and profile surfaces have stronger vertical rhythm and module separation
- Federations, national teams, and transfer center now read like premium operational modules instead of generic list/card screens
- Live clips now uses the same shell language as the rest of the app, including premium stage framing, action rail styling, and state panels
- The shipped broadcast package lane now matches the premium shell primitives and route-level theme treatment
- Theme selection is now a real product setting instead of a disconnected styling fragment

## Truth and runtime integrity

- No fake data was added
- Live/block/degraded truth handling remains intact
- Existing backend-driven blocked states are still shown honestly
- The currently mounted 2D and 3D viewer routes still disclose their blocked-truth state rather than pretending full live viewer support
- The active runtime entry and active router remain the production source of truth

## Test commands and results

Commands run from `frontend/`:

```bash
flutter test --update-goldens test/viral_feed/viral_feed_screen_test.dart test/match/broadcast_package_screen_golden_test.dart

flutter test test/theme/gte_theme_controller_test.dart test/theme/gte_theme_registry_test.dart test/theme/theme_surface_application_test.dart test/active_shell_live_migration_smoke_test.dart test/navigation_surface_truth_test.dart test/transfer_market/transfer_market_screen_test.dart test/profile_admin_visibility_test.dart test/match/match_screen_broadcast_test.dart test/viral_feed/viral_feed_screen_test.dart test/match/broadcast_package_screen_golden_test.dart test/match_broadcast_route_screen_test.dart test/surface_runtime_proof_test.dart
```

Result:

- 48 test cases passed in the final combined regression command
- Theme controller restore/write behavior passed
- Theme registry coverage and contrast checks passed
- Theme picker/profile application widget tests passed
- Active-shell route smoke tests passed
- Federations, National Teams, Transfer Center, Clips, Broadcast Package, and route-proof interactions passed
- Golden coverage was added and refreshed for the premium live clips feed and the premium broadcast package lane
- Home, Market, World, Competitions, Matches, Profile-related smoke/state tests passed
- No active-shell navigation regressions were found in the exercised routes

## Remaining polish backlog

1. Reopen premium styling for the deep 2D and 3D viewer interiors once the current route-integrity blocking work is ready for those screens to render live content again.
2. Extend the new golden coverage to Home, Market, World, Matches hub, and Profile once those layouts are considered visually frozen.
3. Push the same premium module treatment deeper into secondary admin and federation-adjacent drilldowns.
4. Consider route-aware suggested themes while keeping the current single global persisted theme as the source of truth.
