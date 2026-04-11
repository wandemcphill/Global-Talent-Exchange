# GTEX Phased Prompts

These prompts are rewritten to fit the current GTEX codebase.

Context that must be respected:
- GTEX currently sits on top of an existing 3D match engine.
- Existing core ownership already lives in:
  - `Assets/Code/GTEX/GtexMatchRuntime.cs`
  - `Assets/Code/MatchEngine/MatchEngineLoader.cs`
  - `Assets/Code/MatchEngine/MatchManager.cs`
  - `Assets/Code/Events/EventManager.cs`
- New work must be additive and must not replace those systems unless a later phase explicitly says so.

## Prompt A: Implement Immediately

### GTEX Build Stability And Safe Runtime Hardening

You are working inside the Unity project `GTEX 3D Football Engine`.

Your mission is to improve batchmode build reliability and harden GTEX runtime startup without changing match gameplay logic.

Rules:
- Do not replace `MatchManager`, `MatchEngineLoader`, or the existing `EventManager`
- Do not change player AI, ball logic, referee logic, or core match behaviour
- Keep all changes additive, small, and easy to review
- Preserve both Unity Editor usage and batchmode builds
- Prefer better logging, validation, and safe guards over large refactors

Tasks:
1. Harden `Assets/Code/Editor/GtexBuildTools.cs`
   - Use a shared wrapper for all public build entrypoints
   - Add detailed `Debug.Log` before and after each major build stage
   - Log target, output path, scene list, Unity version, and elapsed time
   - Catch exceptions, log the full failure context, then rethrow so batchmode still exits correctly

2. Improve scene validation
   - Validate that at least one scene will be built
   - Log the exact scenes selected from `EditorBuildSettings`
   - Keep the saved active-scene fallback if no enabled build scene exists

3. Add a companion build trace file
   - Write a lightweight trace file under `Builds/Logs/` or `tmp/builds/`
   - Record stage markers, failures, and final result
   - Do not replace Unity's `-logFile`; complement it

4. Harden GTEX runtime startup
   - Update `Assets/Code/GTEX/GtexMatchRuntime.cs`
   - Prevent live runtime bootstrap from starting network or playback flows in batchmode/headless contexts
   - Log clearly when startup is intentionally skipped
   - Do not break normal editor play mode or real player runtime

5. Keep current GTEX ownership intact
   - `GtexMatchRuntime` remains the GTEX live playback bridge
   - `MatchEngineLoader` remains the match/stadium bootstrapper
   - `MatchManager` remains the existing engine lifecycle and clock owner

Acceptance criteria:
- Project compiles successfully
- Windows batch build entrypoint gives clear logs on success and failure
- Scene-selection failures are explicit and actionable
- GTEX runtime does not create avoidable batchmode startup side effects
- Existing gameplay logic is unchanged

## Prompt B: Implement Later

### Additive GTEX Simulation Domain

Only start this phase after Prompt A is complete and Windows batch builds are stable.

Your mission is to add a pure C# GTEX simulation layer that can later support offline, demo, or deterministic-ready flows without replacing the current engine.

Rules:
- This is additive only
- Do not replace `MatchManager`, `MatchEngineLoader`, or existing engine events
- Use GTEX-specific names to avoid class conflicts
- The simulation core must be pure C# with no `MonoBehaviour` or Unity-only APIs
- Integration must be opt-in and disabled by default

Tasks:
1. Create folder:
   - `Assets/Code/GTEX/Simulation/`

2. Implement pure C# core types:
   - `GtexSimState` enum
     - `Kickoff`
     - `FirstHalf`
     - `HalfTime`
     - `SecondHalf`
     - `FullTime`
   - `GtexSimClock`
   - `GtexSimEngine`

3. Implement pure C# event types:
   - `abstract class GtexSimEvent { public float Time; }`
   - `GtexGoalEvent`
   - `GtexMissedChanceEvent`
   - `GtexFoulEvent`
   - `GtexCardEvent`
   - `GtexSimEventSystem`

4. Keep the simulation lightweight
   - Generate simple event flow over accelerated match time
   - Maintain event history
   - Expose callbacks via `Action<GtexSimEvent>`
   - Add deterministic-ready structure where practical
   - Add logging for generated events

5. Add Unity adapters only after the pure C# layer compiles
   - `GtexSimRenderer : MonoBehaviour`
     - Subscribe to `GtexSimEventSystem`
     - Log reactions only
   - `GtexSimCrowdController : MonoBehaviour`
     - On goal log `CHEER`
     - On foul log `BOO`

6. Keep integration opt-in
   - Do not auto-wire the simulation into `GtexMatchRuntime`
   - Use a separate debug harness, bootstrap, or scene object for local testing
   - Do not change existing live GTEX playback flow in this phase

Acceptance criteria:
- Pure C# simulation core compiles independently
- Unity adapters compile in editor and player builds
- Existing GTEX live playback remains untouched
- No batchmode regressions are introduced

## Explicitly Deferred

The following are not part of the immediate implementation:
- Replacing `MatchManager` with a new core engine
- Replacing existing `GameTimeEvent`, `GoalScoredEvent`, or `EventManager`
- Full commentary, VAR, or advanced card/foul presentation systems
- Heavy crowd assets or expensive rendering upgrades
- Direct local-sim takeover of the live GTEX runtime without an explicit mode switch
