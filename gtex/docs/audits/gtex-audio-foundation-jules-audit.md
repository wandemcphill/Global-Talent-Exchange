# GTEX Audio & Soundtrack Foundation Audit & Implementation Brief

**Repository:** `wandemcphill/Global-Talent-Exchange`
**Branch:** `main`
**Author:** Jules (GTEX Senior Systems Engineer)
**Document Path:** `docs/audits/gtex-audio-foundation-jules-audit.md`
**Status:** Canonical Engineering Brief

---

## Executive Summary

This document establishes the verified technical baseline and target engineering architecture for the **GTEX Audio & Soundtrack OS**.

Currently, GTEX possesses a minimal audio foundation: a single local audio asset (`gtex_stadium_ambient.mp3`), a singleton `AmbientAudioController` using `just_audio` (version `^0.10.0`), a shell toggle button (`AmbientAudioToggleButton`), and basic background noise management. Additionally, backend WebSocket endpoints (`/api/matches/{match_id}/audio/stems/stream`) and Unity C# scripts (`GtexStadiumAtmosphere`, `MatchAudio`) exist for matchday atmosphere, but operate in isolation without a unified Flutter playback manager, context-aware soundtrack system, or multi-channel audio mixer.

This brief outlines a robust, scalable audio architecture designed to power GTEX's dynamic ambient music, matchday broadcasts, ducking, commentary priority, and multi-channel audio mixing across Web, Mobile, and Desktop platforms.

---

## Part 1: Repo-Verified Architecture Facts

### 1. Current Audio Architecture
- **Framework & Dependencies:** `pubspec.yaml` specifies `just_audio: ^0.10.0`. `just_audio_web` and `just_audio_platform_interface` are resolved in `pubspec.lock`.
- **Primary Controller:** `frontend/lib/services/ambient_audio_controller.dart` defines `AmbientAudioState` (abstract class) and `AmbientAudioController` (concrete `ChangeNotifier`).
- **Initialization & Scope:** Instantiated in `_GteFrontendAppState.initState()` inside `frontend/lib/app/gte_frontend_app.dart`, passed into `buildGtexAppRouter` and stored in `GteNavigationShellScreen`.
- **Asset Track:** Single hardcoded MP3 file: `assets/media/gtex_stadium_ambient.mp3` (24.2 KB).

### 2. Lifecycle and Ownership
- `AmbientAudioController` is top-level app-owned.
- Instantiated in `_GteFrontendAppState` and lives for the entire application lifecycle.
- Automatically handles teardown in `dispose()` by calling `_player.dispose()` (guarded against execution inside `isFlutterTestEnvironment` to prevent platform-channel teardown races).

### 3. Playback Persistence Across Navigation
- Because `AmbientAudioController` is owned above `MaterialApp.router` / `GoRouter`, audio playback continues uninterrupted across route changes, sub-lane shifts, dialog overlays, and bottom sheet presentations.

### 4. Web Autoplay Restrictions and Current Handling
- Browsers enforce strict user-gesture policies before allowing unmuted audio playback.
- `AmbientAudioController.bootstrap()` inspects `SharedPreferences` key `gtex.ambient_audio.muted`.
- On Web (`kIsWeb`), if `_isMuted` is `true` (the default), `bootstrap()` aborts before loading or playing the track, avoiding unhandled browser DOM exceptions (`NotAllowedError`). Playback is deferred until the user explicitly taps `AmbientAudioToggleButton`.

### 5. Native / Mobile Behaviour
- On iOS/Android, `just_audio` uses native player engines (`AVPlayer` on iOS, `ExoPlayer` on Android).
- Unmuted auto-play attempts on mobile execute `preload()` and `play()`. However, background audio sessions and interrupt handling (e.g., incoming calls, iOS audio category routing) are currently unconfigured.

### 6. Existing Volume / Mute Persistence
- Mute status is stored in `SharedPreferences` under `gtex.ambient_audio.muted`.
- Default mute state is `true` (muted by default).
- Default volume level is fixed at `0.22` (`22%`).
- `toggleMuted()` updates `SharedPreferences` and sets `_player.setVolume(nextMuted ? 0 : defaultVolume)`.

### 7. Existing Asset Pipeline
- Defined in `frontend/pubspec.yaml` under `assets: - assets/media/`.
- Verified present in `AssetManifest`:
  - `assets/media/gtex_stadium_ambient.mp3`
  - `assets/media/gtex_cup_lift_hero.mp4`
  - `assets/media/gtex_cup_lift_poster.webp`
  - `assets/media/gtex_matchday_wallpaper.png`
  - `assets/media/gtex_living_football_os_wallpaper.svg`

