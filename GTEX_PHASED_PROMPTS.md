# GTEX Phased Prompts

These prompts are rewritten to fit the current GTEX codebase.

Context that must be respected:
- GTEX currently sits on top of an existing 3D match engine.
- The current engine remains the default ship path until evidence proves replacement is worth the cost.
- Existing core ownership already lives in:
  - `Assets/Code/GTEX/GtexMatchRuntime.cs`
  - `Assets/Code/MatchEngine/MatchEngineLoader.cs`
  - `Assets/Code/MatchEngine/MatchManager.cs`
  - `Assets/Code/Events/EventManager.cs`
- New work must be additive and must not replace those systems unless a later phase explicitly says so and the evidence gate is satisfied.
- Prompt C and Prompt D are integration and evidence phases, not replacement phases.
- Prompt E is the earliest phase allowed to replace ownership away from legacy engine classes.

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

## Prompt C: Implement Next

### Harden GTEX Integration On Top Of The Current Engine

Only start this phase after Prompt B is complete and the GTEX bridge work is stable.

Your mission is to ship GTEX on top of the current 3D engine while reducing direct coupling and improving observability.

Rules:
- Preserve batchmode and Windows build stability
- Keep the current engine as the default shipped runtime path
- Keep migration reversible while the seam layer is bedding in
- Do not rewrite player AI, referee logic, or animation systems in one pass
- Prefer explicit interfaces and adapters over direct calls into legacy classes
- New GTEX features must plug into GTEX-owned seams, not directly into legacy engine code
- Do not move runtime ownership away from `MatchManager` or `MatchEngineLoader` by default in this phase

Tasks:
1. Create folder:
   - `Assets/Code/GTEX/Engine/`

2. Add GTEX-owned core contracts
   - `GtexMatchController`
   - `GtexMatchState`
   - `GtexMatchPhase`
   - `GtexEngineCommand`
   - `IGtexMatchExecutor`
   - `IGtexClockSource`
   - `IGtexEventStream`

3. Add legacy adapter implementations
   - Wrap `MatchManager`
   - Wrap `MatchEngineLoader`
   - Wrap camera targeting and camera switching
   - Wrap player bindings and ball bindings
   - Keep the adapters thin and observable

4. Route integration through GTEX seams
   - Update `GtexMatchRuntime` so new integration logic talks to `GtexMatchController` and GTEX adapters
   - Remove fresh direct coupling from scattered GTEX runtime call sites
   - Keep legacy/current-engine bootstrap as the default path
   - Allow controller-boundary orchestration only as an opt-in experiment

5. Add migration guards
   - Add a clear ownership mode toggle
   - Keep a reversible legacy fallback
   - Add parity logging for clock, phase, scoreline, possession, and ball owner

6. Add release gating on the current-engine path
   - Put the Unity Windows batch build into CI
   - Gate deploys on backend live-route and live-motion validation
   - Keep build logs and deploy verification actionable

7. Harden hosted live behavior on the current-engine path
   - Ensure generated live matches provision reliably
   - Validate live state motion, ball state, and camera behavior after deploy
   - Add explicit handling for stale transport, token refresh failures, and terminal-match selection

8. Validate content and rendering
   - Remove debug-only overlays
   - Validate shaders, materials, kits, stadium imports, and addressables for mobile and desktop
   - Confirm startup and runtime behavior in both development and release render modes

9. Add soak and ops coverage
   - Run full-session soak tests on the current-engine path
   - Add monitoring for stale state, websocket churn, match-generation failures, and auth refresh failures
   - Define operator workflows for provisioning, verification, incident response, and rollback

Acceptance criteria:
- GTEX has a clear engine boundary under `Assets/Code/GTEX/Engine/`
- New GTEX logic no longer adds fresh direct dependencies on legacy engine ownership classes
- GTEX ships on the current engine with seam-based integration and stable fallback behavior
- Controller-boundary work remains optional and reversible
- Windows batch build and editor play mode remain stable
- Hosted live playback on the current engine path is reliable after deploy
- Unity live playback passes a full-session validation with no debug overlays
- CI and operator workflows are in place for production use on the current-engine path

## Prompt D: Implement After Prompt C

### Gather Evidence Before Any Engine Replacement

Only start this phase after Prompt C is complete and the current-engine ship path is stable.

Your mission is to determine whether replacing any part of the current engine is justified, using objective evidence instead of architectural preference.

Rules:
- Do not replace ownership in this phase
- Use the shipped current-engine path as the baseline
- Controller-boundary experiments must stay opt-in and reversible
- Collect measurable runtime, build, and operating evidence before proposing replacement

Tasks:
1. Add evidence instrumentation
   - Measure live-motion correctness, reconnection behavior, stale-transport recovery, and session completion on the current engine path
   - Measure Windows build stability and runtime startup reliability
   - Capture complexity and maintenance hotspots where GTEX still has to work around legacy behavior

2. Compare experimental seam usage to the shipped baseline
   - Use controller-boundary and adapter hooks only as experiments
   - Log parity for clock, phase, score, ball owner, and camera behavior
   - Record regressions and wins, not just design opinions

3. Produce a bounded replacement proposal
   - Identify what should remain on the current engine
   - Identify the smallest subsystem that might be worth replacing
   - Define success metrics, rollback metrics, and verification requirements

Acceptance criteria:
- There is objective evidence for or against replacement
- Any replacement proposal is specific, bounded, and backed by measured data
- An explicit go/no-go decision can be made without guessing

## Prompt E: Implement After Prompt D

### Replace Only What Evidence Justifies

Only start this phase after Prompt D is complete and there is explicit approval to replace a specific subsystem.

Your mission is to replace only the part of the current engine that has proven, with evidence, to be worth replacing.

Rules:
- Replacement must be targeted, reversible, and measured
- Do not do a blanket rewrite of the current engine
- Keep the shipped current-engine path available until the replacement path proves itself
- Define rollout, rollback, and acceptance metrics before moving ownership

Tasks:
1. Replace the selected subsystem only
   - Keep the write scope bounded
   - Preserve adapter compatibility and fallback routes
   - Avoid changing unrelated engine ownership at the same time

2. Verify against the baseline evidence
   - Re-measure the metrics collected in Prompt D
   - Confirm the replacement materially improves the agreed problem
   - Confirm build, startup, live playback, and operational behavior remain stable

3. Roll out with rollback
   - Keep explicit flags or toggles until the replacement proves itself
   - Define the rollback trigger before rollout
   - Remove the old path only after evidence says it is safe

Acceptance criteria:
- The targeted replacement is measurably better than the current-engine baseline
- Rollback remains available until the replacement path is proven
- No build, runtime, or deploy regressions are introduced

## Explicitly Deferred

The following are not part of the immediate implementation:
- Replacing `MatchManager` with a new core engine without evidence
- Replacing existing `GameTimeEvent`, `GoalScoredEvent`, or `EventManager`
- Full commentary, VAR, or advanced card/foul presentation systems
- Heavy crowd assets or expensive rendering upgrades
- Direct local-sim takeover of the live GTEX runtime without an explicit mode switch
- Blanket replacement of the current engine because the seam layer now exists
