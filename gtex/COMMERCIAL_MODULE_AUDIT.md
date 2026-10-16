# Commercial Module Audit

Scope: A7-001 in `AUDIT_REMEDIATION_TRACKER.md`

Decision rule:
- `SHIP` means the module is reachable through a routed, discoverable frontend surface with a matching live backend path.
- `HIDE` means the backend capability can remain, but it is not truthful to present it as a shipped standalone product surface.
- `DEPRECATE` would mean removing the module from active product claims and retirement planning; no module in this slice met that bar.

## Decisions

| Module | Backend reality | Frontend reality | Owner | Status | Plan |
| --- | --- | --- | --- | --- | --- |
| `reward_engine` | Real public/admin API under `/reward-engine` and `/admin/reward-engine`; actively used by challenge, prediction, and tournament services. | No routed or discoverable standalone frontend surface. Reward UX appears only inside the owning products that settle rewards. | Product + economy backend | `HIDE` | Keep as backend infrastructure. Do not advertise `reward_engine` as its own product lane. Any future standalone reward dashboard needs an explicit routed owner surface first. |
| `broadcast_rights` | Real public/admin API under `/broadcast-rights` and `/admin/broadcast-rights`; used by live matches, media, football universe, and federations logic. | No routed frontend screen. Current frontend evidence is limited to a parsed `broadcast_rights_coin` field in creator-share-market models. | Product + media backend | `HIDE` | Remove it from active product claims until a concrete rights marketplace or access-management UI is routed. Keep the backend capability for internal media and finance flows. |
| `creator_campaign_engine` | Real public/admin API under `/creator-campaigns` and `/admin/creator-campaigns`; supports create, update, metrics, and snapshots. | No routed or discoverable frontend composer, metrics view, or management screen. | Product + creator systems | `HIDE` | Treat it as dormant backend capability. Do not claim creator campaigns as shipped until a creator-facing workflow is routed and verified. |
| `ticketing` | Real `ticketing` module plus creator-league ticket purchase and stadium endpoints under `media_engine`. | Routed and discoverable through creator-stadium club and match routes, with live repository calls for stadium offers and ticket purchases. | Product + creator media + frontend/backend | `SHIP` | Keep ticketing claims scoped to creator-stadium and creator-league monetization. Do not market `/tickets` as a separate standalone surface; the truthful shipped entrypoint is creator-stadium. |

## Evidence Summary

- `reward_engine` public surface: `backend/app/reward_engine/router.py`
- `broadcast_rights` public surface: `backend/app/broadcast_rights/router.py`
- `creator_campaign_engine` public surface: `backend/app/creator_campaign_engine/router.py`
- `ticketing` standalone module: `backend/app/ticketing/router.py`
- Creator-stadium ticketing entrypoints:
  - `backend/app/media_engine/router.py`
  - `frontend/lib/features/creator_stadium_monetization/data/creator_stadium_monetization_repository.dart`
  - `frontend/lib/features/club_hub/widgets/club_hub_content.dart`
  - `frontend/lib/features/home_dashboard/home_dashboard_screen.dart`
  - `frontend/lib/screens/competitions/gte_live_match_center_screen.dart`

## Product-Truth Outcome

- Active product claims should treat `ticketing` as shipped only inside creator-stadium monetization.
- Active product claims should not describe `reward_engine`, `broadcast_rights`, or `creator_campaign_engine` as standalone live modules until routed UI work exists.