### 8. Existing Premium-Media Architecture
- `frontend/test/premium_media_test.dart` verifies that background wallpaper video/images (e.g., `gtex_cup_lift_hero.mp4`) render as non-blocking background visual layers, separate from the ambient audio pipeline.

### 9. Existing Match / Commentary / Audio Infrastructure
- **Frontend Commentary:** `MatchCommentaryEngine` (`frontend/lib/services/match_commentary_engine.dart`) generates textual commentary strings from `MatchEvent` data.
- **Frontend Live Feed:** `LiveCommentaryFeedService` (`frontend/lib/features/match/live_commentary_feed_service.dart`) handles real-time text commentary streams.
- **Backend Audio Stems:** `backend/app/live_matches/router.py` exposes WebSocket endpoint `GET /api/matches/{match_id}/audio/stems/stream` powered by `CommentaryOrchestratorService` (`backend/app/broadcast_network/commentary_service.py`), streaming structured audio stem frames (`commentary`, `crowd`, `stadium_fx`) with interrupt priorities.

### 10. Existing Backend Audio Contracts
- `BroadcastAudioManifestView` and `BroadcastAudioStemFrameView` schemas in `backend/app/broadcast_network/schemas.py`.
- WebSocket payloads deliver fields: `stem_type`, `cue_text`, `speaker_role`, `voice_profile`, `speech_rate`, `intensity`, and `interrupt_priority`.

### 11. Unity Audio Integration Boundaries
- `GtexStadiumAtmosphere` (`Gtex_Test_Migration/Assets/Code/GTEX/GtexStadiumAtmosphere.cs`) uses local Unity `AudioSource` components (`ambienceSource`, `effectsSource`) and loads clips from `Resources.Load<AudioClip>`:
  - `GTEX/FreeAssets/Audio/mixkit_ambient_sports_crowd`
  - `GTEX/FreeAssets/Audio/mixkit_crowd_at_the_stadium`
  - `GTEX/FreeAssets/Audio/mixkit_huge_crowd_cheering_victory`
  - `GTEX/FreeAssets/Audio/mixkit_police_short_whistle`
- `MatchAudio` (`Gtex_Test_Migration/Assets/Code/Audio/MatchAudio.cs`) listens to `FStudio.Events` (e.g., `BallHitNetEvent`, `PlayerShootEvent`, `RefereeShortWhistleEvent`) and triggers `AudioManager.Play(...)`.

### 12. Existing Tests & Test Gaps
- **Existing:** `frontend/test/premium_media_test.dart` tests `AmbientAudioToggleButton` interactions and confirms asset inclusion in `AssetManifest`.
- **Gaps:** No tests for audio ducking, audio channel mixing, playlist transitions, network stream buffering, web autoplay fallback handlers, or matchday handoff state transitions.

### 13. Risks in Evolving AmbientAudioController
- **Test Suite Shutdown Races:** `just_audio` platform channels can throw asynchronous stream-channel closure errors during Flutter widget test teardowns (already guarded via `isFlutterTestEnvironment`).
- **Memory Leaks:** Multiple `AudioPlayer` instances for soundtrack playlists, stingers, commentary, and crowd FX must be strictly managed to avoid mobile OS memory crashes.
- **Web Autoplay Blocks:** Web browsers will block unmuted HTML5 audio elements initialized without a user gesture.

---

## Part 2: Verified Existing Capabilities & Gaps

| Feature Area | Repo Status | Capability Verified | Identified Gap |
| :--- | :--- | :--- | :--- |
| **Global Ambient Toggle** | **Supported** | `AmbientAudioToggleButton` in navigation top bar cleanly toggles state and persists preference in `SharedPreferences`. | Only handles global mute on/off; lacks volume slider or sub-channel control. |
| **Persistence** | **Supported** | Soundtrack stays active during route navigation across all GoRouter paths. | Single static audio file loop; no context-aware playlist dynamic switching. |
| **Web Autoplay Handling** | **Partial** | Suppresses playback on startup if muted, preventing DOM errors. | No visual "Click to Enable Audio" prompt when unmuted state is blocked by browser policy. |
| **Multi-Track Soundtrack** | **Missing** | None. | No soundtrack controller, track switching, fading, or metadata registry. |
| **Channel Mixer** | **Missing** | Single volume setting (`0.22`). | No Master, Music, Commentary, Crowd, or FX channels with independent gain control. |
| **Matchday Ducking** | **Missing** | None. | Music does not lower volume when matchday audio or commentary triggers. |
| **Backend Audio Stems** | **Supported (BE)** | WebSocket stem feed and CommentaryOrchestrator live on backend. | Flutter frontend does not consume or decode the audio stem WebSocket payload. |

