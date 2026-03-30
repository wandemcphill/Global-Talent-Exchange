# CODEX Match Broadcast Package Report

## Executive Summary

The match experience now presents three clearer lanes on the shipped runtime:

- `/matches` remains the live discovery hub.
- `/matches/broadcast/:matchKey` is now a broadcast-package surface with a scene-led matchday presentation flow.
- `/matches/3d/:matchKey` keeps the existing Flutter 3D lane but now adds a richer TV-style overlay package and event-driven camera choreography.

The broadcast route now feels substantially closer to the target Football Manager style. It stages:

- a match title banner
- official roster sheets
- home and away formation boards
- standings and context overlays
- reaction and story panels
- a pseudo-3D on-air lens with scorebar and commentary ribbon
- halftime/fulltime recap boards when the live frame phase supports them

The 3D route now adds:

- a new scorebar
- clock and phase state
- a lower-third commentary ribbon
- a tactical HUD
- a ratings strip
- event-driven camera preset mapping on the Flutter 3D lane

## Implemented Modules

### Broadcast Package

- Match title banner with competition, date, kickoff, venue, and route-source pills
- Official roster card with starting XI and bench columns
- Home and away formation boards with pitch coordinates when available
- Standings and context board
- Reaction desk and storyline panel
- Scene-directed hero transitions across:
  - title banner
  - roster card
  - home formation
  - away formation
  - context board
  - reactions
  - kickoff/live lens
  - halftime board
  - fulltime board
- Pseudo-3D live lens with:
  - scorebar
  - clock
  - camera-state label
  - commentary ribbon

### Match Sim 3D

- Match scorebar overlay
- Lower-third commentary ribbon
- Tactical HUD with team instructions and ratings strip
- Event-driven camera-state resolution mapped into the existing Flutter 3D camera presets

## Data Sources Used

### Backend

- `/api/match-viewer/{matchKey}`
- `/api/match-viewer/{matchKey}/session`
- `/api/broadcast/home`

### Match Package Sources

- existing `match_viewer` payloads
- stored `replay_payload` metadata when present
- live match hub fallback when stored metadata is absent
- existing competition metadata fields already attached to match records
- existing replay summary, broadcast session, fan reaction, media event, and notification payload sections

### Derived Fields

The implementation only derives presentation fields from existing truth sources:

- formation-board coordinates from replay payload visuals or visible frame player positions
- roster grouping from starter and bench ordering
- standings/context callouts from attached competition metadata
- commentary/rating/momentum recaps only when the visible payload is effectively fulltime

## Remaining Missing Data Fields

The package degrades honestly when these fields are absent:

- verified player portraits
- richer coach/staff cards beyond name and tactical notes
- guaranteed referee data on every live match
- universal standings context for every live stream
- richer injury, suspension, and lineup-change metadata
- richer halftime/fulltime recap data on live sessions that have not yet exposed those sections
- more granular camera presets beyond the current Flutter 3D camera enum

## Route and Module Ownership

- `/matches`
  - discovery, live availability, and route entry points
- `/matches/viewer/:matchKey`
  - 2D tactical/event-first lane
- `/matches/broadcast/:matchKey`
  - title banner
  - roster card
  - formation boards
  - standings/context
  - reactions/storylines
  - pseudo-3D live lens
  - halftime/fulltime package boards
- `/matches/3d/:matchKey`
  - Flutter 3D scene
  - scorebar
  - commentary ribbon
  - tactical HUD
  - ratings strip
  - event-driven camera choreography
- `/matches/native-3d`
  - still blocked until a real native bridge is available

## Capability Matrix

- 2D: LIVE
- Broadcast Package: LIVE
- Flutter 3D: LIVE
- Native 3D: BLOCKED

## Next Polish Steps

- feed richer competition-context metadata into more live matches so standings panels appear more often
- add verified staff cards, referee details, and lineup-change callouts when the backend exposes them
- expand the Flutter 3D camera enum so the named scene-director states can map one-to-one instead of collapsing into `broadcast`, `sideline`, and `goalbox`
- add richer halftime/fulltime recap data once more live sessions expose post-match summary sections
