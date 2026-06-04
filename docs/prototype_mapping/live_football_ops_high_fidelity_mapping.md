# Live Football Ops High-Fidelity Mapping

Source prototype: `docs/GTEX_FOOTBALL_OS_HIGH_FIDELITY_PROTOTYPE.html`

Guardrail: this document is mapping only. No runtime, frontend, backend, or legacy engine code is changed by this work.

## Prototype Surface

The high-fidelity prototype presents a richer "2D Match Center" operations view:

- A scorebug with home/away score, clock, match phase, venue, and competition context.
- A tactical 2D pitch with overlay modes for shape, pressure, shots, xG, territory, and market.
- xG, possession, shots, territory, momentum, and market hooks in compact live metrics.
- An official event feed with time, event type, player, team, commentary, xG, and zone.
- Player ratings with xG contribution.
- A contextual inspector for players, clubs, and match incidents.
- A live intelligence rail with tactical alerts, key events, and market impact.

## Feature Mapping

| High-fidelity feature | Existing production surface | Status | Mapping notes |
| --- | --- | --- | --- |
| Scorebug | Flutter live match center, match-viewer payloads | Implemented, data dependent | Score and phase must come from backend/current engine. |
| 2D tactical pitch | Flutter live center pitch painter, 2D tactical viewer widgets, match-viewer timeline frames | Implemented | Keep pitch rendering lightweight and data-driven. |
| Overlay selector | `LiveMatchOverlayMode` values: shape, pressure, shots, xg, territory, market | Implemented in frontend model | Overlay availability depends on stats payload support. |
| Shape overlay | formation/shape painter and match-viewer player positions | Partially implemented | Needs reliable player coordinates and formation state for high fidelity. |
| Pressure overlay | pressure stats and frame pressure/compactness fields | Partially implemented | Backend must supply pressure values; clients should not invent them. |
| Shot map overlay | `LiveMatchStatsSnapshot.shotMap` | Partially implemented | Requires shot coordinates and shot outcome data. |
| xG overlay | expected goals totals and shot-map xG weights | Partially implemented | Frontend can render xG when provided; match-viewer event schema does not currently expose per-event xG. |
| Territory overlay | territory stats and split-zone painter | Partially implemented | Requires backend territory values. |
| Market overlay | market signal/detail fields in live stats | Partially implemented | Market context should remain ops/backend-provided, not client-generated. |
| Event feed | live commentary feed, snapshot events, match-viewer event stream | Implemented, data dependent | High-fidelity event rows need richer event metadata than basic commentary. |
| Player ratings | player/rating rows in high-fidelity prototype; production lineup/status data | Gap | Needs a canonical player rating payload for live match center. |
| Inspector | high-fidelity prototype `renderInspector(entity)` | Gap | Production does not yet have an equivalent full incident/player/club inspector. |
| Tactical assistant | tactical suggestions and live intelligence parsing | Partially implemented | Requires backend `tactical_suggestions` and `live_intelligence` payloads. |
| Momentum/timeline | match momentum field, timeline frames, event ticker | Partially implemented | Live center supports momentum-style presentation when payloads supply it. |

## Layer Notes

Frontend:

- `gte_live_match_center_screen.dart` already separates live commentary/key moments from tabbed Timeline, Stats, Overlays, Lineups, and Incidents.
- `LiveMatchOverlayMode` already names the high-fidelity overlay set.
- The pitch painter can render shape, pressure, shots, xG, territory, and market views when the snapshot has the required stats.
- `LiveMatchLiveIntelligence.fromPayload` can parse live intelligence signals when the backend sends them.
- The separate match broadcast screen is intentionally blocked and points users toward the canonical 2D tactical viewer.

Backend:

- `match_viewer.py` exposes canonical match-viewer state, event streams, timeline frames, presentation, monetization, and integrity payloads.
- Live match routes expose commentary/session access and websocket/polling paths.
- The match-viewer event schema carries event type, minute, team/player, score, banner, commentary, emphasis, flags, review, score commit, positions, and ball data.
- The current match-viewer event schema does not expose per-event xG, inspector payloads, or full live intelligence context.

Legacy engine:

- The existing engine models map score, phase, possession side, active event id, camera preset, pitch size, ball position, and event commentary/banner fields.
- The existing engine can consume score/timeline/commentary-style data, but xG, market, inspector, and live intelligence are not present in the inspected model.
- P6V visual runtime work should stay additive and should not delete or replace the current GTEX runtime.

## Implementation Rules For This Mapping

- Treat backend/current engine as the authority for score, event order, phase, and clock.
- Do not synthesize high-fidelity xG, market, inspector, or live intelligence values on the client.
- Keep overlays lightweight: vector/canvas/SVG-style drawing, no heavy assets.
- Preserve the canonical 2D tactical viewer path while broadcast-style presentation remains blocked.
- Use the high-fidelity prototype as a UX and contract reference, not as a runtime source of truth.

## Blocked Outside This Guardrail

- Implementing the full inspector UI and its player/club/incident actions is a frontend product change.
- Adding per-event xG, player ratings, tactical assistant payloads, or market intelligence requires backend/schema work.
- Adding xG/live intelligence fields to legacy engine match models is outside this Flutter/docs guardrail.
- Unblocking the broadcast-style match presentation route is outside docs ownership.
- Any P7/P8 engine replacement work remains blocked until the project phase gates are satisfied.