---

## Part 3: Proposed Architecture

### 1. Architectural Blueprint
The target architecture introduces a centralized **GTEX Audio OS** engine residing in `frontend/lib/services/audio/`. It decouples high-level UI controls from low-level audio playback engines, introducing a multi-player system built on `just_audio`.

```
+-------------------------------------------------------------------------+
|                              GTEX UI                                    |
|   [ AmbientAudioToggleButton ]  [ AudioSettingsSheet ]  [ MatchViewer ] |
+------------------------------------+------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                        GtexAudioController                              |
|                 (Central State & Lifecycle Coordinator)                 |
+-------------------+--------------------+-------------------+------------+
                    |                    |                   |
                    v                    v                   v
        +-------------------+  +-------------------+  +-------------------+
        |  SoundtrackEngine |  |  MatchAudioEngine |  |  GtexAudioMixer   |
        |  - Context Sync   |  |  - WebSocket Stems|  |  - Gain Control   |
        |  - Crossfade      |  |  - Priority Queue |  |  - Ducking Logic  |
        |  - Track Registry |  |  - Event Stings   |  |  - Master/Sub-G   |
        +---------+---------+  +---------+---------+  +---------+---------+
                  |                      |                      |
                  +----------------------+----------------------+
                                         |
                                         v
                         +-------------------------------+
                         |   just_audio Player Pool      |
                         |  [Music] [Stem] [Sting] [SFX] |
                         +-------------------------------+
```

---

## Part 4: State Model & Soundtrack Context Model

### 1. State Model (`GtexAudioState`) — *[Proposed Target Architecture]*
The global audio state is modeled as an immutable data class exposed via `NotifierProvider`:

```dart
enum AudioPlayState { uninitialized, buffering, playing, paused, ducked, error }

class GtexAudioState {
  final bool isMuted;
  final double masterVolume;   // 0.0 - 1.0
  final double musicVolume;    // 0.0 - 1.0
  final double commentaryVolume;// 0.0 - 1.0
  final double crowdVolume;    // 0.0 - 1.0
  final double effectsVolume;  // 0.0 - 1.0
  final AudioContext activeContext;
  final TrackMetadata? currentTrack;
  final AudioPlayState playState;
  final bool isWebAutoplayBlocked;
  final Object? lastError;
}
```

### 2. Soundtrack Context Model — *[Proposed Target Architecture]*
The GTEX UI is mapped to distinct audio contexts. As users navigate routes, the `SoundtrackEngine` evaluates the current `GtePrimaryDestination` or route path and transitions soundtrack themes seamlessly with a 1.5-second crossfade:

| Route / Context | Primary Destination | Default Soundtrack Theme | Tempo / Mood |
| :--- | :--- | :--- | :--- |
| **Home** | `home` | "GTEX OS Atmosphere" | Chill / Ambient (90 BPM) |
| **Club** | `club` | "Tactical HQ" | Focused / Electronic (110 BPM) |
| **Market** | `market` | "Trading Floor Dynamics" | Upbeat / Modern (124 BPM) |
| **Competition** | `competitions` | "Arena Pressure" | Hype / Orchestral (128 BPM) |
| **Matchday** | `/matches/viewer/*` | "Stadium Noise & Match Stems" | Ducked Music / Atmospheric |
| **Trophy / Celebration** | Victory Modals | "Champions Triumph" | Triumphant Brass / High Energy |
| **World** | `regens`, `world` | "Global Scouting Pulse" | Ethnic Fusion / Deep House |

---

## Part 5: Catalogue Model & Licensing Strategy

### 1. Commercial Catalogue Requirements
- **Strict Prohibition:** GTEX does **NOT** support user-uploaded music, Spotify/Apple Music integrations, or third-party web scrapers. All tracks must be explicitly curated.
- **Catalogue Scale:** Architecture designed to support dozens to hundreds of tracks streamed via CDN with local asset fallback for boot tracks.

### 2. Data Model (`TrackMetadata`) — *[Proposed Target Specification]*

> **Note:** The JSON schema below, CDN endpoints (`https://cdn.gtex.io/...`), proposed API routes (`GET /api/v2/audio/catalog`), and example metadata fields (e.g. `"artist": "GTEX Audio Team"`) represent **proposed target architecture specifications** for future implementation and are **not** existing production features.

