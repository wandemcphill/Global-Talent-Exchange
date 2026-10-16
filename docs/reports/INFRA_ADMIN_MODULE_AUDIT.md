# Infrastructure And Admin-Sensitive Module Audit

Scope: A7-004 in `AUDIT_REMEDIATION_TRACKER.md`

Decision rule:
- `SHIP` means the module is deliberately exposed through a routed, scoped product or admin surface.
- `HIDE` means the capability may remain active, but it is not truthful or safe to present the module itself as a standalone shipped surface.
- `DEPRECATE` means the module should be removed from active product claims and treated as retirement-or-compliance-review work unless a concrete owner revives it.

## Decisions

| Module | Backend reality | Frontend reality | Owner | Status | Plan |
| --- | --- | --- | --- | --- | --- |
| `club_infra_engine` | Real user/admin API for club infrastructure dashboards, stadium upgrades, facility upgrades, club support, and seeding. It is also used during creator provisioning and contributes to downstream valuation signals. | No routed frontend consumer was found for the `club-infra` or `admin/club-infra` routes. Current club and creator surfaces only reflect derived infrastructure values, not this module’s contract. | Product + club platform | `HIDE` | Keep it as backend provisioning and economics infrastructure. Do not claim a live club-infra module until a scoped owner UI is wired to these endpoints. |
| `regen_ecosystem` | Real API for academy generation, scouts, regen feed, awards, lineage, and jobs. Its models and service still feed regen-universe, fan-experience, and ops flows. | The shipped regen experience is routed through `regen-universe` and national-team/world surfaces, not the `regen_ecosystem` router contract directly. | Product + world/regen systems | `HIDE` | Keep it as backend regen-generation infrastructure behind the shipped regen-universe surfaces. Do not market `regen_ecosystem` itself as a standalone module. |
| `surveillance` | Real admin-gated API for suspicious players, clusters, thin markets, holder concentration, and circular trade alerts. It is also used by the integrity scan worker. | No routed admin or frontend surface was found for the surveillance routes. The product only leaks passive thin-market wording, not a deliberate surveillance desk. | Product + platform + compliance | `HIDE` | Keep it hidden and admin-scoped until there is an explicit compliance/admin workflow owner. Do not surface it casually in navigation or product claims. |
| `betting` | Real wallet-user API for preferences, odds, bet placement, and history, with ledger funding and betting pool support. Calendar payloads can still emit a `betting_route`. | No routed frontend betting surface was found. Visible product copy explicitly says competitions are funded by promo pools and are not betting-driven. | Product + compliance + economy | `DEPRECATE` | Remove betting from active product claims and treat it as compliance-sensitive retirement-or-review work. Any future revival would require an explicit compliance program, scoped geography rules, and a deliberate routed product surface. |

## Evidence Summary

- `club_infra_engine` backend surface and integration:
  - `backend/app/club_infra_engine/router.py`
  - `backend/app/services/creator_provisioning_service.py`
  - `frontend/lib/features/creator_share_market/presentation/creator_share_market_screen.dart`
- `regen_ecosystem` backend surface and shipped adjacent seam:
  - `backend/app/regen_ecosystem/router.py`
  - `backend/app/services/regen_ecosystem_service.py`
  - `backend/app/regen_universe/service.py`
  - `frontend/lib/features/world/live_world_provider.dart`
  - `frontend/lib/features/football_world_simulation/presentation/football_world_simulation_screen.dart`
  - `frontend/lib/features/national_teams/live_national_teams_provider.dart`
- `surveillance` backend-only scope:
  - `backend/app/surveillance/router.py`
  - `backend/app/workers/integrity_scan_worker.py`
- `betting` backend surface, implied route leak, and contradictory product copy:
  - `backend/app/betting/router.py`
  - `backend/app/calendar_engine/service.py`
  - `backend/app/wallets/service.py`
  - `frontend/lib/screens/competitions/competition_detail_screen.dart`
  - `frontend/lib/screens/competitions/competition_join_screen.dart`
  - `frontend/lib/data/competition_api.dart`

## Product-Truth Outcome

- `club_infra_engine`, `regen_ecosystem`, and `surveillance` should remain hidden backend or admin-scoped systems until they gain explicit routed owners.
- `regen_ecosystem` does support shipped regen experiences, but those experiences are truthfully claimed through `regen-universe`, world, and national-team routes instead of the module name itself.
- `betting` should not appear in active GTEX product claims while the visible app copy simultaneously asserts that competitions are not betting products.
