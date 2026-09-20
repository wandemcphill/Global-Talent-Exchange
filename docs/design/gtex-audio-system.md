# GTEX Audio System & Soundtrack OS Specification

**Repository:** `wandemcphill/Global-Talent-Exchange`
**Branch:** `p7-fe-audio-soundtrack-os`
**Document Path:** `docs/design/gtex-audio-system.md`
**Status:** Verified Architecture & Implementation

---

## Executive Summary

The **GTEX Soundtrack OS** turns GTEX's single-track ambient noise into a scalable, context-aware audio engine built on Flutter, `just_audio`, and `SharedPreferences`.

This document details the soundtrack model, channel mixer, context routing, web autoplay resolution, licensing & provenance standards, matchday ducking handoff protocol, and test coverage.

---

## Architecture Overview

```
+--------------------------------------------------------------------------+
|                                GTEX UI                                   |
|   [ AmbientAudioToggleButton ]  [ GtexAudioSettingsSheet ]  [ MatchViewer ]|
+------------------------------------+-------------------------------------+
                                     |
                                     v
+--------------------------------------------------------------------------+
|                          AmbientAudioController                          |
|             (Central State & Shared Preferences Manager)                 |
+--------------------+---------------------+-------------------------------+
                     |                     |
                     v                     v
         +----------------------+  +---------------------+
         | SoundtrackCatalogue  |  |  GtexAudioMixer     |
         | - Context Indexing   |  |  - Gain Control     |
         | - Starter Tracks     |  |  - Ducking Factor   |
         | - Metadata & Licensing |  |  - Master / Music   |
         +----------------------+  +----------+----------+
                                              |
                                              v
                                   +---------------------+
                                   | MatchdayAudioHandoff|
                                   | - Match Context Sync|
                                   | - Stem Schemas      |
                                   | - Event Stings      |
                                   +---------------------+
```

---

## 1. Core Soundtrack Model & Catalogue

### Data Model (`GtexTrackMetadata`)
Every soundtrack track bundled or referenced in GTEX enforces strict metadata tracking:

- **Identity & Audio Info:** `id`, `title`, `artist`, `album`, `genre`, `bpm`, `durationSeconds`, `contexts`, `assetPath`, `streamUrl`.
- **Licensing & Provenance (Required):**
  - `source`: First-party production, Pixabay, Incompetech, or custom composition.
  - `licence`: Explicit license type (e.g., *GTEX First-Party Commercial Game Licence*, *CC-BY 4.0*).
  - `licenceUrl`: Verifiable URL pointing to terms.
  - `attributionRequired`: Boolean flag indicating if attribution UI display is legally required.
  - `provenance`: Asset origin and bundling location (e.g., `assets/media/gtex_stadium_ambient.mp3`).

### Context Model (`GtexAudioContext`)
1. **Home (`home`):** Atmospheric GTEX OS theme (90-110 BPM).
2. **Club (`club`):** Tactical HQ ambient synth.
3. **Market (`market`):** Trading floor rhythm & cyber synth (124 BPM).
4. **Competition (`competition`):** Arena hype & orchestral hybrid (128 BPM).
5. **Matchday (`matchday`):** Stadium crowd & match broadcast stems.
6. **World (`world`):** Global scouting pulse & ethnic deep house (118 BPM).
7. **Celebration (`celebration`):** Triumphant brass fanfare (132 BPM).

---

## 2. Audio Channel Mixer & Math

Final output gain $G_{\text{Music}}$ for the active Music channel is computed as:

$$G_{\text{Music}} = \text{MasterVolume} \times \text{MusicVolume} \times \text{DuckingFactor}$$

Where:
- $\text{MasterVolume} \in [0.0, 1.0]$ (persisted in `SharedPreferences`).
- $\text{MusicVolume} \in [0.0, 1.0]$ (persisted in `SharedPreferences`).
- $\text{DuckingFactor} \in [0.0, 1.0]$ (default $1.0$, ducked to $0.125$ [$-18\text{ dB}$] during matchday/commentary).

---

## 3. Matchday Handoff Protocol

When the user enters a live match surface (`/matches/viewer/:matchKey` or `GtexMatchViewerScreen`):

1. `enterMatchContext(matchKey)` switches `GtexAudioContext` to `matchday` and sets ducking factor to $0.125$.
2. The soundtrack remains playing in ducked state underneath stadium ambience.
3. Audio stem WebSocket payloads (`BroadcastAudioStemFrame`) update commentary and crowd metadata without pretending fake commentary audio streams are active.
4. Exiting the match viewer calls `leaveMatchContext()`, restoring soundtrack volume ($1.0$) and returning to `home` context over a smooth transition.

---

## 4. Web Autoplay Policies

- On Web (`kIsWeb`), if playback is initiated prior to user document interaction, `AmbientAudioController` catches the DOM exception and sets `isWebAutoplayBlocked = true`.
- The shell toggle icon transforms to a warning indicator (`Icons.warning_amber_rounded`) with a tooltip.
- Tapping the button or clicking **Enable** on the `GtexAudioSettingsSheet` banner invokes `resolveWebAutoplay()`, immediately unblocking audio.

---

## 5. UI Components

- **`AmbientAudioToggleButton`:** Compact top-bar action providing quick mute/unmute toggling, web autoplay resolution, and long-press access to settings.
- **`GtexAudioSettingsSheet`:** Native game-like bottom sheet featuring:
  - Now Playing track card with BPM, genre, and duration chips.
  - Playback controls (Play, Pause, Next Track, Shuffle).
  - Active Master & Music volume sliders.
  - Soundtrack Context manual override chips.
  - Dynamic **Music Credits & Audio Sources** view displaying verified licensing info for all bundled tracks.

---

## 6. Test Suite & Verification

Focused test suite in `frontend/test/audio/gtex_audio_system_test.dart` verifies:
- Catalogue filtering and starter track metadata completeness.
- Gain calculations and ducking operations in `GtexAudioMixer`.
- Volume and mute persistence in `SharedPreferences`.
- Rebuild/navigation track preservation (avoiding track restarts).
- Web autoplay resolution mechanics.
- Full UI sheet and toggle button widget interactions.
