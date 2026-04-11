# GTEX Task Gates

This file is the execution order for GTEX implementation work.

Rules:
- Only implement phases marked `READY`
- Do not start phases marked `BLOCKED`
- A blocked phase becomes ready only after its gate is satisfied
- Preserve build stability before expanding architecture

## Current Target

- `P5` is complete

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
