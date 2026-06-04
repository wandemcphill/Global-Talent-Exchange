# Live Football Ops Implementation Status

Scope: prototype mapping documentation for live football operations under `docs/prototype_mapping/**`.

No code changes are included here. This status document captures what can be mapped today and what remains blocked outside the documentation guardrail.

## Status Snapshot

| Area | Status | Evidence from current surfaces |
| --- | --- | --- |
| v13 score, clock, and event intent | Mapped | Production has score/minute/phase/event fields across Flutter snapshots and backend match-viewer payloads. |
| v13 commentary feed | Partially implemented | Commentary websocket/polling and snapshot merge services exist; exact v13 Commentary tab placement is not the current Flutter layout. |
| v13 tabs | Partially implemented | Production tabs are Timeline, Stats, Overlays, Lineups, Incidents, with commentary as a live view mode. |
| v13 static stats | Partially implemented | Production parses live stats when supplied; static prototype values should not be hardcoded. |
| 2D tactical pitch | Implemented | Flutter live center and tactical viewer paths provide 2D pitch rendering and event playback surfaces. |
| High-fidelity overlays | Partially implemented | Shape, pressure, shots, xG, territory, and market overlay modes exist; availability is payload-dependent. |
| xG | Partially implemented | Frontend stats can parse/display expected goals and shot-map weights; backend match-viewer event schema inspected here does not carry per-event xG. |
| Timeline and incidents | Implemented, data dependent | Backend match-viewer and live commentary/event services provide timeline/event foundations. |
| Tactical/live intelligence | Partially implemented | Frontend can parse tactical suggestions/live intelligence, but backend payload completeness is required. |
| Inspector | Gap | The high-fidelity prototype inspector does not have a matching full production implementation in the inspected surfaces. |
| Broadcast-style presentation | Blocked | Existing screen indicates broadcast presentation is coming later and routes users to the canonical 2D tactical viewer. |

## Ready To Map Now

- v13 match center concepts to canonical live match snapshot fields.
- Events and commentary to backend stream/polling payloads.
- Score and phase to backend/current-engine authority.
- Stats and overlays to `LiveMatchStatsSnapshot` and `LiveMatchOverlayMode`.
- 2D pitch concepts to Flutter pitch painters and match-viewer frames.
- Tactical suggestions and live intelligence to payload-driven UI only.

## Remaining Blocked Items

These are intentionally outside the current ownership boundary:

- Editing any source file outside `docs/prototype_mapping/**`.
- Fixing the duplicate v13 prototype tab functions in `Gtex_prototype_v13 (5).html`.
- Changing Flutter tab structure or adding the full high-fidelity inspector.
- Adding backend fields for per-event xG, player ratings, inspector context, market hooks, or richer tactical intelligence.
- Extending legacy engine match models for xG, market context, inspector payloads, or live intelligence.
- Enabling the blocked broadcast-style presentation route.
- Running P7/P8 engine replacement work before the documented phase gates allow it.

## Verification

No engine build, frontend test, or backend test was run because this is a documentation-only mapping update.
