# Competitive Module Audit

Scope: A7-002 in `AUDIT_REMEDIATION_TRACKER.md`

Decision rule:
- `SHIP` means the module is reflected in a routed, discoverable product surface or clearly shipped product lane.
- `HIDE` means the backend capability may remain in use, but it is not truthful to present the module itself as a standalone live surface.
- `DEPRECATE` means the module is isolated enough that it should be removed from active product claims and treated as retirement-or-rescope work unless a concrete owner revives it.

## Decisions

| Module | Backend reality | Frontend reality | Owner | Status | Plan |
| --- | --- | --- | --- | --- | --- |
| `manager_duels` | Real API and persisted model; duel records are consumed by live-match, viral, commentary, and football-universe services. | No routed or discoverable duel-specific frontend surface. | Product + match/meta systems | `HIDE` | Keep it as supporting match metadata. Do not claim a live manager-duels module until a real duel surface exists. |
| `simulation_matchmaking` | Real API for simulation profiles, quick games, quick tournaments, and hosted-competition previews. No downstream backend consumers outside module registration. | No routed live frontend uses the backend module. Existing simulation UI is fixture-gated and explicitly blocked in the live shell. | Product + gameplay systems | `DEPRECATE` | Remove `simulation_matchmaking` from active product claims. If product wants live matchmaking later, rebuild from an explicit routed owner surface instead of implying this dormant API is shipped. |
| `ultimate_league` | Real API for tiers, competitors, standings, matchmaking batches, tournaments, and tactical presets. No downstream backend consumers outside module registration. | No routed or discoverable frontend surface for ultimate-league management or play. | Product + gameplay systems | `DEPRECATE` | Remove `ultimate_league` from active product claims and treat it as retirement-or-rescope work until a concrete ladder or league UX is actually routed. |
| `infinite_league` | Real runtime and API; actively powers generated live-match streams, match-viewer hydration, pundits, viral feeds, and broadcast bootstrap. | No discoverable standalone `infinite_league` route or named module UI. Users see its output through other shipped surfaces, not through a dedicated league screen. | Product + live-match systems | `HIDE` | Keep it as shipped infrastructure behind generated match and media surfaces, but do not market `infinite_league` itself as a standalone live module. |
| `fast_cups` | Real backend module and API for upcoming cups, join, bracket, countdown, and result summaries. | Discoverable competitions-hub lane exists as `GTEX Fast Cup`, with explicit routing and curation for fast-cup entries. | Product + competitions | `SHIP` | Keep fast-cup claims scoped to the competitions-hub product lane. A standalone `/fast-cups` surface is not required for truthful shipped status. |

## Evidence Summary

- `manager_duels` surface and integrations:
  - `backend/app/manager_duels/router.py`
  - `backend/app/live_matches/router.py`
  - `backend/app/viral/service.py`
  - `backend/app/services/commentary_service.py`
  - `backend/app/football_universe/service.py`
- `simulation_matchmaking` isolated API:
  - `backend/app/simulation_matchmaking/router.py`
  - `backend/app/modules.py`
- `ultimate_league` isolated API:
  - `backend/app/ultimate_league/router.py`
  - `backend/app/modules.py`
- `infinite_league` live runtime integrations:
  - `backend/app/infinite_league/router.py`
  - `backend/app/live_matches/router.py`
  - `backend/app/routes/match_viewer.py`
  - `backend/app/viral/router.py`
  - `backend/app/pundits/router.py`
  - `backend/app/broadcast_network/service.py`
- Fast-cup product discovery:
  - `frontend/lib/features/competitions_hub/routing/competition_hub_destination.dart`
  - `frontend/lib/features/competitions_hub/data/competition_hub_curator.dart`
  - `backend/app/fast_cups/api/router.py`
- Simulation route truthfulness:
  - `frontend/test/navigation_surface_truth_test.dart`
  - `frontend/test/match_simulate_route_screen_test.dart`
  - `frontend/test/active_shell_live_migration_smoke_test.dart`

## Product-Truth Outcome

- Active product claims can treat `fast_cups` as shipped.
- Active product claims should treat `infinite_league` and `manager_duels` as supporting engines, not standalone live modules.
- Active product claims should stop implying `simulation_matchmaking` and `ultimate_league` are shipped until they either gain real routed owners or are formally retired.
