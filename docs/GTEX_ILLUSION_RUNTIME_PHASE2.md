# GTEX Illusion Runtime Phase 2 (Quarantined)

Status: deprecated, internal-only, and not part of the canonical GTEX product surface.

This document is retained as a quarantine record for the legacy Illusion runtime. It is not a setup guide for production, public API consumers, or Flutter surfaces.

## Canonical Direction

The active GTEX match experience is the backend-authored 2D broadcast match center. Production clients must consume canonical match center state, websocket events, timeline payloads, stats, xG, overlays, and commentary from the match center contracts.

Do not promote Illusion runtime paths from:

- production navigation
- public API contracts
- generated frontend bindings
- deployment checks
- monetization surfaces
- user-facing docs

## Retired Public Exposure

The legacy backend payload path below is quarantined and must stay absent from generated/static contracts:

```text
/api/match-viewer/{matchId}/illusion
```

If backend implementation code remains temporarily, it is for dependency analysis only. The route must not appear in `docs/ROUTE_MAP.json`, `docs/FINAL_API_SCHEMA.json`, shared API contracts, frontend generated bindings, or production route promotion.

## Historical Runtime Notes

The former runtime could load precomputed timelines from local files, embedded resources, or a temporary API helper. Those instructions are intentionally retired:

- `npm run gtex:api:illusion`
- local `/api/illusion/*` helper endpoints
- runtime URL mode for match viewer Illusion payloads
- local fallback generation as product truth

Any remaining Unity or pseudo-render code must be treated as quarantined legacy implementation until dependency analysis proves what can be deleted safely. Reusable orchestration or event logic may be extracted only if it is independent from rendering and does not reintroduce public Illusion surfaces.

## Migration Rule

When touching old Illusion references, migrate toward:

- canonical 2D broadcast match center contracts
- backend-owned clocks, scores, events, stats, positions, xG, momentum, and commentary
- explicit loading, empty, blocked, syncing, degraded, error, and confirmed states
- realtime reconnect semantics

No GTEX screen should infer or simulate match truth locally.
