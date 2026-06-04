# Live Football Ops v13 Match Center Mapping

Source prototype: `C:\Users\ayomc\Downloads\Gtex_prototype_v13 (5).html`

Guardrail: this document is mapping only. No runtime, frontend, backend, or legacy engine code is changed by this work.

## Prototype Surface

The v13 match center prototype is a single-page browser runtime that owns match state locally:

- `renderMatch()` builds the match screen, scorebug, team names, formation labels, goal chips, pitch SVG, and match detail tabs.
- `matchScore`, `matchMinute`, `matchFT`, `matchEvents_log`, and `matchCommentary` are in-browser state.
- `startMatchClock()` increments the minute, generates weighted live events, resolves shots into goals/saves/wides, updates score, and appends commentary.
- `matchTabContent(tab)` renders Events, Commentary, Stats, Lineups, and Tactics.
- `pitchSVG()` draws a static 2D pitch with player dots and a moving ball.

Important prototype caveat: the file defines `switchMatchTab(tab)` and `matchTabContent(tab)` twice. The later definition only recognizes `events`, `stats`, `lineups`, and `tactics`, so it can shadow the intended Commentary tab. Production mapping should preserve the intended five-tab concept and should not port that duplicate-function bug.

## Production Truth Map

| v13 concept | Production mapping | Current status | Notes |
| --- | --- | --- | --- |
| Scorebug: home, away, score, minute, FT | `LiveMatchSnapshot.homeScore`, `awayScore`, `minute`, `phase`; backend match-viewer score fields | Implemented, data dependent | Backend/current engine remains the score authority. v13 local score mutation is reference behavior only. |
| Clock and match phase | `LiveMatchSnapshot.minute/phase`, match-viewer timeline frames | Implemented, data dependent | Do not recreate v13 `setInterval` authority in production clients. |
| Events tab | `LiveMatchEvent`, backend `timeline_events`/`events`, match-viewer event stream | Implemented, data dependent | Event ids, minute, type, team, player, score, banner, and commentary should be passed through from canonical sources. |
| Commentary tab | `LiveCommentaryFeedService`, snapshot commentary merge, backend commentary websocket/polling payloads | Partially implemented | Production has commentary stream plumbing, but the v13 exact tab placement is not the current Flutter layout. Commentary is currently a live view mode/feed rather than a top-level tab. |
| Stats tab | `LiveMatchStatsSnapshot`, canonical match-viewer stats payloads, frontend stat tiles | Partially implemented | Possession, shots, on-target, expected goals, territory, pressure, market context, and shot map are parsed when present. Static v13 numbers must not become hardcoded production data. Retired Illusion stat schemas must not be used for new Flutter work. |
| Lineups tab | `LiveMatchLineup`, snapshot lineups, player positions where supplied | Partially implemented | Static v13 elevens map to backend-provided lineups. Formation labels should be payload-driven. |
| Tactics tab | tactical suggestions, formation overlays, match-viewer frame fields such as pressure/compactness/possession phase | Partially implemented | v13 static tactical notes map to live tactical payloads only when backend provides them. |
| 2D pitch | Flutter live center pitch painter, match-viewer 2D timeline frames | Implemented across separate surfaces | The v13 SVG pitch is a visual reference, not the production rendering stack. |
| Local event generator | Backend match engine/live match session/current engine | Not mapped as client authority | The weighted v13 event pool is useful for intent, but production event generation belongs server-side/current-engine-side. |

## v13 Tabs To Production Tabs

The v13 intended tabs are:

1. Events
2. Commentary
3. Stats
4. Lineups
5. Tactics

The current production live match center uses:

1. Timeline
2. Stats
3. Overlays
4. Lineups
5. Incidents

It also exposes live-view modes for commentary and key moments. The closest mapping is:

| v13 tab | Production destination | Mapping note |
| --- | --- | --- |
| Events | Timeline plus Incidents | Timeline should show canonical ordered match events; Incidents can hold fouls/cards/reviews/injuries. |
| Commentary | Commentary live view/feed | Keep commentary stream separate from locally composed event rows when payloads provide both. |
| Stats | Stats tab and stat tiles | Use backend stat snapshots; include xG when present. |
| Lineups | Lineups tab | Preserve team shape, player identity, status, cards, and substitutions. |
| Tactics | Overlays plus tactical suggestions | Tactics become overlay modes, formation context, and assistant suggestions. |

## Data Contract Checklist

The production payloads needed to satisfy the v13 mapping are:

- Match identity: `match_id`, home/away names, crest/color metadata where available.
- Score authority: `home_score`, `away_score`, `minute`, `phase`, `status`.
- Event stream: ordered events with id, sequence, minute, type, team, player, score after event, banner, commentary, emphasis, flags, and review/score-commit fields where relevant.
- Commentary stream: ordered lines with source event id, minute, type, line text, team, player, and cue/context.
- Stats snapshot: possession, shots, shots on target, corners, fouls, cards, offsides, expected goals, territory, pressure, market context, and shot map when available.
- Lineups: home/away starters, formation, positions, ratings/status, cards, and substitutions.
- Tactical payload: suggestions, formation state, pressure/compactness, possession phase, transition state, and danger zone.

## Blocked Outside This Guardrail

- Fixing the duplicate `matchTabContent`/`switchMatchTab` definitions in the v13 HTML file is outside `docs/prototype_mapping/**`.
- Moving production Flutter tabs to exactly match the v13 tab order is a frontend code change.
- Adding missing backend payload fields, including richer tactical data, per-event xG, or inspector context, is a backend/schema change.
- Extending legacy engine match models for xG, live intelligence, market context, or inspector state is outside this Flutter/docs guardrail.
- Replacing the current engine with the prototype local event generator is blocked by the project phase gates and should not happen during P6/P6V mapping.