```json
{
  "track_id": "gtex-trk-001",
  "title": "Neon Pitch",
  "artist": "GTEX Audio Team (Proposed)",
  "album": "OS Vol. 1",
  "genre": "Synthwave / Cyber-Football",
  "bpm": 120,
  "duration_seconds": 184,
  "context_tags": ["home", "market"],
  "stream_url": "https://cdn.gtex.io/audio/soundtracks/gtex-trk-001.mp3",
  "asset_fallback": "assets/media/soundtrack/gtex-trk-001.mp3",
  "provenance": "GTEX First-Party Commission",
  "licence_type": "Royalty-Free Commercial Game Licence",
  "licence_source": "Internal Composition / Pixabay Content License",
  "licence_url": "https://gtex.io/legal/audio-licensing",
  "attribution_required": false,
  "commercial_use_suitable": true
}
```

### 3. Distribution Strategy Recommendation: **Hybrid Architecture**
- **First-Party Bundled Assets:** Pre-pack 3-4 lightweight core boot tracks (e.g., Home, Matchday Ambient, Victory Sting) directly in the Flutter asset bundle (`assets/media/soundtrack/`) to guarantee immediate offline/instant-play availability.
- **CDN / Object Storage:** Host the broader catalogue (dozens/hundreds of tracks) on a high-availability CDN (e.g., Cloudflare R2 / AWS CloudFront) with local disk caching using `just_audio` cache handlers.
- **Rationale:** Hybrid distribution keeps app download size under 50 MB while allowing infinite soundtrack expansion via remote manifest updates (`GET /api/v2/audio/catalog` — *proposed endpoint*).

---

## Part 6: Mixer Model & Matchday Handoff Contract

### 1. Audio Mixer Architecture (`GtexAudioMixer`) — *[Proposed Target Architecture]*
The mixer controls 5 hierarchical channels. Final output gain for any channel $C$ is defined as:
$$\text{Gain}_C = \text{MasterVolume} \times \text{ChannelVolume}_C \times \text{DuckingFactor}_C$$

```
+--------------------------------------------------------------------+
|                           MASTER GAIN                              |
+-------+------------------+------------------+----------------------+
        |                  |                  |                      |
        v                  v                  v                      v
  [ MUSIC GAIN ]   [ COMMENTARY GAIN ]  [ CROWD GAIN ]    [ EFFECTS GAIN ]
        |                  |                  |                      |
  (Ducking -18dB)     (Priority 1)      (Stems/Ambience)      (UI/Stings)
```

### 2. Matchday Handoff Contract & Ducking Matrix — *[Proposed Target Architecture]*
When a user enters a live Matchday Viewer surface (`/matches/viewer/:matchKey`), `GtexAudioController` executes the **Matchday Handoff Protocol**:

1. **Music Ducking:** Soundtrack channel volume is ducked by `-18 dB` (factor $0.125$) over $600\text{ ms}$.
2. **Commentary Priority:** Commentary stem audio commands full channel volume ($1.0$).
3. **Crowd Audio Control:** Crowd ambiance streams from backend WebSocket stems or local Unity audio sources.
4. **Event Stings:** Key events trigger immediate audio stings with priority interrupts:
   - **Goal:** Music ducks to $0.0$, Goal Sting plays immediately ($1.0$ volume), Crowd Cheer peaks ($1.0$).
   - **Half-Time / Full-Time:** Whistle sting plays, commentary finishes cue, soundtrack gradually restores over $2.0\text{s}$.
5. **Restore Soundtrack:** Exiting matchday viewer smoothly restores music volume back to standard user-defined level over $1.5\text{s}$.

---

## Part 7: External Licence / Source Research

### 1. Primary Free/Game-Compatible Sourcing Strategy
For GTEX's initial launch catalogue, music sourcing focuses strictly on free, game-compatible commercial licenses:
- **Pixabay Audio (Content License):** Free for commercial game use and video game monetization without royalties, provided raw audio files are not redistributed standalone.
- **Incompetech (CC-BY 4.0 / Free Attribution License):** Provides free commercial game usage under Creative Commons Attribution 4.0, or optional low-cost zero-attribution licenses.

### 2. Future Paid Licensing Alternatives (Enterprise Options)
For future expanded soundtrack releases beyond the initial free-source catalogue:
- **Epidemic Sound (Enterprise Game License):** Offers paid commercial subscription and game synchronization licensing. *Note: Epidemic Sound operates on a paid licensing model and is explicitly categorized as a future commercial upgrade path, not part of the initial free-source launch strategy.*
- **Custom Game Commissions:** Direct work-for-hire agreements with indie game composers providing exclusive royalty-free ownership.

