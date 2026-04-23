# GTEX Task Gates

This file is the execution order for GTEX implementation work.

Rules:
- Only implement phases marked `READY`
- Do not start phases marked `BLOCKED`
- A blocked phase becomes ready only after its gate is satisfied
- Preserve build stability before expanding architecture

## Current Target

- `P5` is complete
- `P6` is `READY`
- Ship GTEX on top of the current engine first
- Production readiness on the current engine is part of `P6`
- Engine replacement is deferred until objective evidence says replacement is justified

## Phases

### P0 Baseline
Status: `COMPLETE`

Scope:
- Confirm Unity project location and version
- Confirm existing engine ownership
- Add root project guidance

### P1 Build Hardening
Status: `COMPLETE`

Source prompt:
- `Prompt A` in `GTEX_PHASED_PROMPTS.md`

Scope:
- Harden `GtexBuildTools.cs`
- Improve scene validation and build logging
- Add companion build trace file
- Safely harden `GtexMatchRuntime.cs` startup for batchmode/headless contexts

Exit gate:
- Project compiles
- Windows batch build entrypoint provides actionable logs
- No new batchmode startup regressions are introduced
- Existing GTEX gameplay flow is unchanged

### P2 Windows Build Verification
Status: `COMPLETE`

Scope:
- Run the Windows batch build
- Use the improved logs to identify build failures
- Fix only concrete build blockers

Exit gate:
- Windows batch build completes successfully, or remaining failures are isolated to content-heavy late-stage packaging with clear logs

### P3 GTEX Simulation Core
Status: `COMPLETE`

Source prompt:
- `Prompt B` in `GTEX_PHASED_PROMPTS.md`

Scope:
- Add pure C# GTEX simulation core under `Assets/Code/GTEX/Simulation/`
- Add `GtexSimState`, `GtexSimClock`, `GtexSimEngine`, and `GtexSimEventSystem`

Exit gate:
- Simulation core compiles
- No changes to existing live playback flow

### P4 GTEX Simulation Adapters
Status: `COMPLETE`

Scope:
- Add `GtexSimRenderer`
- Add `GtexSimCrowdController`
- Keep them opt-in and logging-only

Exit gate:
- Adapters compile and react to simulation events
- No batchmode regressions

### P5 GTEX Bridge Work
Status: `COMPLETE`

Scope:
- Introduce a clean mode switch between live playback and local simulation
- Bridge simulation outputs into existing UI or GTEX systems carefully

Exit gate:
- Local sim mode is explicit, stable, and does not break live mode

### P6 GTEX Current-Engine Integration Hardening
Status: `READY`

Source prompt:
- `Prompt C` in `GTEX_PHASED_PROMPTS.md`

Execution addendum:
- `GTEX_P6_PRODUCTION_GAP_BACKLOG.md`

Scope:
- Keep `MatchManager`, `MatchEngineLoader`, and the current 3D engine as the default shipped runtime owners
- Use `Assets/Code/GTEX/Engine/` for additive seams, adapters, parity logging, and observability
- Route new GTEX integration work through GTEX-owned interfaces instead of adding fresh direct calls into legacy engine classes
- Keep legacy/current-engine bootstrap as the default path, with controller ownership remaining opt-in and reversible
- Stabilize live playback, local simulation, and Unity build behavior on top of the current engine
- Stabilize hosted live match generation and deployed Unity playback on the current engine path
- Remove debug overlays and complete render/content validation for desktop and mobile
- Add CI gating for Unity Windows batch builds and targeted backend live-motion tests
- Add soak testing, transport/auth monitoring, provisioning verification, and rollback-ready operator workflows

Exit gate:
- GTEX ships on top of the current engine without introducing ownership regressions
- New GTEX work plugs into GTEX-owned interfaces or adapters instead of adding fresh direct legacy coupling
- Legacy/current-engine bootstrap remains the default and is stable for live playback and local simulation
- Windows batch build remains stable
- Hosted live match generation is reliable and verified after deploy
- Unity live playback runs a full session with moving players, moving ball, stable camera, and no debug overlays
- `main` is gated by backend checks and Unity Windows batch build verification before deploy
- Staging passes a 15-minute soak run and production has actionable observability plus rollback-ready procedures

### P7 Evidence For Engine Replacement
Status: `BLOCKED`

Gate:
- `P6` exit gate satisfied

Source prompt:
- `Prompt D` in `GTEX_PHASED_PROMPTS.md`

Scope:
- Gather objective evidence on whether replacing any part of the current engine is justified
- Measure parity, stability, live-motion correctness, reconnection behavior, build/runtime complexity, and operating cost on the current engine path
- Add instrumentation and comparison hooks for controller-boundary experiments without making them the shipped default
- Produce an evidence pack that identifies what should stay, what should be wrapped, and what specific subsystem might be worth replacing

Exit gate:
- There is measured evidence for or against replacement, not just architectural preference
- Any proposed replacement target is specific, bounded, and backed by runtime/build data
- A replacement decision can be made explicitly with rollback and success metrics defined

### P8 Selective Engine Replacement
Status: `BLOCKED`

Gate:
- `P7` exit gate satisfied

Source prompt:
- `Prompt E` in `GTEX_PHASED_PROMPTS.md`

Scope:
- Replace only the specific legacy subsystem(s) justified by the evidence pack
- Keep replacement targeted, reversible, and measured
- Preserve the shipped current-engine path until the replacement path proves materially better
- Define success metrics and rollback metrics before any ownership transfer

Exit gate:
- Replacement delivers measurable benefit against the current-engine baseline
- Rollback remains available until the replacement path is proven in staging and production-like verification
- No build, live-runtime, or deploy regressions are introduced by the targeted replacement
