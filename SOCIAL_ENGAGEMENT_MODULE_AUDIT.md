# Social And Engagement Module Audit

Scope: A7-003 in `AUDIT_REMEDIATION_TRACKER.md`

Decision rule:
- `SHIP` means the module is reflected in a routed, discoverable product surface with matching live behavior.
- `HIDE` means the backend capability remains active or useful, but it is not truthful to present the module itself as a standalone shipped surface.
- `DEPRECATE` means the module is sufficiently orphaned that product claims should stop and retirement-or-rescope work should start.

## Decisions

| Module | Backend reality | Frontend reality | Owner | Status | Plan |
| --- | --- | --- | --- | --- | --- |
| `club_social` | Real API for challenges, follows, match reactions, live reactions, chat, identity metrics, and rivalries. Its models and service are still consumed by competition match, commentary, club sale, creator share, national-team, and creator-fan-engagement systems. | No routed or discoverable frontend surface currently consumes the `club_social` router contract directly. | Product + social systems | `HIDE` | Keep it as supporting club-rivalry and engagement infrastructure. Do not claim a live standalone club-social product until a routed surface is wired to these endpoints. |
| `history_engagement` | Real API plus scheduler/seed path for history, achievements, social feed, community, objectives, and season-pass data. Its models are still used by leaderboard and streamer-tournament systems. | Current shipped community and reputation flows use other frontend/backend seams, not the `history_engagement` router contract. No discoverable standalone history-engagement lane is routed. | Product + social systems | `HIDE` | Keep it as backend social-history substrate. Do not present it as a shipped standalone module until an explicit history/community surface is routed against it. |
| `legend_layer` | Real API for news, rankings, personality, and interviews. A projection worker still invokes `LegendLayerService` on match-completed events. | No routed frontend consumer was found for the legend-layer routes. The currently shipped reputation and world surfaces do not call this module directly. | Product + narrative systems | `HIDE` | Keep it as backend narrative/projection infrastructure. Do not claim a live legend-layer product surface until the news/rankings/personality routes are actually wired into the app. |
| `live_ops` | Real API for season-pass and live-events data. The service remains active in club-finance, club-ownership, predictions, ticketing, broadcast, and ops-job flows. | The shipped tasks experience no longer uses this module as a frontend product lane; it now uses live daily challenges and explicitly states that the fake season-pass loop was removed. No discoverable standalone live-ops screen is routed. | Product + economy/engagement | `HIDE` | Keep it as backend multiplier/XP infrastructure. Do not market season-pass or live-events as a shipped standalone surface unless a real routed UI returns. |
| `moments` | Real live moments engine and API with startup binding and downstream event fanout. It participates in live clip/highlight generation and event propagation. | Match and home surfaces talk about key moments, but no discoverable standalone frontend moments feed consumes `/api/moments/live` directly. | Product + live-match media | `HIDE` | Keep it as supporting live-match media infrastructure. If product wants a standalone moments feed, route it explicitly instead of implying the backend module is already shipped as a surface. |

## Evidence Summary

- `club_social` backend surface and consumers:
  - `backend/app/club_social/router.py`
  - `backend/app/services/competition_match_service.py`
  - `backend/app/commentary/service.py`
  - `backend/app/club_sale_market/service.py`
  - `backend/app/services/creator_share_market_service.py`
- `history_engagement` backend surface and downstream usage:
  - `backend/app/history_engagement/router.py`
  - `backend/app/history_engagement/worker.py`
  - `backend/app/streamer_tournament_engine/service.py`
  - `backend/app/leaderboards/season_service.py`
- Current shipped community lane uses different seams:
  - `frontend/lib/data/community_api.dart`
  - `frontend/lib/features/social/social_screen.dart`
- Current shipped reputation lane uses different seams:
  - `frontend/lib/features/club_identity/reputation/data/reputation_repository.dart`
  - `frontend/lib/features/club_identity/reputation/presentation/reputation_screen.dart`
- `legend_layer` backend surface and projection integration:
  - `backend/app/legend_layer/router.py`
  - `backend/app/backbone/projection_runtime.py`
- `live_ops` backend usage and frontend truthfulness:
  - `backend/app/live_ops/router.py`
  - `backend/app/club_finance/service.py`
  - `backend/app/predictions/service.py`
  - `backend/app/ticketing/service.py`
  - `frontend/lib/features/tasks/tasks_screen.dart`
- `moments` backend surface and shipped product context:
  - `backend/app/moments/router.py`
  - `backend/app/moments/service.py`
  - `frontend/lib/screens/competitions/gte_live_match_center_screen.dart`
  - `frontend/lib/features/home_dashboard/home_dashboard_screen.dart`

## Product-Truth Outcome

- None of these module names currently qualify as honest standalone shipped product lanes.
- The app does ship adjacent community, reputation, daily-challenge, and match-moment experiences, but those are surfaced through different seams than `club_social`, `history_engagement`, `legend_layer`, `live_ops`, and `moments`.
- Active product claims should treat these modules as backend/supporting systems until a routed owner surface exists.
