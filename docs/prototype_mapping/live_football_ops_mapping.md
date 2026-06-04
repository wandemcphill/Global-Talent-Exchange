# Live Football Ops Prototype Mapping

## Current Detail Docs

2026-05-29 update: this file is retained as a short legacy summary. The current
docs-only live football ops mapping pass is split into:

- `live_football_ops_v13_match_center_mapping.md`
- `live_football_ops_high_fidelity_mapping.md`
- `live_football_ops_implementation_status.md`

For this pass, the active ownership boundary is only `docs/prototype_mapping/**`.
References below to feature components, tests, or mounting work are historical
mapping notes, not runtime changes made by this documentation update.

## Scope

Canonical live football work is split across backend-authoritative data parsing,
2D match-center surfaces, realtime payload reducers, competition lifecycle
views, and notification log primitives.

## V13 Mapping

- Commentary: `LiveMatchEvent` payloads render as a fan-readable timeline and
  are preserved through merge updates.
- Tabs: canonical feature components expose timeline, overlay readiness, score,
  pitch, and live intelligence primitives for the active Match Center to mount.
- Stats: `LiveMatchStatsSnapshot` parses possession, shots, shots on target,
  xG, territory, pressure, market context, and shot maps from backend payloads.
- Score display: `CanonicalLiveScorebug` renders only the score and clock state
  present on `LiveMatchSnapshot`.
- Timeline: missing event payloads render empty or blocked states; no local
  events are produced.

## High-Fidelity Mapping

- Pitch rendering: `CanonicalPitch2D` draws a 2D pitch with backend lineup and
  overlay payloads.
- Overlay modes: shape, pressure, shots, xG, territory, and market are exposed
  through `LiveMatchOverlayMode` and `canonicalOverlayStatuses`.
- xG: shot markers scale from backend xG values when present.
- Inspector rail: `CanonicalLiveIntelligenceRail` renders parsed backend live
  intelligence signals and blocks when the payload is absent.
- Tactical visualization: tactical notes are still text-backed in the current
  model; richer lane/zone payloads remain a follow-up.
- Live intelligence: parser coverage exists in `live_match_fixtures.dart`; the
  allowed feature component now renders it, while the legacy competition screen
  still needs an integration pass outside this guardrail.

## Guardrail Status

- Implemented inside guardrail:
  - data parser/merge authority
  - canonical match-center feature primitives
  - realtime live snapshot/commentary reducers
  - compete bracket/lifecycle primitives
  - notification grouped/unread log primitives
  - scoped tests for each allowed feature folder

- Still blocked by ownership:
  - mounting canonical `features/match_center` components into the active
    `screens/competitions` Match Center
  - wiring production navigation to the new compete feature
  - removing legacy native match viewer imports outside allowed folders
  - replacing active competition hub bracket summaries with backend bracket
    payload rendering