---

## Part 8: Browser Autoplay & Platform Technical Constraints

### 1. Web Autoplay Restrictions
Modern browsers (Chrome, Safari, Edge, Firefox) block audio element playback with `NotAllowedError: play() failed because the user didn't interact with the document first.`

### 2. Target Handling Strategy
1. App boots in `muted` state if no prior user interaction exists.
2. If `SharedPreferences` has `isMuted = false`, `GtexAudioController` attempts an unmuted boot play.
3. If `play()` throws a `NotAllowedError` or `DOMException`, `GtexAudioController` sets `isWebAutoplayBlocked = true`.
4. The UI surfaces a subtle, non-intrusive floating banner or highlights `AmbientAudioToggleButton` with a tooltip: *"Click anywhere to enable stadium sound"*.
5. First user tap on any interactive UI element resolves the AudioContext state and clears `isWebAutoplayBlocked`.

---

## Part 9: Test Strategy & Verification

### 1. Automated Test Suite Expansion
- **Unit Tests (`frontend/test/audio/gtex_audio_mixer_test.dart`):**
  - Verify ducking gain calculations across Master, Music, Commentary, and FX.
  - Verify persistence of channel volume sliders to `SharedPreferences`.
- **Controller Tests (`frontend/test/audio/gtex_audio_controller_test.dart`):**
  - Verify context-aware track selection based on primary route destinations.
  - Test mock player transitions and error handling during network failures.
  - Verify test environment guards (`isFlutterTestEnvironment`) prevent native channel teardown crashes.
- **Golden / Widget Tests (`frontend/test/audio/ambient_audio_toggle_button_test.dart`):**
  - Verify audio toggle button states (Muted, Unmuted, Autoplay Blocked).

---

## Part 10: Unresolved Questions & Risks

1. **Unity WebGL Audio Coexistence:** When Unity 3D match runtime runs inside Flutter Web via WebGL/iframe, Unity's internal WebAudio context can conflict with `just_audio`'s HTML5 Audio element. *Resolution required during Phase 8 Unity integration.*
2. **Audio Stem Latency:** Backend WebSocket audio stem streaming (`/api/matches/{match_id}/audio/stems/stream`) may introduce buffer jitter on mobile connections. *Needs client-side jitter buffer implementation.*

---

## Part 11: Implementation Sequence

```
Phase 1: Core Foundation & Mixer Architecture
├── Create frontend/lib/services/audio/models/
├── Implement GtexAudioMixer & GtexAudioState
└── Write unit tests for Gain calculation & SharedPreferences persistence

Phase 2: Context-Aware Soundtrack Engine
├── Create SoundtrackEngine & TrackMetadata registry
├── Wire GoRouter route listener in buildGtexAppRouter
└── Implement 1.5s crossfade between route transitions

Phase 3: Matchday Audio & Ducking Contract
├── Implement MatchdayHandoffController
├── Wire ducking trigger on opening /matches/viewer/*
└── Connect commentary & crowd priority queues

Phase 4: Audio Settings UI & Web Autoplay UX
├── Implement GtexAudioSettingsSheet (Master, Music, Commentary sliders)
└── Build Web Autoplay interaction listener & banner
```

---

## Part 12: Codex Implementation Prompt

```text
PROMPT FOR CODEX SLICE IMPLEMENTATION:

Execute the GTEX Audio OS Foundation based on docs/audits/gtex-audio-foundation-jules-audit.md.

Scope of work:
1. Create `frontend/lib/services/audio/` directory containing:
   - `gtex_audio_mixer.dart`: Multi-channel gain calculator (Master, Music, Commentary, Crowd, FX) with ducking support.
   - `gtex_audio_state.dart`: Immutable state model and NotifierProvider.
   - `soundtrack_engine.dart`: Playlist context mapper and crossfading manager built on `just_audio`.
   - `track_metadata.dart`: Catalogue data model with explicit licensing fields.
2. Update `AmbientAudioController` to delegate to `GtexAudioController`.
3. Wire route navigation context changes in `frontend/lib/router/app_router.dart` to trigger soundtrack context switches.
4. Add comprehensive unit tests in `frontend/test/audio/` verifying channel mixing, ducking calculations, and test environment isolation.

Do NOT modify backend database schemas, ingestion scripts, or Unity C# code.
Ensure all tests pass with `flutter test`.
```
